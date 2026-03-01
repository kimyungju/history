"""Entity extraction service using Gemini structured JSON output.

Extracts entities (persons, organizations, locations, events, etc.) and
relationships from OCR text chunks of colonial-era archive documents.
"""

from __future__ import annotations

import asyncio
import json
import logging

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from app.config.settings import settings
from app.models.schemas import (
    MAIN_CATEGORIES,
    Chunk,
    EntityExtractionResult,
    Evidence,
)

logger = logging.getLogger(__name__)

ENTITY_EXTRACTION_PROMPT = """You are an expert historian specializing in colonial-era archives. Extract all named entities and relationships from the following document text.

Document ID: {doc_id}
Chunk ID: {chunk_id}
Pages: {pages}
Document categories: {categories}

Text:
\"\"\"
{text}
\"\"\"

Instructions:
1. Extract every named entity (person, organization, location, event, policy, concept, etc.).
2. For each entity, provide:
   - "name": the canonical name as it appears in the text
   - "main_categories": one or two from ONLY this list: {main_categories}
   - "sub_category": a more specific type you infer (e.g., "Trade Official", "Military Fort", "Shipping Company")
   - "attributes": key-value pairs of notable properties (role, title, date, location, etc.)
   - "evidence": the exact text span where this entity is mentioned, plus your confidence (0.0-1.0)
3. Extract relationships between entities:
   - "from_entity": name of source entity (must match an entity name above)
   - "to_entity": name of target entity (must match an entity name above)
   - "type": a verb phrase in UPPER_SNAKE_CASE (e.g., "ADMINISTERED", "TRADED_WITH", "GOVERNED")
   - "attributes": contextual details (period, nature, etc.)
   - "evidence": the exact text span supporting this relationship, plus confidence
4. Only extract entities and relationships explicitly stated in the text. Never infer or guess.
5. Set confidence below 0.5 for anything uncertain.

Respond with valid JSON matching this exact schema:
{{
  "entities": [
    {{
      "name": "string",
      "main_categories": ["string"],
      "sub_category": "string or null",
      "attributes": {{}},
      "evidence": {{
        "doc_id": "{doc_id}",
        "page": <first page number>,
        "text_span": "exact quote from text",
        "chunk_id": "{chunk_id}",
        "confidence": 0.0-1.0
      }}
    }}
  ],
  "relationships": [
    {{
      "from_entity": "string",
      "to_entity": "string",
      "type": "UPPER_SNAKE_CASE_VERB",
      "attributes": {{}},
      "evidence": {{
        "doc_id": "{doc_id}",
        "page": <first page number>,
        "text_span": "exact quote from text",
        "chunk_id": "{chunk_id}",
        "confidence": 0.0-1.0
      }}
    }}
  ]
}}

Return ONLY the JSON object, no additional text."""


class EntityExtractionService:
    """Extracts entities and relationships from text chunks using Gemini."""

    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        if self._model is None:
            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.VERTEX_LLM_REGION,
            )
            self._model = GenerativeModel(settings.VERTEX_LLM_MODEL)
            logger.info(
                "EntityExtractionService initialised with model=%s in %s",
                settings.VERTEX_LLM_MODEL,
                settings.VERTEX_LLM_REGION,
            )
        return self._model

    async def extract_from_chunks(
        self,
        chunks: list[Chunk],
        doc_id: str,
    ) -> EntityExtractionResult:
        """Extract entities and relationships from a list of chunks.

        Processes each chunk individually and aggregates results.  A failure
        in one chunk does not prevent extraction from the remaining chunks.
        """
        all_entities: list[EntityExtractionResult.ExtractedEntity] = []
        all_relationships: list[EntityExtractionResult.ExtractedRelationship] = []

        for chunk in chunks:
            try:
                result = await self._extract_from_chunk(chunk)
                all_entities.extend(result.entities)
                all_relationships.extend(result.relationships)
            except Exception:
                logger.warning(
                    "Entity extraction failed for chunk %s; skipping",
                    chunk.chunk_id,
                    exc_info=True,
                )

        # Filter by confidence threshold
        min_confidence = settings.ENTITY_CONFIDENCE_MIN
        all_entities = [
            e for e in all_entities if e.evidence.confidence >= min_confidence
        ]
        all_relationships = [
            r for r in all_relationships if r.evidence.confidence >= min_confidence
        ]

        logger.info(
            "Extracted %d entities and %d relationships from %d chunks (doc_id=%s)",
            len(all_entities),
            len(all_relationships),
            len(chunks),
            doc_id,
        )

        return EntityExtractionResult(
            entities=all_entities,
            relationships=all_relationships,
        )

    async def _extract_from_chunk(
        self,
        chunk: Chunk,
    ) -> EntityExtractionResult:
        """Extract entities and relationships from a single chunk via Gemini."""
        prompt = ENTITY_EXTRACTION_PROMPT.format(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            pages=chunk.pages,
            categories=chunk.categories,
            text=chunk.text,
            main_categories=MAIN_CATEGORIES,
        )

        generation_config = GenerationConfig(
            temperature=0.1,
            max_output_tokens=4096,
            response_mime_type="application/json",
        )

        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(
                prompt,
                generation_config=generation_config,
            ),
        )

        raw_text = response.text.strip()
        data = json.loads(raw_text)

        # Parse entities
        entities: list[EntityExtractionResult.ExtractedEntity] = []
        for ent in data.get("entities", []):
            evidence_data = ent.get("evidence", {})
            entities.append(
                EntityExtractionResult.ExtractedEntity(
                    name=ent["name"],
                    main_categories=ent.get("main_categories", []),
                    sub_category=ent.get("sub_category"),
                    attributes=ent.get("attributes", {}),
                    evidence=Evidence(
                        doc_id=evidence_data.get("doc_id", chunk.doc_id),
                        page=evidence_data.get("page", chunk.pages[0] if chunk.pages else 1),
                        text_span=evidence_data.get("text_span", ""),
                        chunk_id=evidence_data.get("chunk_id", chunk.chunk_id),
                        confidence=float(evidence_data.get("confidence", 0.5)),
                    ),
                )
            )

        # Parse relationships
        relationships: list[EntityExtractionResult.ExtractedRelationship] = []
        for rel in data.get("relationships", []):
            evidence_data = rel.get("evidence", {})
            relationships.append(
                EntityExtractionResult.ExtractedRelationship(
                    from_entity=rel["from_entity"],
                    to_entity=rel["to_entity"],
                    type=rel["type"],
                    attributes=rel.get("attributes", {}),
                    evidence=Evidence(
                        doc_id=evidence_data.get("doc_id", chunk.doc_id),
                        page=evidence_data.get("page", chunk.pages[0] if chunk.pages else 1),
                        text_span=evidence_data.get("text_span", ""),
                        chunk_id=evidence_data.get("chunk_id", chunk.chunk_id),
                        confidence=float(evidence_data.get("confidence", 0.5)),
                    ),
                )
            )

        logger.debug(
            "Chunk %s: extracted %d entities, %d relationships",
            chunk.chunk_id,
            len(entities),
            len(relationships),
        )

        return EntityExtractionResult(
            entities=entities,
            relationships=relationships,
        )


# Module-level singleton
entity_extraction_service = EntityExtractionService()
