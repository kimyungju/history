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


class RetryEntitiesRequest(BaseModel):
    doc_id: str  # e.g. "CO 273:550:1"


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


class RetryEntitiesResponse(BaseModel):
    doc_id: str
    entities_extracted: int
    relationships_extracted: int


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
