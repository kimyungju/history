"""Vertex AI text-embedding service for the Colonial Archives Graph-RAG backend."""

import asyncio
import logging

from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from app.config.settings import settings
from app.models.schemas import Chunk

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 250  # Vertex AI limit per request


class EmbeddingsService:
    """Wraps the Vertex AI TextEmbeddingModel for chunk and query embedding."""

    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = TextEmbeddingModel.from_pretrained(settings.VERTEX_EMBED_MODEL)
            logger.info(
                "EmbeddingsService initialised with model=%s", settings.VERTEX_EMBED_MODEL
            )
        return self._model

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Embed a list of Chunk objects for document retrieval.

        Extracts the text from each chunk and delegates to embed_texts with
        task_type ``RETRIEVAL_DOCUMENT``.
        """
        texts = [chunk.text for chunk in chunks]
        logger.info("Embedding %d chunks", len(texts))
        return await self.embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for retrieval.

        Returns a flat list of floats (the embedding vector).
        """
        logger.info("Embedding query (%d chars)", len(query))
        results = await self.embed_texts([query], task_type="RETRIEVAL_QUERY")
        return results[0]

    async def embed_texts(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """Batch-embed a list of raw text strings.

        Texts are processed in batches of ``EMBEDDING_BATCH_SIZE`` to stay
        within the Vertex AI per-request limit.  The blocking
        ``model.get_embeddings`` call is offloaded to a thread via
        ``run_in_executor``.
        """
        all_vectors: list[list[float]] = []
        loop = asyncio.get_event_loop()

        for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + EMBEDDING_BATCH_SIZE]
            inputs = [
                TextEmbeddingInput(text=t, task_type=task_type) for t in batch
            ]

            logger.debug(
                "Requesting embeddings for batch %d-%d / %d",
                start,
                start + len(batch),
                len(texts),
            )

            embeddings = await loop.run_in_executor(
                None, self.model.get_embeddings, inputs
            )
            all_vectors.extend([e.values for e in embeddings])

        logger.info(
            "Produced %d embedding vectors (dim=%d)",
            len(all_vectors),
            len(all_vectors[0]) if all_vectors else 0,
        )
        return all_vectors


embeddings_service = EmbeddingsService()
