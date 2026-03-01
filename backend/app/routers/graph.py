"""Graph API router for the Colonial Archives Graph-RAG backend.

Provides endpoints for entity subgraph retrieval and entity search
backed by Neo4j.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import GraphNode, GraphPayload
from app.services.neo4j_service import neo4j_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/search", response_model=list[GraphNode])
async def graph_search(
    q: str,
    limit: int = Query(default=20, ge=1, le=100),
    categories: list[str] | None = Query(default=None),
) -> list[GraphNode]:
    """Search entities by name or alias.

    Returns a list of matching ``GraphNode`` objects ordered by confidence.
    """
    results = await neo4j_service.search_entities(
        q, limit=limit, categories=categories
    )
    return results


@router.get("/{entity_canonical_id}", response_model=GraphPayload)
async def get_entity(
    entity_canonical_id: str,
    categories: list[str] | None = Query(default=None),
) -> GraphPayload:
    """Get the subgraph surrounding an entity.

    Returns a ``GraphPayload`` with nodes, edges, and the center node ID.
    Raises 404 if the entity does not exist.
    """
    payload = await neo4j_service.get_subgraph(
        entity_canonical_id, categories=categories
    )
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_canonical_id}' not found",
        )
    return payload
