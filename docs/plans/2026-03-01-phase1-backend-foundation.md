# Phase 1: Backend Foundation + Vector-Only Query — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working FastAPI backend that ingests PDFs from Cloud Storage (OCR → chunk → embed → vector index) and answers questions via vector-only retrieval with Gemini-generated cited answers.

**Architecture:** FastAPI monolith on Cloud Run. Direct Google Cloud SDK calls to Document AI (OCR), Vertex AI (embeddings + LLM), Vector Search (retrieval), and Cloud Storage (PDF storage + signed URLs). Sync ingestion in this phase. No Neo4j, no graph, no frontend yet.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, google-cloud-documentai, google-cloud-aiplatform, google-cloud-storage, vertexai, pydantic v2, Docker

---

## Task 1: Project Skeleton + Configuration

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config/settings.py`
- Create: `backend/app/config/__init__.py`
- Create: `backend/app/config/document_categories.json`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`

**Step 1: Create directory structure**

```bash
mkdir -p backend/app/config backend/app/models backend/app/routers backend/app/services
touch backend/app/__init__.py backend/app/config/__init__.py backend/app/models/__init__.py backend/app/routers/__init__.py backend/app/services/__init__.py
```

**Step 2: Write requirements.txt**

```text
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
pydantic-settings==2.7.1
google-cloud-documentai==2.32.0
google-cloud-storage==2.19.0
google-cloud-aiplatform==1.74.0
vertexai==1.74.0
python-multipart==0.0.20
httpx==0.28.1
```

**Step 3: Write config/settings.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GCP
    GCP_PROJECT_ID: str = "PLACEHOLDER_GCP_PROJECT_ID"
    GCP_REGION: str = "PLACEHOLDER_GCP_REGION"

    # Document AI
    DOC_AI_PROCESSOR_ID: str = "PLACEHOLDER_DOC_AI_PROCESSOR_ID"

    # Vertex AI Embeddings
    VERTEX_EMBED_MODEL: str = "text-embedding-004"

    # Vertex AI Vector Search
    VECTOR_SEARCH_ENDPOINT: str = "PLACEHOLDER_VECTOR_SEARCH_ENDPOINT"
    VECTOR_SEARCH_INDEX_ID: str = "PLACEHOLDER_VECTOR_SEARCH_INDEX_ID"
    VECTOR_SEARCH_DEPLOYED_INDEX_ID: str = "PLACEHOLDER_DEPLOYED_INDEX_ID"

    # Vertex AI LLM
    VERTEX_LLM_MODEL: str = "gemini-1.5-flash"

    # Neo4j (Phase 2)
    NEO4J_URI: str = "PLACEHOLDER_NEO4J_URI"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "PLACEHOLDER_NEO4J_PASSWORD"

    # Cloud Storage
    CLOUD_STORAGE_BUCKET: str = "PLACEHOLDER_GCS_BUCKET_NAME"

    # Pub/Sub (Phase 4)
    PUBSUB_TOPIC: str = "PLACEHOLDER_PUBSUB_TOPIC"

    # Tavily (Phase 4)
    TAVILY_API_KEY: str = "PLACEHOLDER_TAVILY_API_KEY"

    # Thresholds
    RELEVANCE_THRESHOLD: float = 0.7
    OCR_CONFIDENCE_FLAG: float = 0.5
    CHUNK_SIZE_TOKENS: int = 450
    CHUNK_OVERLAP_TOKENS: int = 100
    GRAPH_HOP_DEPTH: int = 3
    VECTOR_TOP_K: int = 10

    # Signed URL
    SIGNED_URL_EXPIRY_MINUTES: int = 15

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 4: Write config/document_categories.json**

```json
{
  "_comment": "Map PDF filenames to 1-2 categories from MAIN_CATEGORIES. Provided by user before ingestion.",
  "_example_document_001.pdf": ["Economic and Financial"],
  "_example_document_002.pdf": ["Defence and Military", "General and Establishment"]
}
```

**Step 5: Write models/schemas.py**

```python
from pydantic import BaseModel


MAIN_CATEGORIES = [
    "Internal Relations and Research",
    "Economic and Financial",
    "Social Services",
    "Defence and Military",
    "General and Establishment",
]


# --- Request Models ---

class IngestRequest(BaseModel):
    pdf_url: str  # "gs://bucket/document_042.pdf"


class QueryRequest(BaseModel):
    question: str
    filter_categories: list[str] | None = None


# --- Evidence ---

class Evidence(BaseModel):
    doc_id: str
    page: int
    text_span: str
    chunk_id: str
    confidence: float


# --- Citation Models ---

class ArchiveCitation(BaseModel):
    type: str = "archive"
    id: int
    doc_id: str
    pages: list[int]
    text_span: str
    confidence: float


class WebCitation(BaseModel):
    type: str = "web"
    id: int
    title: str
    url: str


# --- Graph Models (Phase 2, defined now for schema completeness) ---

class GraphNode(BaseModel):
    canonical_id: str
    name: str
    main_categories: list[str]
    sub_category: str | None = None
    attributes: dict = {}
    highlighted: bool = False


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    attributes: dict = {}
    highlighted: bool = False


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    center_node: str


# --- Response Models ---

class OcrConfidenceWarning(BaseModel):
    page: int
    confidence: float


class IngestResponse(BaseModel):
    job_id: str
    status: str  # "processing" | "done" | "failed"
    pages_total: int = 0
    chunks_processed: int = 0
    entities_extracted: int = 0
    ocr_confidence_warnings: list[OcrConfidenceWarning] = []


class QueryResponse(BaseModel):
    answer: str
    source_type: str  # "archive" | "web_fallback" | "mixed"
    citations: list[ArchiveCitation | WebCitation]
    graph: GraphPayload | None = None


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int  # seconds


# --- Internal Models ---

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    pages: list[int]
    text: str
    language_tag: str  # "en" | "zh" | "mixed"
    categories: list[str]


class EntityExtractionResult(BaseModel):
    """LLM structured output for entity extraction (Phase 2)."""

    class ExtractedEntity(BaseModel):
        name: str
        main_categories: list[str]
        sub_category: str | None = None
        attributes: dict = {}
        evidence: Evidence

    class ExtractedRelationship(BaseModel):
        from_entity: str
        to_entity: str
        type: str
        attributes: dict = {}
        evidence: Evidence

    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]
```

**Step 6: Write main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Colonial Archives Graph-RAG",
    description="Source-grounded Q&A over colonial-era archive documents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Step 7: Write Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Step 8: Write .env.example**

```
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=asia-southeast1
DOC_AI_PROCESSOR_ID=projects/PROJECT/locations/LOCATION/processors/PROCESSOR_ID
CLOUD_STORAGE_BUCKET=your-bucket-name
VECTOR_SEARCH_ENDPOINT=your-vector-search-endpoint
VECTOR_SEARCH_INDEX_ID=your-index-id
VECTOR_SEARCH_DEPLOYED_INDEX_ID=your-deployed-index-id
```

**Step 9: Verify the app starts**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
# Visit http://localhost:8080/health → {"status": "ok"}
# Visit http://localhost:8080/docs → Swagger UI
```

**Step 10: Commit**

```bash
git add backend/
git commit -m "feat: Phase 1 skeleton — FastAPI app, config, schemas, Dockerfile"
```

---

## Task 2: Cloud Storage Service

**Files:**
- Create: `backend/app/services/storage.py`

**Step 1: Write storage service**

```python
import json
from datetime import timedelta
from pathlib import PurePosixPath

from google.cloud import storage

from app.config.settings import settings


class StorageService:
    def __init__(self) -> None:
        self.client = storage.Client(project=settings.GCP_PROJECT_ID)
        self.bucket = self.client.bucket(settings.CLOUD_STORAGE_BUCKET)

    def read_pdf_bytes(self, gcs_url: str) -> bytes:
        """Read PDF bytes from a gs:// URL."""
        blob_name = self._parse_blob_name(gcs_url)
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()

    def upload_json(self, path: str, data: dict | list) -> str:
        """Upload JSON data to Cloud Storage. Returns gs:// URL."""
        blob = self.bucket.blob(path)
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False),
            content_type="application/json",
        )
        return f"gs://{settings.CLOUD_STORAGE_BUCKET}/{path}"

    def generate_signed_url(self, gcs_url: str, expiry_minutes: int | None = None) -> str:
        """Generate a signed URL for a Cloud Storage object."""
        blob_name = self._parse_blob_name(gcs_url)
        blob = self.bucket.blob(blob_name)
        minutes = expiry_minutes or settings.SIGNED_URL_EXPIRY_MINUTES
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="GET",
        )

    def get_doc_id_from_url(self, gcs_url: str) -> str:
        """Extract document ID (filename without extension) from gs:// URL."""
        blob_name = self._parse_blob_name(gcs_url)
        return PurePosixPath(blob_name).stem

    def get_pdf_url(self, doc_id: str) -> str:
        """Build gs:// URL from doc_id. Assumes PDFs are at top level of bucket."""
        return f"gs://{settings.CLOUD_STORAGE_BUCKET}/{doc_id}.pdf"

    def _parse_blob_name(self, gcs_url: str) -> str:
        """Parse 'gs://bucket/path/to/file' → 'path/to/file'."""
        if not gcs_url.startswith("gs://"):
            raise ValueError(f"Invalid GCS URL: {gcs_url}")
        parts = gcs_url[5:].split("/", 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid GCS URL (no path): {gcs_url}")
        return parts[1]


storage_service = StorageService()
```

**Step 2: Commit**

```bash
git add backend/app/services/storage.py
git commit -m "feat: Cloud Storage service — read PDFs, upload JSON, signed URLs"
```

---

## Task 3: Document AI OCR Service

**Files:**
- Create: `backend/app/services/ocr.py`

**Step 1: Write OCR service**

```python
import asyncio
import logging
from dataclasses import dataclass

from google.cloud import documentai_v1 as documentai

from app.config.settings import settings

logger = logging.getLogger(__name__)

DOCUMENT_AI_MAX_PAGES_PER_REQUEST = 15


@dataclass
class OcrPageResult:
    page_number: int  # 1-indexed
    text: str
    confidence: float


@dataclass
class OcrResult:
    doc_id: str
    pages: list[OcrPageResult]
    raw_responses: list[dict]  # for debugging, stored to GCS


class OcrService:
    def __init__(self) -> None:
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = settings.DOC_AI_PROCESSOR_ID

    async def process_pdf(self, pdf_bytes: bytes, doc_id: str) -> OcrResult:
        """OCR a PDF using Document AI. Batches pages in groups of 15."""
        # Document AI sync API handles the full document at once
        # but has a 15-page limit for online processing.
        # For large docs, we split into batches.
        total_pages = self._count_pages(pdf_bytes)
        logger.info(f"OCR starting: doc_id={doc_id}, total_pages={total_pages}")

        if total_pages <= DOCUMENT_AI_MAX_PAGES_PER_REQUEST:
            # Small enough for single request
            result = await self._process_batch(pdf_bytes, doc_id, page_start=1)
            return OcrResult(
                doc_id=doc_id,
                pages=result["pages"],
                raw_responses=result["raw_responses"],
            )

        # Split into batches and process with concurrency limit
        batches = []
        for start in range(0, total_pages, DOCUMENT_AI_MAX_PAGES_PER_REQUEST):
            end = min(start + DOCUMENT_AI_MAX_PAGES_PER_REQUEST, total_pages)
            batches.append((start, end))

        semaphore = asyncio.Semaphore(5)  # limit concurrent API calls

        async def process_with_limit(batch_start: int, batch_end: int):
            async with semaphore:
                return await self._process_page_range(
                    pdf_bytes, doc_id, batch_start, batch_end
                )

        tasks = [process_with_limit(s, e) for s, e in batches]
        results = await asyncio.gather(*tasks)

        all_pages = []
        all_raw = []
        for r in results:
            all_pages.extend(r["pages"])
            all_raw.extend(r["raw_responses"])

        all_pages.sort(key=lambda p: p.page_number)

        return OcrResult(doc_id=doc_id, pages=all_pages, raw_responses=all_raw)

    async def _process_page_range(
        self, pdf_bytes: bytes, doc_id: str, page_start: int, page_end: int
    ) -> dict:
        """Process a range of pages (0-indexed start/end)."""
        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf",
        )
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
            process_options=documentai.ProcessOptions(
                individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
                    pages=list(range(page_start + 1, page_end + 1))  # 1-indexed for API
                )
            ),
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.client.process_document, request)
        document = response.document

        pages = []
        for i, page in enumerate(document.pages):
            page_num = page_start + i + 1  # 1-indexed
            page_text = self._extract_page_text(document.text, page)
            confidence = page.detected_languages[0].confidence if page.detected_languages else 0.0
            pages.append(OcrPageResult(
                page_number=page_num,
                text=page_text,
                confidence=confidence,
            ))

        return {
            "pages": pages,
            "raw_responses": [{"page_range": [page_start, page_end], "text_length": len(document.text)}],
        }

    async def _process_batch(self, pdf_bytes: bytes, doc_id: str, page_start: int) -> dict:
        """Process a full PDF (<=15 pages) in a single request."""
        raw_document = documentai.RawDocument(
            content=pdf_bytes,
            mime_type="application/pdf",
        )
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.client.process_document, request)
        document = response.document

        pages = []
        for i, page in enumerate(document.pages):
            page_text = self._extract_page_text(document.text, page)
            confidence = page.detected_languages[0].confidence if page.detected_languages else 0.0
            pages.append(OcrPageResult(
                page_number=i + 1,
                text=page_text,
                confidence=confidence,
            ))

        return {
            "pages": pages,
            "raw_responses": [{"page_count": len(document.pages), "text_length": len(document.text)}],
        }

    def _extract_page_text(self, full_text: str, page) -> str:
        """Extract text for a specific page using layout text anchors."""
        segments = []
        for block in page.blocks:
            for segment in block.layout.text_anchor.text_segments:
                start = int(segment.start_index) if segment.start_index else 0
                end = int(segment.end_index)
                segments.append(full_text[start:end])
        return "".join(segments)

    def _count_pages(self, pdf_bytes: bytes) -> int:
        """Count pages in a PDF without full processing."""
        # Simple heuristic: count /Type /Page occurrences
        # For production, use PyPDF2 or similar, but keeping deps minimal
        import re
        matches = re.findall(rb"/Type\s*/Page[^s]", pdf_bytes)
        count = len(matches)
        return max(count, 1)  # at least 1 page


ocr_service = OcrService()
```

**Step 2: Commit**

```bash
git add backend/app/services/ocr.py
git commit -m "feat: Document AI OCR service — batched page processing with concurrency"
```

---

## Task 4: Text Cleaning + Chunking Service

**Files:**
- Create: `backend/app/services/chunking.py`

**Step 1: Write chunking service**

```python
import re
import logging

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
        for end_char in [".\n", ".\r", ". ", ".\t", "。"]:
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
```

**Step 2: Commit**

```bash
git add backend/app/services/chunking.py
git commit -m "feat: chunking service — page markers, sliding window, language detection"
```

---

## Task 5: Vertex AI Embeddings Service

**Files:**
- Create: `backend/app/services/embeddings.py`

**Step 1: Write embeddings service**

```python
import asyncio
import logging

from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from app.config.settings import settings
from app.models.schemas import Chunk

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 250  # Vertex AI limit per request


class EmbeddingsService:
    def __init__(self) -> None:
        self.model = TextEmbeddingModel.from_pretrained(settings.VERTEX_EMBED_MODEL)

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed a list of chunks. Returns list of embedding vectors."""
        texts = [chunk.text for chunk in chunks]
        return await self.embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        results = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return results[0]

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Embed texts in batches. Returns list of embedding vectors."""
        all_embeddings = []

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            inputs = [
                TextEmbeddingInput(text=t, task_type=task_type) for t in batch
            ]
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda inp=inputs: self.model.get_embeddings(inp)
            )
            all_embeddings.extend([e.values for e in embeddings])

        logger.info(f"Embedded {len(texts)} texts in {(len(texts) - 1) // EMBEDDING_BATCH_SIZE + 1} batches")
        return all_embeddings


embeddings_service = EmbeddingsService()
```

**Step 2: Commit**

```bash
git add backend/app/services/embeddings.py
git commit -m "feat: Vertex AI embeddings service — batch embed with text-embedding-004"
```

---

## Task 6: Vertex AI Vector Search Service

**Files:**
- Create: `backend/app/services/vector_search.py`

**Step 1: Write vector search service**

```python
import asyncio
import json
import logging

from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint

from app.config.settings import settings
from app.models.schemas import Chunk

logger = logging.getLogger(__name__)


class VectorSearchService:
    def __init__(self) -> None:
        aiplatform.init(
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_REGION,
        )
        self._endpoint: MatchingEngineIndexEndpoint | None = None

    @property
    def endpoint(self) -> MatchingEngineIndexEndpoint:
        if self._endpoint is None:
            self._endpoint = MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.VECTOR_SEARCH_ENDPOINT,
            )
        return self._endpoint

    async def upsert(
        self, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> int:
        """Upsert chunk embeddings into Vector Search index."""
        # Prepare datapoints with metadata
        datapoints = []
        for chunk, embedding in zip(chunks, embeddings):
            restricts = []
            for cat in chunk.categories:
                restricts.append(
                    aiplatform.matching_engine.matching_engine_index_endpoint.Namespace(
                        name="category", allow_tokens=[cat]
                    )
                )

            datapoints.append({
                "id": chunk.chunk_id,
                "embedding": embedding,
                "restricts": restricts,
                "metadata": {
                    "doc_id": chunk.doc_id,
                    "pages": json.dumps(chunk.pages),
                    "language_tag": chunk.language_tag,
                    "text": chunk.text[:500],  # store truncated text for preview
                },
            })

        loop = asyncio.get_event_loop()
        # Upsert in batches of 100
        upserted = 0
        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i : i + batch_size]
            ids = [d["id"] for d in batch]
            embs = [d["embedding"] for d in batch]

            await loop.run_in_executor(
                None,
                lambda _ids=ids, _embs=embs: self.endpoint.upsert_datapoints(
                    deployed_index_id=settings.VECTOR_SEARCH_DEPLOYED_INDEX_ID,
                    datapoint_ids=_ids,
                    embeddings=_embs,
                ),
            )
            upserted += len(batch)

        logger.info(f"Upserted {upserted} vectors to Vector Search")
        return upserted

    async def search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        filter_categories: list[str] | None = None,
    ) -> list[dict]:
        """Search for similar chunks. Returns list of {id, distance, metadata}."""
        k = top_k or settings.VECTOR_TOP_K

        restricts = []
        if filter_categories:
            restricts.append(
                aiplatform.matching_engine.matching_engine_index_endpoint.Namespace(
                    name="category",
                    allow_tokens=filter_categories,
                )
            )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.endpoint.find_neighbors(
                deployed_index_id=settings.VECTOR_SEARCH_DEPLOYED_INDEX_ID,
                queries=[query_embedding],
                num_neighbors=k,
            ),
        )

        results = []
        if response and response[0]:
            for neighbor in response[0]:
                results.append({
                    "id": neighbor.id,
                    "distance": neighbor.distance,
                })

        logger.info(f"Vector search returned {len(results)} results")
        return results


vector_search_service = VectorSearchService()
```

**Step 2: Commit**

```bash
git add backend/app/services/vector_search.py
git commit -m "feat: Vertex AI Vector Search service — upsert and search with category filtering"
```

---

## Task 7: Gemini LLM Service

**Files:**
- Create: `backend/app/services/llm.py`

**Step 1: Write LLM service**

```python
import asyncio
import json
import logging

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from app.config.settings import settings

logger = logging.getLogger(__name__)

ANSWER_GENERATION_PROMPT = """Context retrieved from archives and/or web:
\"\"\"
{context}
\"\"\"

Sources: {citations}
Source type: {source_type}

Rules:
1. Answer ONLY using information from the context above.
2. Cite every fact using [archive:N] or [web:N].
3. If the context does not contain enough information to answer:
   respond exactly: "I cannot answer this based on the available sources."
4. NEVER infer, guess, or use external knowledge.
5. DO NOT merge facts from different sources without citing each.

User question: {question}"""


class LlmService:
    def __init__(self) -> None:
        vertexai.init(
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_REGION,
        )
        self.model = GenerativeModel(settings.VERTEX_LLM_MODEL)

    async def generate_answer(
        self,
        question: str,
        context_chunks: list[dict],
        source_type: str = "archive",
    ) -> dict:
        """Generate a cited answer from retrieved context chunks.

        Args:
            question: User's question.
            context_chunks: List of dicts with keys: id, text, doc_id, pages, confidence.
            source_type: "archive", "web_fallback", or "mixed".

        Returns:
            Dict with keys: answer, citations.
        """
        # Build context string with citation markers
        context_parts = []
        citation_list = []

        for i, chunk in enumerate(context_chunks):
            cite_type = chunk.get("cite_type", "archive")
            cite_id = i + 1
            context_parts.append(f"[{cite_type}:{cite_id}] {chunk['text']}")
            citation_list.append(f"[{cite_type}:{cite_id}]: doc_id={chunk.get('doc_id', 'N/A')}, pages={chunk.get('pages', [])}")

        context = "\n\n".join(context_parts)
        citations = "\n".join(citation_list)

        prompt = ANSWER_GENERATION_PROMPT.format(
            context=context,
            citations=citations,
            source_type=source_type,
            question=question,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            ),
        )

        answer_text = response.text if response.text else "I cannot answer this based on the available sources."

        return {
            "answer": answer_text,
            "context_chunks": context_chunks,
        }


llm_service = LlmService()
```

**Step 2: Commit**

```bash
git add backend/app/services/llm.py
git commit -m "feat: Gemini LLM service — grounded answer generation with citation prompting"
```

---

## Task 8: Hybrid Retrieval Service (Vector-Only for Phase 1)

**Files:**
- Create: `backend/app/services/hybrid_retrieval.py`

**Step 1: Write hybrid retrieval service**

```python
import json
import logging

from app.config.settings import settings
from app.models.schemas import ArchiveCitation, QueryResponse
from app.services.embeddings import embeddings_service
from app.services.vector_search import vector_search_service
from app.services.llm import llm_service
from app.services.storage import storage_service

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    async def query(
        self, question: str, filter_categories: list[str] | None = None
    ) -> QueryResponse:
        """Execute the full query pipeline: embed → search → generate answer."""

        # Step 1: Embed the question
        query_embedding = await embeddings_service.embed_query(question)

        # Step 2: Vector search
        vector_results = await vector_search_service.search(
            query_embedding=query_embedding,
            filter_categories=filter_categories,
        )

        if not vector_results:
            return QueryResponse(
                answer="I cannot answer this based on the available sources.",
                source_type="archive",
                citations=[],
                graph=None,
            )

        # Step 3: Load chunk texts from stored chunks in GCS
        context_chunks = await self._load_chunk_contexts(vector_results)

        # Step 4: Compute relevance score (Phase 1: avg vector similarity)
        avg_similarity = sum(r["distance"] for r in vector_results) / len(vector_results)

        # Step 5: Determine source type (Phase 1: always archive, no web fallback)
        source_type = "archive"

        # Step 6: Generate answer with Gemini
        llm_result = await llm_service.generate_answer(
            question=question,
            context_chunks=context_chunks,
            source_type=source_type,
        )

        # Step 7: Build citations
        citations = []
        for i, chunk in enumerate(context_chunks):
            citations.append(ArchiveCitation(
                type="archive",
                id=i + 1,
                doc_id=chunk["doc_id"],
                pages=chunk["pages"],
                text_span=chunk["text"][:300],  # truncate for response
                confidence=chunk.get("confidence", avg_similarity),
            ))

        return QueryResponse(
            answer=llm_result["answer"],
            source_type=source_type,
            citations=citations,
            graph=None,  # Phase 2
        )

    async def _load_chunk_contexts(self, vector_results: list[dict]) -> list[dict]:
        """Load full chunk data for vector search results.

        In production, chunk text is stored in GCS at chunks/{doc_id}.json.
        We load the relevant chunks and match by chunk_id.
        """
        # Group results by doc_id (extracted from chunk_id: "{doc_id}_chunk_{N}")
        chunks_by_doc: dict[str, list[str]] = {}
        for result in vector_results:
            chunk_id = result["id"]
            parts = chunk_id.rsplit("_chunk_", 1)
            doc_id = parts[0] if len(parts) == 2 else chunk_id
            chunks_by_doc.setdefault(doc_id, []).append(chunk_id)

        # Load chunk files from GCS and build context
        context_chunks = []
        for doc_id, chunk_ids in chunks_by_doc.items():
            try:
                gcs_path = f"chunks/{doc_id}.json"
                gcs_url = f"gs://{settings.CLOUD_STORAGE_BUCKET}/{gcs_path}"
                blob_name = storage_service._parse_blob_name(gcs_url)
                blob = storage_service.bucket.blob(blob_name)
                data = json.loads(blob.download_as_text())

                chunk_lookup = {c["chunk_id"]: c for c in data}
                for cid in chunk_ids:
                    if cid in chunk_lookup:
                        c = chunk_lookup[cid]
                        context_chunks.append({
                            "id": cid,
                            "text": c["text"],
                            "doc_id": c["doc_id"],
                            "pages": c["pages"],
                            "confidence": next(
                                (r["distance"] for r in vector_results if r["id"] == cid),
                                0.0,
                            ),
                            "cite_type": "archive",
                        })
            except Exception as e:
                logger.warning(f"Failed to load chunks for {doc_id}: {e}")

        # Sort by confidence (distance) descending
        context_chunks.sort(key=lambda c: c["confidence"], reverse=True)
        return context_chunks


hybrid_retrieval_service = HybridRetrievalService()
```

**Step 2: Commit**

```bash
git add backend/app/services/hybrid_retrieval.py
git commit -m "feat: hybrid retrieval service — vector-only query pipeline for Phase 1"
```

---

## Task 9: Ingestion Router

**Files:**
- Create: `backend/app/routers/ingest.py`
- Modify: `backend/app/main.py`

**Step 1: Write ingestion router**

```python
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config.settings import settings
from app.models.schemas import (
    MAIN_CATEGORIES,
    Chunk,
    IngestRequest,
    IngestResponse,
    OcrConfidenceWarning,
)
from app.services.chunking import chunking_service
from app.services.embeddings import embeddings_service
from app.services.ocr import ocr_service
from app.services.storage import storage_service
from app.services.vector_search import vector_search_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

# In-memory job tracking (Phase 1 only; Phase 4 uses Pub/Sub)
_jobs: dict[str, IngestResponse] = {}


def _load_document_categories() -> dict[str, list[str]]:
    """Load document-to-category mapping from config."""
    import importlib.resources
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config" / "document_categories.json"
    try:
        with open(config_path) as f:
            data = json.load(f)
        # Filter out comment keys
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except FileNotFoundError:
        logger.warning("document_categories.json not found, using empty mapping")
        return {}


@router.post("/ingest_pdf", response_model=IngestResponse)
async def ingest_pdf(request: IngestRequest, background_tasks: BackgroundTasks):
    """Ingest a PDF from Cloud Storage: OCR → chunk → embed → vector index."""
    job_id = str(uuid.uuid4())
    doc_id = storage_service.get_doc_id_from_url(request.pdf_url)

    _jobs[job_id] = IngestResponse(job_id=job_id, status="processing")

    background_tasks.add_task(_run_ingestion, job_id, request.pdf_url, doc_id)

    return _jobs[job_id]


@router.get("/ingest_status/{job_id}", response_model=IngestResponse)
async def ingest_status(job_id: str):
    """Check ingestion job status."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _jobs[job_id]


async def _run_ingestion(job_id: str, pdf_url: str, doc_id: str) -> None:
    """Execute the full ingestion pipeline."""
    job = _jobs[job_id]
    try:
        # Step 1: Download PDF
        logger.info(f"[{job_id}] Downloading PDF: {pdf_url}")
        pdf_bytes = storage_service.read_pdf_bytes(pdf_url)

        # Step 2: OCR
        logger.info(f"[{job_id}] Running OCR on {doc_id}")
        ocr_result = await ocr_service.process_pdf(pdf_bytes, doc_id)
        job.pages_total = len(ocr_result.pages)

        # Store raw OCR output to GCS
        storage_service.upload_json(
            f"ocr/{doc_id}_ocr.json",
            {"doc_id": doc_id, "pages": [{"page": p.page_number, "text": p.text, "confidence": p.confidence} for p in ocr_result.pages]},
        )

        # Flag low confidence pages
        for page in ocr_result.pages:
            if page.confidence < settings.OCR_CONFIDENCE_FLAG:
                job.ocr_confidence_warnings.append(
                    OcrConfidenceWarning(page=page.page_number, confidence=page.confidence)
                )

        # Step 3: Look up categories
        categories_map = _load_document_categories()
        pdf_filename = pdf_url.rsplit("/", 1)[-1]
        categories = categories_map.get(pdf_filename, categories_map.get(doc_id, []))
        if not categories:
            # Default: will be auto-classified in Phase 4
            logger.warning(f"[{job_id}] No categories found for {doc_id}, using empty list")
            categories = []

        # Step 4: Chunk
        logger.info(f"[{job_id}] Chunking {len(ocr_result.pages)} pages")
        chunks = chunking_service.clean_and_chunk(
            pages=ocr_result.pages,
            doc_id=doc_id,
            categories=categories,
        )
        job.chunks_processed = len(chunks)

        # Store chunks to GCS
        storage_service.upload_json(
            f"chunks/{doc_id}.json",
            [chunk.model_dump() for chunk in chunks],
        )

        # Step 5: Embed
        logger.info(f"[{job_id}] Embedding {len(chunks)} chunks")
        embeddings = await embeddings_service.embed_chunks(chunks)

        # Step 6: Upsert to Vector Search
        logger.info(f"[{job_id}] Upserting to Vector Search")
        await vector_search_service.upsert(chunks, embeddings)

        # Phase 2: Entity extraction + Neo4j would go here

        job.status = "done"
        logger.info(f"[{job_id}] Ingestion complete: {job.chunks_processed} chunks from {job.pages_total} pages")

    except Exception as e:
        logger.error(f"[{job_id}] Ingestion failed: {e}", exc_info=True)
        job.status = "failed"


```

**Step 2: Update main.py to include routers**

Add to `backend/app/main.py` after the CORS middleware:

```python
from app.routers import ingest

app.include_router(ingest.router)
```

**Step 3: Commit**

```bash
git add backend/app/routers/ingest.py backend/app/main.py
git commit -m "feat: /ingest_pdf endpoint — full OCR → chunk → embed → vector pipeline"
```

---

## Task 10: Query Router

**Files:**
- Create: `backend/app/routers/query.py`
- Modify: `backend/app/main.py`

**Step 1: Write query router**

```python
from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryResponse, SignedUrlResponse
from app.services.hybrid_retrieval import hybrid_retrieval_service
from app.services.storage import storage_service

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Ask a question about the archive documents."""
    return await hybrid_retrieval_service.query(
        question=request.question,
        filter_categories=request.filter_categories,
    )


@router.get("/document/signed_url", response_model=SignedUrlResponse)
async def get_signed_url(doc_id: str, page: int = 1):
    """Get a signed URL for viewing a PDF document."""
    pdf_url = storage_service.get_pdf_url(doc_id)
    signed_url = storage_service.generate_signed_url(pdf_url)
    return SignedUrlResponse(
        url=signed_url,
        expires_in=storage_service.bucket.client.project and 900,  # 15 min in seconds
    )
```

**Step 2: Update main.py**

Add to `backend/app/main.py`:

```python
from app.routers import ingest, query

app.include_router(ingest.router)
app.include_router(query.router)
```

**Step 3: Commit**

```bash
git add backend/app/routers/query.py backend/app/main.py
git commit -m "feat: /query and /document/signed_url endpoints"
```

---

## Task 11: Graph Router Placeholder (Phase 2 stub)

**Files:**
- Create: `backend/app/routers/graph.py`
- Modify: `backend/app/main.py`

**Step 1: Write graph router stub**

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{entity_canonical_id}")
async def get_entity_graph(entity_canonical_id: str):
    """Get subgraph around an entity. Phase 2."""
    raise HTTPException(status_code=501, detail="Graph endpoints available in Phase 2")


@router.get("/search")
async def search_entities(q: str):
    """Search entities by name. Phase 2."""
    raise HTTPException(status_code=501, detail="Graph endpoints available in Phase 2")
```

**Step 2: Update main.py**

```python
from app.routers import ingest, query, graph

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)
```

**Step 3: Commit**

```bash
git add backend/app/routers/graph.py backend/app/main.py
git commit -m "feat: graph router stubs (Phase 2 placeholder)"
```

---

## Task 12: Docker Compose + Vertex AI Init + Final Verification

**Files:**
- Create: `infra/docker-compose.yml`
- Modify: `backend/app/main.py` (add Vertex AI init on startup)

**Step 1: Write docker-compose.yml**

```yaml
version: "3.8"

services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    env_file:
      - ../backend/.env
    volumes:
      - ${GOOGLE_APPLICATION_CREDENTIALS:-~/.config/gcloud/application_default_credentials.json}:/app/credentials.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

**Step 2: Add Vertex AI initialization to main.py startup**

```python
import vertexai
from contextlib import asynccontextmanager
from app.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Vertex AI on startup
    vertexai.init(
        project=settings.GCP_PROJECT_ID,
        location=settings.GCP_REGION,
    )
    yield


app = FastAPI(
    title="Colonial Archives Graph-RAG",
    description="Source-grounded Q&A over colonial-era archive documents",
    version="0.1.0",
    lifespan=lifespan,
)
```

**Step 3: Verify full app starts and Swagger docs render**

```bash
cd backend
uvicorn app.main:app --reload --port 8080
# Visit http://localhost:8080/docs
# Verify all endpoints visible:
#   POST /ingest_pdf
#   GET /ingest_status/{job_id}
#   POST /query
#   GET /document/signed_url
#   GET /graph/{entity_canonical_id}
#   GET /graph/search
#   GET /health
```

**Step 4: Commit**

```bash
git add infra/docker-compose.yml backend/app/main.py
git commit -m "feat: docker-compose for local dev, Vertex AI startup init"
```

---

## Summary

| Task | What it builds | Key files |
|------|---------------|-----------|
| 1 | Project skeleton, config, schemas, Dockerfile | `main.py`, `settings.py`, `schemas.py`, `Dockerfile` |
| 2 | Cloud Storage read/write/signed URLs | `services/storage.py` |
| 3 | Document AI OCR with batched page processing | `services/ocr.py` |
| 4 | Text cleaning + sliding window chunking | `services/chunking.py` |
| 5 | Vertex AI embeddings (batch) | `services/embeddings.py` |
| 6 | Vector Search upsert + search | `services/vector_search.py` |
| 7 | Gemini answer generation with citations | `services/llm.py` |
| 8 | Hybrid retrieval (vector-only Phase 1) | `services/hybrid_retrieval.py` |
| 9 | POST /ingest_pdf endpoint | `routers/ingest.py` |
| 10 | POST /query + GET /document/signed_url | `routers/query.py` |
| 11 | Graph router stubs | `routers/graph.py` |
| 12 | Docker compose + Vertex AI init | `docker-compose.yml`, `main.py` |
