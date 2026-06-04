"""Shared serializers for Memory, MemoryLink, and SearchResult.

Each endpoint accepts keyword arguments to customize output:
- truncation for content field
- field exclusion (omit created_at/updated_at from dashboard list view)
- relevance score rounding
- omit links, omit decay_factor

Adding a new field to Memory/MemoryLink/SearchResult now requires
touching only this file — not handlers.py AND dashboard/app.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.models import Memory, MemoryLink
from lorekeeper.services.search import SearchResult

if TYPE_CHECKING:
    from lorekeeper.services.link_candidate import LinkCandidate


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
    result["namespace"] = memory.namespace
    result["last_used"] = memory.last_used
    if exclude_fields:
        for field in exclude_fields:
            result.pop(field, None)
    return result


def serialize_reflection(reflection: Any) -> dict[str, Any]:
    """Serialize a reflection SQLite row to a stable dict shape."""
    return {
        "id": reflection["id"],
        "created_at": reflection["created_at"],
        "session_count": reflection["session_count"],
        "lessons_learnt": reflection["lessons_learnt"],
        "good_patterns": reflection.get("good_patterns"),
        "user_profile_updates": reflection.get("user_profile_updates"),
        "factual_discoveries": reflection.get("factual_discoveries"),
        "summary": reflection["summary"],
        "memory_ids": reflection.get("memory_ids"),
    }


def serialize_session(session: Any) -> dict[str, Any]:
    """Serialize a session SQLite row to a stable dict shape."""
    return {
        "session_id": session["session_id"],
        "session_date": session.get("session_date"),
        "topic": session.get("topic"),
        "task_type": session.get("task_type"),
        "reviewed_at": session["reviewed_at"],
        "reflection_id": session.get("reflection_id"),
        "transcript": session.get("transcript"),
        "what_was_done": session.get("what_was_done"),
        "decisions": session.get("decisions"),
        "lessons_learnt": session.get("lessons_learnt"),
        "good_patterns": session.get("good_patterns"),
        "user_profile": session.get("user_profile"),
        "discoveries": session.get("discoveries"),
    }


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


def serialize_search_result_title(result: SearchResult) -> dict[str, Any]:
    """Serialize a SearchResult to a compact title-only dict (format='title').

    Returns flat {id, title, score} — no memory body, no relevance nesting.
    Score is rounded to 4 decimal places for token efficiency.
    """
    return {
        "id": result.memory.id,
        "title": result.memory.title,
        "score": round(result.combined_score, 4),
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


def serialize_link_candidate(candidate: LinkCandidate | dict[str, Any]) -> dict[str, Any]:
    """Serialize a LinkCandidate for MCP response."""
    if isinstance(candidate, dict):
        cand = candidate
    else:
        cand = {
            "source_lore_id": candidate.source_lore_id,
            "target_lore_id": candidate.target_lore_id,
            "weighted_score": candidate.weighted_score,
            "cosine_score": candidate.cosine_score,
            "bm25_score": candidate.bm25_score,
            "entity_score": candidate.entity_score,
            "temporal_score": candidate.temporal_score,
            "proposed_relation": candidate.proposed_relation,
            "classifier_confidence": candidate.classifier_confidence,
            "classifier_reasoning": candidate.classifier_reasoning,
        }

    result: dict[str, Any] = {
        "source_lore_id": cand["source_lore_id"],
        "target_lore_id": cand["target_lore_id"],
        "proposed_relation": cand["proposed_relation"],
        "weighted_score": round(cand["weighted_score"], 4),
        "scores": {
            "cosine": round(cand["cosine_score"], 4),
            "bm25": round(cand["bm25_score"], 4),
            "entity": round(cand["entity_score"], 4),
            "temporal": round(cand["temporal_score"], 4),
        },
    }

    confidence = cand.get("classifier_confidence", 0.0)
    if confidence > 0:
        result["classifier"] = {
            "confidence": round(confidence, 4),
            "reasoning": cand.get("classifier_reasoning", ""),
        }
    else:
        result["classifier"] = None

    return result
