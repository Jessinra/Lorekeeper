"""Shared serializers for Memory, MemoryLink, and SearchResult.

Each endpoint accepts keyword arguments to customize output:
- truncation for content field
- field exclusion (omit created_at/updated_at from dashboard list view)
- relevance score rounding
- omit links, omit decay_factor

Adding a new field to Memory/MemoryLink/SearchResult now requires
touching only this file — not handlers.py AND dashboard/app.py.
"""

from typing import Any

from lorekeeper.models import Memory, MemoryLink
from lorekeeper.services.search import SearchResult


def serialize_memory(
    memory: Memory,
    *,
    truncate_content: int | None = None,
    exclude_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Serialize a Memory model to a dict.

    Args:
        memory: The Memory instance to serialize.
        truncate_content: If set, truncates content to this many chars.
        exclude_fields: Set of field names to omit from output.
    """
    content = memory.content[:truncate_content] if truncate_content is not None else memory.content
    result: dict[str, Any] = {
        "id": memory.id,
        "title": memory.title,
        "description": memory.description,
        "content": content,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
        "usage_count": memory.usage_count,
        "score": memory.score,
        "soft_deleted": memory.soft_deleted,
        "confidence": memory.confidence,
        "confidence_count": memory.confidence_count,
    }
    if exclude_fields:
        for field in exclude_fields:
            result.pop(field, None)
    return result


def serialize_memory_link(link: MemoryLink) -> dict[str, Any]:
    """Serialize a MemoryLink to a dict (no optional overrides — shape is stable)."""
    return {
        "id": link.id,
        "source_memory_id": link.source_memory_id,
        "target_memory_id": link.target_memory_id,
        "relation_type": link.relation_type,
        "reason": link.reason,
        "score": link.score,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
        "usage_count": link.usage_count,
        "confidence": link.confidence,
        "confidence_count": link.confidence_count,
    }


def serialize_search_result(
    result: SearchResult,
    *,
    truncate_content: int | None = None,
    exclude_memory_fields: set[str] | None = None,
    exclude_relevance_fields: set[str] | None = None,
    round_relevance: int | None = None,
    include_links: bool = True,
) -> dict[str, Any]:
    """Serialize a SearchResult to a dict.

    Composes serialize_memory + serialize_memory_link, adding relevance.

    Args:
        result: The SearchResult to serialize.
        truncate_content: Passed through to serialize_memory.
        exclude_memory_fields: Passed through to serialize_memory.
        exclude_relevance_fields: Set of relevance sub-fields to omit.
        round_relevance: If set, round relevance scores to this many places.
        include_links: If False, omit the links array from output.
    """
    mem_dict = serialize_memory(
        result.memory,
        truncate_content=truncate_content,
        exclude_fields=exclude_memory_fields,
    )

    relevance: dict[str, Any] = {
        "combined_score": result.combined_score,
        "semantic_score": result.semantic_score,
        "keyword_score": result.keyword_score,
        "decay_factor": result.decay_factor,
    }
    if exclude_relevance_fields:
        for field in exclude_relevance_fields:
            relevance.pop(field, None)
    if round_relevance is not None:
        relevance = {k: round(v, round_relevance) for k, v in relevance.items()}

    output: dict[str, Any] = {
        "memory": mem_dict,
        "relevance": relevance,
    }

    if include_links:
        output["links"] = [serialize_memory_link(lnk) for lnk in result.links]

    return output
