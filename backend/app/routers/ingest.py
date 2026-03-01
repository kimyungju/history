"""Ingestion router for the Colonial Archives Graph-RAG backend.

Provides endpoints for PDF ingestion (OCR -> chunking -> embedding -> vector upsert)
with background processing and job status tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config.logging_config import log_stage
from app.config.settings import settings
from app.models.schemas import (
    Chunk,
    IngestRequest,
    IngestResponse,
    OcrConfidenceWarning,
    RetryEntitiesRequest,
    RetryEntitiesResponse,
)
from app.services.auto_classification import auto_classification_service
from app.services.chunking import chunking_service
from app.services.embeddings import embeddings_service
from app.services.entity_extraction import entity_extraction_service
from app.services.entity_normalization import normalization_service
from app.services.neo4j_service import neo4j_service
from app.services.ocr import ocr_service
from app.services.storage import storage_service
from app.services.vector_search import vector_search_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

# ---------------------------------------------------------------------------
# In-memory job tracking (Phase 1 only)
# ---------------------------------------------------------------------------

_jobs: dict[str, IngestResponse] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_document_categories() -> dict[str, list[str]]:
    """Load document-to-category mapping from ``document_categories.json``.

    Keys starting with ``_`` (comments, examples) are filtered out.
    Returns an empty dict if the file is not found.
    """
    categories_path = Path(__file__).parent.parent / "config" / "document_categories.json"
    if not categories_path.exists():
        logger.warning("document_categories.json not found at %s", categories_path)
        return {}

    try:
        with open(categories_path, "r", encoding="utf-8") as f:
            raw: dict = json.load(f)
    except Exception:
        logger.exception("Failed to load document_categories.json")
        return {}

    return {k: v for k, v in raw.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Background ingestion pipeline
# ---------------------------------------------------------------------------


async def _run_ingestion(job_id: str, pdf_url: str, doc_id: str) -> None:
    """Execute the full ingestion pipeline in the background.

    Steps:
        1. Download PDF from GCS.
        2. OCR via Document AI.
        3. Resolve document categories.
        4. Clean and chunk OCR output.
        5. Embed chunks via Vertex AI.
        6. Upsert embeddings into Vector Search.
        7. Entity extraction via Gemini (Phase 2).
        8. Entity normalization (Phase 2).
        9. Neo4j MERGE — entities and relationships (Phase 2).
    """
    job = _jobs[job_id]

    try:
        # ---- Step 1: Download PDF -------------------------------------------
        with log_stage("pdf_download", logger=logger, job_id=job_id, doc_id=doc_id):
            loop = asyncio.get_event_loop()
            pdf_bytes = await loop.run_in_executor(
                None, storage_service.read_pdf_bytes, pdf_url
            )

        # ---- Step 2: OCR ----------------------------------------------------
        with log_stage("ocr", logger=logger, job_id=job_id, doc_id=doc_id):
            ocr_result = await ocr_service.process_pdf(pdf_bytes, doc_id)

            job.pages_total = len(ocr_result.pages)

            # Store raw OCR output to GCS
            ocr_data = [
                {
                    "page_number": p.page_number,
                    "text": p.text,
                    "confidence": p.confidence,
                }
                for p in ocr_result.pages
            ]
            await loop.run_in_executor(
                None, storage_service.upload_json, f"ocr/{doc_id}_ocr.json", ocr_data
            )
            logger.info("[%s] Stored OCR JSON to ocr/%s_ocr.json", job_id, doc_id)

            # Flag low-confidence pages
            for page in ocr_result.pages:
                if page.confidence < settings.OCR_CONFIDENCE_FLAG:
                    job.ocr_confidence_warnings.append(
                        OcrConfidenceWarning(
                            page=page.page_number,
                            confidence=page.confidence,
                        )
                    )

            if job.ocr_confidence_warnings:
                logger.warning(
                    "[%s] %d page(s) below OCR confidence threshold (%.2f)",
                    job_id,
                    len(job.ocr_confidence_warnings),
                    settings.OCR_CONFIDENCE_FLAG,
                )

        # ---- Step 3: Resolve categories -------------------------------------
        with log_stage("category_resolution", logger=logger, job_id=job_id, doc_id=doc_id):
            categories_map = _load_document_categories()

            # Derive the PDF filename from the URL for the primary lookup
            blob_name = storage_service._parse_blob_name(pdf_url)
            pdf_filename = PurePosixPath(blob_name).name

            categories: list[str] = categories_map.get(
                pdf_filename, categories_map.get(doc_id, [])
            )

            if not categories:
                # Phase 4: Auto-classify using first-page OCR text.
                logger.info(
                    "[%s] No manual categories for %s — running auto-classification",
                    job_id,
                    pdf_filename,
                )
                first_page_text = ocr_result.pages[0].text if ocr_result.pages else ""
                if first_page_text:
                    category, confidence = await auto_classification_service.classify(
                        first_page_text
                    )
                    if confidence >= settings.CLASSIFICATION_CONFIDENCE_MIN:
                        categories = [category]
                        logger.info(
                            "[%s] Auto-classified as '%s' (confidence=%.2f)",
                            job_id,
                            category,
                            confidence,
                        )
                    else:
                        categories = [category]
                        logger.warning(
                            "[%s] Auto-classified as '%s' with LOW confidence "
                            "%.2f (threshold=%.2f) — flagged for review",
                            job_id,
                            category,
                            confidence,
                            settings.CLASSIFICATION_CONFIDENCE_MIN,
                        )
                else:
                    logger.warning("[%s] No OCR text for auto-classification", job_id)

        # ---- Step 4: Chunk ---------------------------------------------------
        with log_stage("chunking", logger=logger, job_id=job_id, doc_id=doc_id):
            chunks = chunking_service.clean_and_chunk(ocr_result.pages, doc_id, categories)

            job.chunks_processed = len(chunks)

            # Store chunks to GCS
            chunks_data = [chunk.model_dump() for chunk in chunks]
            await loop.run_in_executor(
                None, storage_service.upload_json, f"chunks/{doc_id}.json", chunks_data
            )
            logger.info("[%s] Stored %d chunks to chunks/%s.json", job_id, len(chunks), doc_id)

        # ---- Step 5: Embed ---------------------------------------------------
        with log_stage("embedding", logger=logger, job_id=job_id, doc_id=doc_id):
            embeddings = await embeddings_service.embed_chunks(chunks)

        # ---- Step 6: Upsert to Vector Search ---------------------------------
        with log_stage("vector_upsert", logger=logger, job_id=job_id, doc_id=doc_id):
            await vector_search_service.upsert(chunks, embeddings)

        # ---- Steps 7-9: Entity extraction + normalization + Neo4j MERGE ------
        # Wrapped in try/except so graph failures do NOT block vector ingestion.
        try:
            # Step 7: Entity extraction
            with log_stage("entity_extraction", logger=logger, job_id=job_id, doc_id=doc_id):
                extraction_result = await entity_extraction_service.extract_from_chunks(
                    chunks, doc_id
                )

            # Step 8: Entity normalization
            with log_stage("entity_normalization", logger=logger, job_id=job_id, doc_id=doc_id):
                normalized = await normalization_service.normalize(
                    extraction_result.entities, neo4j_service
                )

            # Build a mapping from entity name -> canonical_id for relationship wiring
            name_to_canonical: dict[str, str] = {}
            for norm_entity in normalized:
                name_to_canonical[norm_entity.extracted.name] = norm_entity.canonical_id

            # Step 9: Neo4j MERGE — entities and relationships
            with log_stage("neo4j_merge", logger=logger, job_id=job_id, doc_id=doc_id):
                # Step 9a: MERGE entities into Neo4j
                entity_count = 0
                for norm_entity in normalized:
                    ent = norm_entity.extracted
                    aliases = [ent.name] if not norm_entity.is_new else []
                    await neo4j_service.merge_entity(
                        canonical_id=norm_entity.canonical_id,
                        name=ent.name if norm_entity.is_new else ent.name,
                        main_categories=ent.main_categories,
                        sub_category=ent.sub_category,
                        aliases=aliases,
                        attributes=ent.attributes,
                        evidence=ent.evidence,
                    )
                    entity_count += 1

                # Step 9b: MERGE relationships into Neo4j
                rel_count = 0
                for rel in extraction_result.relationships:
                    source_id = name_to_canonical.get(rel.from_entity)
                    target_id = name_to_canonical.get(rel.to_entity)
                    if source_id and target_id:
                        await neo4j_service.merge_relationship(
                            source_canonical_id=source_id,
                            target_canonical_id=target_id,
                            rel_type=rel.type,
                            attributes=rel.attributes,
                            evidence=rel.evidence,
                        )
                        rel_count += 1
                    else:
                        logger.debug(
                            "[%s] Skipping relationship %s->%s: entity not found in normalized set",
                            job_id,
                            rel.from_entity,
                            rel.to_entity,
                        )

            job.entities_extracted = entity_count
            logger.info(
                "[%s] Graph integration complete: %d entities, %d relationships",
                job_id,
                entity_count,
                rel_count,
            )

        except Exception:
            logger.exception(
                "[%s] Graph integration failed for doc_id=%s (vector ingestion succeeded)",
                job_id,
                doc_id,
            )

        # ---- Done ------------------------------------------------------------
        job.status = "done"
        logger.info("[%s] Ingestion complete for doc_id=%s", job_id, doc_id)

    except Exception:
        logger.exception("[%s] Ingestion failed for doc_id=%s", job_id, doc_id)
        job.status = "failed"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest_pdf", response_model=IngestResponse)
async def ingest_pdf(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestResponse:
    """Start PDF ingestion as a background task.

    Returns an ``IngestResponse`` with a ``job_id`` that can be polled via
    ``GET /ingest_status/{job_id}``.
    """
    job_id = str(uuid4())
    doc_id = storage_service.get_doc_id_from_url(request.pdf_url)

    job = IngestResponse(job_id=job_id, status="processing")
    _jobs[job_id] = job

    background_tasks.add_task(_run_ingestion, job_id, request.pdf_url, doc_id)

    logger.info("Ingestion job %s queued for doc_id=%s", job_id, doc_id)
    return job


@router.get("/ingest_status/{job_id}", response_model=IngestResponse)
async def ingest_status(job_id: str) -> IngestResponse:
    """Poll the status of an ingestion job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/retry_entities", response_model=RetryEntitiesResponse)
async def retry_entities(request: RetryEntitiesRequest) -> RetryEntitiesResponse:
    """Re-run entity extraction (steps 7-9) for a previously ingested document.

    Use this when vector ingestion succeeded but graph integration failed.
    Chunks must already exist in GCS at ``chunks/{doc_id}.json``.
    """
    doc_id = request.doc_id
    logger.info("Entity retry requested for doc_id=%s", doc_id)

    # Step 1: Download chunks from GCS
    with log_stage("chunk_download", logger=logger, doc_id=doc_id):
        loop = asyncio.get_event_loop()
        try:
            chunks_data = await loop.run_in_executor(
                None, storage_service.download_json, f"chunks/{doc_id}.json"
            )
        except Exception as exc:
            logger.error("Failed to download chunks for doc_id=%s: %s", doc_id, exc)
            raise HTTPException(
                status_code=404,
                detail=f"Chunks not found for doc_id={doc_id}. Has this document been ingested?",
            ) from exc

    # Step 2: Deserialize into Chunk objects
    chunks = [Chunk(**c) for c in chunks_data]
    logger.info("Loaded %d chunks for doc_id=%s", len(chunks), doc_id)

    # Step 3: Entity extraction
    with log_stage("entity_extraction", logger=logger, doc_id=doc_id):
        extraction_result = await entity_extraction_service.extract_from_chunks(chunks, doc_id)

    # Step 4: Entity normalization
    with log_stage("entity_normalization", logger=logger, doc_id=doc_id):
        normalized = await normalization_service.normalize(
            extraction_result.entities, neo4j_service
        )

    # Build name -> canonical_id mapping for relationship wiring
    name_to_canonical: dict[str, str] = {}
    for norm_entity in normalized:
        name_to_canonical[norm_entity.extracted.name] = norm_entity.canonical_id

    # Step 5: Neo4j MERGE — entities and relationships
    with log_stage("neo4j_merge", logger=logger, doc_id=doc_id):
        entity_count = 0
        for norm_entity in normalized:
            ent = norm_entity.extracted
            aliases = [ent.name] if not norm_entity.is_new else []
            await neo4j_service.merge_entity(
                canonical_id=norm_entity.canonical_id,
                name=ent.name if norm_entity.is_new else ent.name,
                main_categories=ent.main_categories,
                sub_category=ent.sub_category,
                aliases=aliases,
                attributes=ent.attributes,
                evidence=ent.evidence,
            )
            entity_count += 1

        rel_count = 0
        for rel in extraction_result.relationships:
            source_id = name_to_canonical.get(rel.from_entity)
            target_id = name_to_canonical.get(rel.to_entity)
            if source_id and target_id:
                await neo4j_service.merge_relationship(
                    source_canonical_id=source_id,
                    target_canonical_id=target_id,
                    rel_type=rel.type,
                    attributes=rel.attributes,
                    evidence=rel.evidence,
                )
                rel_count += 1
            else:
                logger.debug(
                    "Skipping relationship %s->%s: entity not found in normalized set",
                    rel.from_entity,
                    rel.to_entity,
                )

    logger.info(
        "Entity retry complete for doc_id=%s: %d entities, %d relationships",
        doc_id,
        entity_count,
        rel_count,
    )

    return RetryEntitiesResponse(
        doc_id=doc_id,
        entities_extracted=entity_count,
        relationships_extracted=rel_count,
    )
