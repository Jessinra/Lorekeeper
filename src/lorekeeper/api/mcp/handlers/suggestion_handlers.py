"""MCP handlers for the Suggestion domain — thin shims over SuggestionProcessor.

Input sanitization and validation now live in the processor layer.
These handlers only wire the processor result to the MCP output format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.shared.serializers import serialize_link_candidate, serialize_suggestion

if TYPE_CHECKING:
    from lorekeeper.processors.suggestion import SuggestionProcessor

log = structlog.get_logger()


def handle_recommend_links(
    processor: SuggestionProcessor,
    lore_id: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    candidates = processor.recommend_links(lore_id=lore_id, top_k=top_k)
    return {
        "candidates": [serialize_link_candidate(c) for c in candidates],
        "count": len(candidates),
        "source_lore_id": lore_id,
    }


def handle_get_suggestions(
    processor: SuggestionProcessor,
    limit: int = 20,
    min_score: float = 0.0,
) -> dict[str, Any]:
    items, total = processor.get_pending(limit=limit, min_score=min_score)
    return {
        "suggestions": [serialize_suggestion(s) for s in items],
        "count": len(items),
        "total_pending": total,
    }


def handle_review_suggestion(
    processor: SuggestionProcessor,
    suggestion_ids: list[str],
    action: str,
) -> dict[str, Any]:
    result = processor.review(
        suggestion_ids=suggestion_ids, action=action
    )
    return {
        "results": result.results,
        "accepted": result.accepted,
        "rejected": result.rejected,
        "skipped": result.skipped,
        "errors": result.errors,
    }
