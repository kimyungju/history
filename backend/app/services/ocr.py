"""Document AI OCR service for the Colonial Archives Graph-RAG backend."""

from __future__ import annotations

import asyncio
import io
import logging
import re
from dataclasses import dataclass

from google.api_core.exceptions import ResourceExhausted
from google.cloud import documentai_v1 as documentai
from pypdf import PdfReader, PdfWriter

from app.config.settings import settings

logger = logging.getLogger(__name__)

DOCUMENT_AI_MAX_PAGES_PER_REQUEST = 15
# Document AI synchronous API rejects inline documents > 40 MB.
DOCUMENT_AI_MAX_INLINE_BYTES = 40 * 1024 * 1024


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
        request and rejects inline documents larger than 40 MB.

        For large PDFs (> 40 MB) we physically split the PDF into sub-PDFs
        of up to 15 pages each using pypdf before sending to Document AI.
        For smaller multi-page PDFs we use ``IndividualPageSelector``.

        Adaptive concurrency: reduces parallelism for very large PDFs to
        avoid memory pressure and API quota exhaustion.
        """
        file_size_mb = len(pdf_bytes) / 1024 / 1024
        is_oversized = len(pdf_bytes) > DOCUMENT_AI_MAX_INLINE_BYTES
        total_pages = self._count_pages_pypdf(pdf_bytes)

        logger.info(
            "[%s] OCR starting — %.1f MB, %d pages, oversized=%s",
            doc_id,
            file_size_mb,
            total_pages,
            is_oversized,
        )

        if total_pages <= DOCUMENT_AI_MAX_PAGES_PER_REQUEST and not is_oversized:
            # Small document -- single request, no page selector needed.
            result = await self._process_batch(pdf_bytes, doc_id, page_start=1, batch_label="1/1")
            pages = sorted(result["pages"], key=lambda p: p.page_number)
            return OcrResult(
                doc_id=doc_id,
                pages=pages,
                raw_responses=result["raw_responses"],
            )

        # Adaptive concurrency: reduce parallelism for XL documents to
        # avoid memory pressure and Document AI quota exhaustion.
        if total_pages > 200:
            concurrency = 1
        elif total_pages > 100:
            concurrency = 2
        else:
            concurrency = 5

        total_batches = (total_pages + DOCUMENT_AI_MAX_PAGES_PER_REQUEST - 1) // DOCUMENT_AI_MAX_PAGES_PER_REQUEST
        logger.info(
            "[%s] Large PDF — %d batches of ≤%d pages, concurrency=%d",
            doc_id,
            total_batches,
            DOCUMENT_AI_MAX_PAGES_PER_REQUEST,
            concurrency,
        )

        # Large document -- split into batches of 15 pages.
        reader = PdfReader(io.BytesIO(pdf_bytes)) if is_oversized else None
        semaphore = asyncio.Semaphore(concurrency)
        completed_count = 0
        completed_lock = asyncio.Lock()

        async def _limited(coro, batch_num: int):
            nonlocal completed_count
            async with semaphore:
                result = await coro
                async with completed_lock:
                    completed_count += 1
                    logger.info(
                        "[%s] OCR batch %d/%d complete (%d/%d done)",
                        doc_id,
                        batch_num,
                        total_batches,
                        completed_count,
                        total_batches,
                    )
                return result

        tasks: list[asyncio.Task] = []
        batch_num = 0
        for batch_start in range(1, total_pages + 1, DOCUMENT_AI_MAX_PAGES_PER_REQUEST):
            batch_end = min(
                batch_start + DOCUMENT_AI_MAX_PAGES_PER_REQUEST - 1,
                total_pages,
            )
            batch_num += 1
            batch_label = f"{batch_num}/{total_batches}"

            if is_oversized:
                # Split out just the needed pages into a smaller sub-PDF.
                sub_pdf_bytes = self._extract_page_range(reader, batch_start, batch_end)
                tasks.append(
                    _limited(
                        self._process_batch(sub_pdf_bytes, doc_id, page_start=batch_start, batch_label=batch_label),
                        batch_num,
                    )
                )
            else:
                tasks.append(
                    _limited(
                        self._process_page_range(pdf_bytes, doc_id, batch_start, batch_end, batch_label=batch_label),
                        batch_num,
                    )
                )

        # Release the PdfReader now — sub-PDFs are already extracted.
        reader = None

        batch_results: list[dict] = await asyncio.gather(*tasks)

        all_pages: list[OcrPageResult] = []
        all_raw: list[dict] = []
        for br in batch_results:
            all_pages.extend(br["pages"])
            all_raw.extend(br["raw_responses"])

        all_pages.sort(key=lambda p: p.page_number)
        logger.info(
            "[%s] OCR complete — %d pages extracted",
            doc_id,
            len(all_pages),
        )

        return OcrResult(doc_id=doc_id, pages=all_pages, raw_responses=all_raw)

    # -- internal -----------------------------------------------------------

    async def _process_page_range(
        self,
        pdf_bytes: bytes,
        doc_id: str,
        page_start: int,
        page_end: int,
        *,
        batch_label: str = "",
    ) -> dict:
        """Process a specific page range using ``IndividualPageSelector``.

        Parameters
        ----------
        page_start, page_end:
            1-indexed inclusive page bounds.
        batch_label:
            Human-readable label like "3/14" for logging.
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

        response = await self._call_document_ai(request, doc_id, batch_label)

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
        # Release the heavy response object to free memory.
        del response, document, full_text

        return {"pages": pages, "raw_responses": [raw_resp]}

    async def _process_batch(
        self,
        pdf_bytes: bytes,
        doc_id: str,
        page_start: int,
        *,
        batch_label: str = "",
    ) -> dict:
        """Process a full PDF (<= 15 pages) in a single request.

        ``page_start`` is the 1-indexed offset of the first page within the
        larger document (used to compute absolute page numbers).  For
        standalone documents this is simply ``1``.

        ``batch_label`` is a human-readable label like "3/14" for logging.
        """
        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf",
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
        )

        response = await self._call_document_ai(request, doc_id, batch_label)

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
        # Release the heavy response object to free memory.
        del response, document, full_text

        return {"pages": pages, "raw_responses": [raw_resp]}

    # -- Document AI call with retry ----------------------------------------

    async def _call_document_ai(
        self,
        request: documentai.ProcessRequest,
        doc_id: str,
        batch_label: str,
    ) -> documentai.ProcessResponse:
        """Call Document AI with retry on 429 RESOURCE_EXHAUSTED.

        Retries up to 3 times with exponential backoff (2s, 4s, 8s).
        """
        max_retries = 3
        base_delay = 2.0

        loop = asyncio.get_event_loop()
        for attempt in range(max_retries + 1):
            try:
                response: documentai.ProcessResponse = await loop.run_in_executor(
                    None, self.client.process_document, request
                )
                return response
            except ResourceExhausted:
                if attempt >= max_retries:
                    logger.error(
                        "[%s] batch %s — Document AI RESOURCE_EXHAUSTED after %d retries, giving up",
                        doc_id,
                        batch_label,
                        max_retries,
                    )
                    raise
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "[%s] batch %s — Document AI RESOURCE_EXHAUSTED (429), retrying in %.0fs (attempt %d/%d)",
                    doc_id,
                    batch_label,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)

        # Unreachable, but satisfies type checkers.
        raise RuntimeError("Unexpected: exhausted retry loop without returning or raising")

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_page_range(reader: PdfReader, page_start: int, page_end: int) -> bytes:
        """Extract pages [page_start, page_end] (1-indexed, inclusive) into a new PDF.

        Uses pypdf to create a sub-PDF containing only the requested pages,
        which keeps the byte size well under Document AI's 40 MB limit.
        """
        writer = PdfWriter()
        for i in range(page_start - 1, page_end):  # Convert to 0-indexed
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    @staticmethod
    def _count_pages_pypdf(pdf_bytes: bytes) -> int:
        """Count pages in a PDF using pypdf (accurate, unlike regex heuristic)."""
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages)

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
