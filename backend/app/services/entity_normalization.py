"""Entity normalization service for deduplicating and merging entities.

Uses a three-stage matching pipeline:
  1. Exact name match against existing Neo4j entities
  2. Embedding similarity (text-embedding-004 on entity names)
  3. Fuzzy string matching (rapidfuzz) for OCR spelling variants

Produces canonical IDs and alias-merge decisions so the graph stays clean.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.config.settings import settings
from app.models.schemas import EntityExtractionResult
from app.services.embeddings import embeddings_service

logger = logging.getLogger(__name__)


@dataclass
class NormalizedEntity:
    """Result of normalizing a single extracted entity."""

    extracted: EntityExtractionResult.ExtractedEntity
    canonical_id: str
    is_new: bool


class EntityNormalizationService:
    """Deduplicates extracted entities against the existing Neo4j graph."""

    async def normalize(
        self,
        extracted_entities: list[EntityExtractionResult.ExtractedEntity],
        neo4j_service,
    ) -> list[NormalizedEntity]:
        """Normalize a batch of extracted entities.

        For each entity, checks Neo4j for an existing match via three stages:
          1. Exact name match (case-insensitive)
          2. Embedding cosine similarity
          3. Fuzzy string match

        Returns a list of ``NormalizedEntity`` with canonical_id and is_new flag.
        """
        if not extracted_entities:
            return []

        results: list[NormalizedEntity] = []

        # Fetch all existing entities from Neo4j for comparison
        existing_entities = await neo4j_service.get_all_entity_names()

        # Pre-compute embeddings for new entity names
        new_names = [e.name for e in extracted_entities]
        new_embeddings = await embeddings_service.embed_texts(
            new_names, task_type="RETRIEVAL_DOCUMENT"
        )

        # Pre-compute embeddings for existing entity names (if any)
        existing_names = [e["name"] for e in existing_entities]
        existing_embeddings: list[list[float]] = []
        if existing_names:
            existing_embeddings = await embeddings_service.embed_texts(
                existing_names, task_type="RETRIEVAL_DOCUMENT"
            )

        for idx, entity in enumerate(extracted_entities):
            match = await self._find_match(
                entity,
                existing_entities,
                new_embeddings[idx],
                existing_names,
                existing_embeddings,
            )

            if match is not None:
                # Existing entity found — merge as alias
                results.append(
                    NormalizedEntity(
                        extracted=entity,
                        canonical_id=match["canonical_id"],
                        is_new=False,
                    )
                )
                logger.debug(
                    "Merged '%s' into existing entity '%s' (%s)",
                    entity.name,
                    match["name"],
                    match["canonical_id"],
                )
            else:
                # New entity — generate canonical_id
                canonical_id = await self._generate_canonical_id(
                    entity.name, neo4j_service
                )
                results.append(
                    NormalizedEntity(
                        extracted=entity,
                        canonical_id=canonical_id,
                        is_new=True,
                    )
                )
                # Add to existing pool so subsequent entities in this batch
                # can match against it
                existing_entities.append(
                    {"canonical_id": canonical_id, "name": entity.name, "aliases": []}
                )
                existing_names.append(entity.name)
                existing_embeddings.append(new_embeddings[idx])

                logger.debug(
                    "New entity '%s' assigned canonical_id=%s",
                    entity.name,
                    canonical_id,
                )

        new_count = sum(1 for r in results if r.is_new)
        merged_count = len(results) - new_count
        logger.info(
            "Normalized %d entities: %d new, %d merged",
            len(results),
            new_count,
            merged_count,
        )

        return results

    async def _find_match(
        self,
        entity: EntityExtractionResult.ExtractedEntity,
        existing_entities: list[dict],
        entity_embedding: list[float],
        existing_names: list[str],
        existing_embeddings: list[list[float]],
    ) -> dict | None:
        """Try to match an entity against existing graph nodes.

        Returns the matching existing entity dict, or None if no match.
        """
        if not existing_entities:
            return None

        name_lower = entity.name.lower().strip()

        # --- Stage 1: Exact name match (case-insensitive) ---
        for existing in existing_entities:
            if existing["name"].lower().strip() == name_lower:
                return existing
            # Also check aliases
            for alias in existing.get("aliases", []):
                if alias.lower().strip() == name_lower:
                    return existing

        # --- Stage 2: Embedding similarity ---
        best_sim = 0.0
        best_match_idx = -1

        for i, existing_emb in enumerate(existing_embeddings):
            sim = self._cosine_similarity(entity_embedding, existing_emb)
            if sim > best_sim:
                best_sim = sim
                best_match_idx = i

        if best_sim >= settings.ENTITY_SIMILARITY_THRESHOLD:
            logger.debug(
                "Embedding match: '%s' ~ '%s' (sim=%.3f)",
                entity.name,
                existing_names[best_match_idx],
                best_sim,
            )
            return existing_entities[best_match_idx]

        # --- Stage 3: Fuzzy string match ---
        best_fuzzy = 0.0
        best_fuzzy_idx = -1

        for i, existing in enumerate(existing_entities):
            # Compare against name and all aliases
            candidates = [existing["name"]] + existing.get("aliases", [])
            for candidate in candidates:
                score = fuzz.token_sort_ratio(name_lower, candidate.lower()) / 100.0
                if score > best_fuzzy:
                    best_fuzzy = score
                    best_fuzzy_idx = i

        # Use embedding threshold for fuzzy too — entities with high fuzzy
        # similarity AND moderate embedding similarity are likely matches
        if best_fuzzy >= settings.ENTITY_SIMILARITY_THRESHOLD and best_fuzzy_idx >= 0:
            logger.debug(
                "Fuzzy match: '%s' ~ '%s' (score=%.3f)",
                entity.name,
                existing_entities[best_fuzzy_idx]["name"],
                best_fuzzy,
            )
            return existing_entities[best_fuzzy_idx]

        return None

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    async def _generate_canonical_id(name: str, neo4j_service) -> str:
        """Generate a unique canonical_id from an entity name.

        Format: ``entity_{slug}_{counter}`` where slug is derived from the
        name and counter increments to avoid collisions.
        """
        # Slugify the name
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
        if not slug:
            slug = "unknown"
        # Keep slug reasonable length
        slug = slug[:50]

        # Check Neo4j for existing IDs with this slug prefix
        base_id = f"entity_{slug}"
        counter = 1
        candidate = f"{base_id}_{counter:03d}"

        existing_ids = await neo4j_service.get_entity_ids_with_prefix(base_id)
        existing_set = set(existing_ids)

        while candidate in existing_set:
            counter += 1
            candidate = f"{base_id}_{counter:03d}"

        return candidate


# Module-level singleton
normalization_service = EntityNormalizationService()
