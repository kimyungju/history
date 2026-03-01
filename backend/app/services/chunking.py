import logging
import re

from app.config.settings import settings
from app.models.schemas import Chunk
from app.services.ocr import OcrPageResult

logger = logging.getLogger(__name__)

# Rough token estimation: 1 token ≈ 4 characters for English
CHARS_PER_TOKEN = 4


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size = settings.CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN
        self.overlap = settings.CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

    def clean_and_chunk(
        self,
        pages: list[OcrPageResult],
        doc_id: str,
        categories: list[str],
    ) -> list[Chunk]:
        """Clean OCR text, add page markers, and create sliding window chunks."""
        # Step 1: Clean each page and concatenate with markers
        marked_text = ""
        page_offsets: list[tuple[int, int, int]] = []  # (start_char, end_char, page_number)

        for page in pages:
            cleaned = self._clean_text(page.text)
            if not cleaned.strip():
                continue
            marker = f"[PAGE:{page.page_number}]\n"
            start = len(marked_text)
            marked_text += marker + cleaned + "\n"
            end = len(marked_text)
            page_offsets.append((start, end, page.page_number))

        if not marked_text.strip():
            return []

        # Step 2: Sliding window chunking
        chunks = []
        chunk_idx = 0
        pos = 0

        while pos < len(marked_text):
            end = pos + self.chunk_size

            # Try to break at a sentence boundary
            if end < len(marked_text):
                boundary = self._find_sentence_boundary(marked_text, end)
                if boundary > pos:
                    end = boundary

            chunk_text = marked_text[pos:end].strip()
            if not chunk_text:
                break

            # Determine which pages this chunk spans
            chunk_pages = self._get_pages_for_range(page_offsets, pos, end)
            language_tag = self._detect_language(chunk_text)

            chunks.append(Chunk(
                chunk_id=f"{doc_id}_chunk_{chunk_idx:04d}",
                doc_id=doc_id,
                pages=chunk_pages,
                text=chunk_text,
                language_tag=language_tag,
                categories=categories,
            ))

            chunk_idx += 1
            pos = end - self.overlap
            if pos <= 0 and end >= len(marked_text):
                break

        logger.info(f"Chunked doc_id={doc_id}: {len(chunks)} chunks from {len(pages)} pages")
        return chunks

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace, remove common OCR artifacts."""
        # Normalize unicode
        text = text.replace("\u00a0", " ")  # non-breaking space
        # Collapse multiple spaces
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse multiple newlines to max 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip leading/trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(lines).strip()

    def _find_sentence_boundary(self, text: str, pos: int) -> int:
        """Find the nearest sentence-ending punctuation near pos."""
        search_window = 200  # look back up to 200 chars
        start = max(pos - search_window, 0)
        region = text[start:pos]
        # Find last sentence-ending punctuation
        for end_char in [".\n", ".\r", ". ", ".\t", "\u3002"]:
            idx = region.rfind(end_char)
            if idx >= 0:
                return start + idx + len(end_char)
        return pos

    def _get_pages_for_range(
        self, page_offsets: list[tuple[int, int, int]], start: int, end: int
    ) -> list[int]:
        """Determine which pages a character range spans."""
        pages = []
        for page_start, page_end, page_num in page_offsets:
            if page_start < end and page_end > start:
                pages.append(page_num)
        return pages if pages else [1]

    def _detect_language(self, text: str) -> str:
        """Simple heuristic language detection."""
        # Count CJK characters
        cjk_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return "en"
        ratio = cjk_count / total_alpha
        if ratio > 0.5:
            return "zh"
        elif ratio > 0.1:
            return "mixed"
        return "en"


chunking_service = ChunkingService()
