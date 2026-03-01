"""Document AI OCR service for the Colonial Archives Graph-RAG backend."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from google.cloud import documentai_v1 as documentai

from app.config.settings import settings

DOCUMENT_AI_MAX_PAGES_PER_REQUEST = 15


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OcrPageResult:
    """OCR result for a single page."""

    page_number: int  # 1-indexed
    text: str
    confidence: float


@dataclass
class OcrResult:
    """Aggregated OCR result for an entire document."""

    doc_id: str
    pages: list[OcrPageResult]
    raw_responses: list[dict]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class OcrService:
    """Wraps Google Cloud Document AI for PDF OCR."""

    def __init__(self) -> None:
        self._client = None
        self.processor_name = settings.DOC_AI_PROCESSOR_ID

    @property
    def client(self):
        if self._client is None:
            api_endpoint = f"{settings.GCP_REGION}-documentai.googleapis.com"
            self._client = documentai.DocumentProcessorServiceClient(
                client_options={"api_endpoint": api_endpoint}
            )
        return self._client

    # -- public -------------------------------------------------------------

    async def process_pdf(self, pdf_bytes: bytes, doc_id: str) -> OcrResult:
        """OCR a full PDF document.

        Document AI's synchronous endpoint accepts at most 15 pages per
        request.  For longer documents the PDF is processed in batches of
        15 pages with concurrency limited by a semaphore.
        """
        total_pages = self._count_pages(pdf_bytes)

        if total_pages <= DOCUMENT_AI_MAX_PAGES_PER_REQUEST:
            # Small document -- single request, no page selector needed.
            result = await self._process_batch(pdf_bytes, doc_id, page_start=1)
            pages = sorted(result["pages"], key=lambda p: p.page_number)
            return OcrResult(
                doc_id=doc_id,
                pages=pages,
                raw_responses=result["raw_responses"],
            )

        # Large document -- split into batches of 15 pages.
        semaphore = asyncio.Semaphore(5)

        async def _limited(coro):
            async with semaphore:
                return await coro

        tasks: list[asyncio.Task] = []
        for batch_start in range(1, total_pages + 1, DOCUMENT_AI_MAX_PAGES_PER_REQUEST):
            batch_end = min(
                batch_start + DOCUMENT_AI_MAX_PAGES_PER_REQUEST - 1,
                total_pages,
            )
            tasks.append(
                _limited(
                    self._process_page_range(pdf_bytes, doc_id, batch_start, batch_end)
                )
            )

        batch_results: list[dict] = await asyncio.gather(*tasks)

        all_pages: list[OcrPageResult] = []
        all_raw: list[dict] = []
        for br in batch_results:
            all_pages.extend(br["pages"])
            all_raw.extend(br["raw_responses"])

        all_pages.sort(key=lambda p: p.page_number)

        return OcrResult(doc_id=doc_id, pages=all_pages, raw_responses=all_raw)

    # -- internal -----------------------------------------------------------

    async def _process_page_range(
        self,
        pdf_bytes: bytes,
        doc_id: str,
        page_start: int,
        page_end: int,
    ) -> dict:
        """Process a specific page range using ``IndividualPageSelector``.

        Parameters
        ----------
        page_start, page_end:
            1-indexed inclusive page bounds.
        """
        individual_pages = list(range(page_start, page_end + 1))

        process_options = documentai.ProcessOptions(
            individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                pages=individual_pages,
            ),
        )

        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf",
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
            process_options=process_options,
        )

        loop = asyncio.get_event_loop()
        response: documentai.ProcessResponse = await loop.run_in_executor(
            None, self.client.process_document, request
        )

        document = response.document
        full_text = document.text

        pages: list[OcrPageResult] = []
        for idx, page in enumerate(document.pages):
            # The page_number in the response corresponds to the selected
            # pages.  Map back to the absolute page number.
            absolute_page_number = page_start + idx
            text = self._extract_page_text(full_text, page)
            confidence = page.layout.confidence if page.layout else 0.0
            pages.append(
                OcrPageResult(
                    page_number=absolute_page_number,
                    text=text,
                    confidence=confidence,
                )
            )

        raw_resp = documentai.ProcessResponse.to_dict(response)

        return {"pages": pages, "raw_responses": [raw_resp]}

    async def _process_batch(
        self,
        pdf_bytes: bytes,
        doc_id: str,
        page_start: int,
    ) -> dict:
        """Process a full PDF (<= 15 pages) in a single request.

        ``page_start`` is the 1-indexed offset of the first page within the
        larger document (used to compute absolute page numbers).  For
        standalone documents this is simply ``1``.
        """
        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf",
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
        )

        loop = asyncio.get_event_loop()
        response: documentai.ProcessResponse = await loop.run_in_executor(
            None, self.client.process_document, request
        )

        document = response.document
        full_text = document.text

        pages: list[OcrPageResult] = []
        for idx, page in enumerate(document.pages):
            absolute_page_number = page_start + idx
            text = self._extract_page_text(full_text, page)
            confidence = page.layout.confidence if page.layout else 0.0
            pages.append(
                OcrPageResult(
                    page_number=absolute_page_number,
                    text=text,
                    confidence=confidence,
                )
            )

        raw_resp = documentai.ProcessResponse.to_dict(response)

        return {"pages": pages, "raw_responses": [raw_resp]}

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_page_text(full_text: str, page) -> str:
        """Extract the text for a single page from the full document text.

        Document AI stores the complete OCR text in ``document.text`` and
        each page/block/paragraph references into it via *text anchors*
        (``text_segments`` with ``start_index`` / ``end_index``).  We use
        the block-level layout anchors to reconstruct per-page text.
        """
        segments: list[tuple[int, int]] = []
        for block in page.blocks:
            text_anchor = block.layout.text_anchor
            if not text_anchor or not text_anchor.text_segments:
                continue
            for seg in text_anchor.text_segments:
                start = int(seg.start_index)
                end = int(seg.end_index)
                segments.append((start, end))

        if not segments:
            return ""

        # Sort by start position to maintain reading order.
        segments.sort(key=lambda s: s[0])

        parts: list[str] = []
        for start, end in segments:
            parts.append(full_text[start:end])

        return "".join(parts)

    @staticmethod
    def _count_pages(pdf_bytes: bytes) -> int:
        """Estimate the number of pages in a PDF using a regex heuristic.

        Counts occurrences of ``/Type /Page`` (but not ``/Type /Pages``)
        which corresponds to individual page objects in the PDF cross-
        reference table.  This avoids pulling in a heavy PDF library.
        """
        # The pattern matches "/Type /Page" NOT followed by "s" to
        # exclude the "/Type /Pages" (page tree root) entry.
        matches = re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes)
        return max(len(matches), 1)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

ocr_service = OcrService()
