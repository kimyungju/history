"""Query router -- Q&A and document signed-URL endpoints."""

from fastapi import APIRouter

from app.config.settings import settings
from app.models.schemas import QueryRequest, QueryResponse, SignedUrlResponse
from app.services.hybrid_retrieval import hybrid_retrieval_service
from app.services.storage import storage_service

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Run a hybrid retrieval query and return the answer with citations."""
    return await hybrid_retrieval_service.query(
        question=request.question,
        filter_categories=request.filter_categories,
    )


@router.get("/document/signed_url", response_model=SignedUrlResponse)
async def document_signed_url(doc_id: str, page: int = 1) -> SignedUrlResponse:
    """Generate a temporary signed URL for a document PDF."""
    pdf_url = storage_service.get_pdf_url(doc_id)
    signed_url = storage_service.generate_signed_url(pdf_url)
    return SignedUrlResponse(
        url=signed_url,
        expires_in=settings.SIGNED_URL_EXPIRY_MINUTES * 60,
    )
