"""MCP handler helpers — input sanitization, validation, and output formatting.

Extracted from server.py (LKPR-103) for independent testability.
Each handler receives svc: MemoryService as an explicit first parameter —
no global state dependency.

Non-handler code (boot, MCP tool decorators, module-level state) stays
in server.py. Everything that can be unit-tested lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.link.models import RELATION_TYPES
from lorekeeper.domains.memory.models import SOURCE_TYPES, WRITE_SOURCE_TYPES
from lorekeeper.serializers import (
    serialize_link_candidate,
    serialize_search_result,
    serialize_search_result_title,
    serialize_suggestion,
)
from lorekeeper.services.search import VALID_SORT_BY, parse_filter_dt

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
    from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()

# ── Search ──────────────────────────────────────────────────────────────────

_VALID_SEARCH_FORMATS = {"full", "title"}


def handle_search(
    svc: MemoryService,
    query: str = "",
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,
    format: str = "full",
    ids: list[str] | None = None,
    created_after: str | None = None,
    updated_after: str | None = None,
    sort_by: str = "relevance",
    source_type: str | None = None,
) -> dict[str, Any]:
    if format not in _VALID_SEARCH_FORMATS:
        raise ValueError(
            f"Unknown format {format!r}. Must be one of: {sorted(_VALID_SEARCH_FORMATS)}"
        )
    if sort_by not in VALID_SORT_BY:
        raise ValueError(
            f"Unknown sort_by {sort_by!r}. Must be one of: {sorted(VALID_SORT_BY)}"
        )
    if source_type is not None and source_type not in SOURCE_TYPES:
        raise ValueError(
            f"Unknown source_type {source_type!r}. Must be one of: {sorted(SOURCE_TYPES)}"
        )

    # Parse and validate timestamp filters up front — clear error before any DB work.
    dt_created_after = parse_filter_dt(created_after, "created_after") if created_after else None
    dt_updated_after = parse_filter_dt(updated_after, "updated_after") if updated_after else None

    # When ids provided — skip search pipeline, bulk SQL lookup
    if ids is not None:
        if not ids:
            return {"results": [], "total_matched": 0, "query": query}
        if len(ids) > svc.settings.max_search_ids:
            raise ValueError(
                f"ids exceeds cap of {svc.settings.max_search_ids} IDs "
                f"(got {len(ids)})"
            )
        results = svc.search_by_ids(
            ids,
            include_deleted=include_deleted,
            include_links=include_links and format != "title",
            created_after=dt_created_after,
            updated_after=dt_updated_after,
            sort_by=sort_by,
            source_type=source_type,
        )
        if format == "title":
            serialized = [serialize_search_result_title(r) for r in results]
        else:
            serialized = [serialize_search_result(r, include_links=include_links) for r in results]
        return {"results": serialized, "total_matched": len(serialized), "query": query}

    # Guard against empty query when ids is not provided
    if not query or not query.strip():
        raise ValueError("query is required when ids is not provided")

    if refine_from is not None and len(refine_from) > svc.settings.max_refine_from_ids:
        raise ValueError(
            f"refine_from exceeds cap of {svc.settings.max_refine_from_ids} IDs "
            f"(got {len(refine_from)})"
        )
    results = svc.search(
        query, limit, min_score, include_links, include_deleted,
        refine_from=refine_from,
        search_format=format,
        created_after=dt_created_after,
        updated_after=dt_updated_after,
        sort_by=sort_by,
        source_type=source_type,
    )
    if format == "title":
        serialized = [serialize_search_result_title(r) for r in results]
    else:
        serialized = [serialize_search_result(r, include_links=include_links) for r in results]
    return {"results": serialized, "total_matched": len(serialized), "query": query}


# ── Insert ──────────────────────────────────────────────────────────────────


def handle_insert(
    svc: MemoryService,
    memories: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    memories = memories or []
    links = links or []
    for i, m in enumerate(memories):
        if "title" not in m:
            raise ValueError(f"memory at index {i} is missing required field: 'title'")
        if "source_type" in m and m["source_type"] not in WRITE_SOURCE_TYPES:
            raise ValueError(
                f"memory at index {i} has invalid source_type {m['source_type']!r}. "
                f"Must be one of: {sorted(WRITE_SOURCE_TYPES)}"
            )
    return svc.insert(memories, links, force)


# ── Recommend links ─────────────────────────────────────────────────────────


def handle_recommend_links(
    svc: MemoryService,
    lore_id: str,
    top_k: int | None = None,
) -> dict[str, Any]:
    if not lore_id or not lore_id.strip():
        raise ValueError("lore_id is required")
    if top_k is not None:
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        top_k = min(top_k, 50)  # hard cap
    candidates = svc.recommend_links(
        lore_id=lore_id, top_k=top_k
    )
    return {
        "candidates": [serialize_link_candidate(c) for c in candidates],
        "count": len(candidates),
        "source_lore_id": lore_id,
    }


# ── Suggestions ─────────────────────────────────────────────────────────────

_MAX_SUGGESTIONS_LIMIT = 100
_VALID_REVIEW_ACTIONS = {"accept", "reject"}


def handle_get_suggestions(
    svc: MemoryService,
    suggestions: LinkSuggestionStore,
    limit: int = 20,
    min_score: float = 0.0,
) -> dict[str, Any]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    limit = min(limit, _MAX_SUGGESTIONS_LIMIT)
    if not (0.0 <= min_score <= 1.0):
        raise ValueError("min_score must be between 0.0 and 1.0")
    svc._increment_metric("lore_get_suggestions")
    items = suggestions.get_pending_suggestions(limit=limit, min_score=min_score)
    total = suggestions.count_pending_suggestions()
    return {
        "suggestions": [serialize_suggestion(s) for s in items],
        "count": len(items),
        "total_pending": total,
    }


def handle_review_suggestion(
    svc: MemoryService,
    suggestions: LinkSuggestionStore,
    suggestion_ids: list[str],
    action: str,
) -> dict[str, Any]:
    if not suggestion_ids:
        raise ValueError("suggestion_ids must not be empty")
    if action not in _VALID_REVIEW_ACTIONS:
        raise ValueError(
            f"action must be 'accept' or 'reject', got {action!r}"
        )
    cleaned = [sid.strip() for sid in suggestion_ids if sid and sid.strip()]
    if not cleaned:
        raise ValueError("suggestion_ids contained only empty strings")

    svc._increment_metric("lore_review_suggestion")

    results: list[dict[str, Any]] = []
    accepted = 0
    rejected = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for sid in cleaned:
        try:
            sug = suggestions.get_suggestion(sid)

            if action == "accept":
                if sug is None:
                    skipped += 1
                    results.append({
                        "id": sid, "status": "skipped",
                        "link_id": None,
                        "message": "Suggestion not found",
                    })
                    continue
                if sug.status == "accepted":
                    skipped += 1
                    results.append({
                        "id": sid, "status": "skipped",
                        "link_id": None,
                        "message": "Already accepted",
                    })
                    continue

                rel_type = sug.suggested_type
                if rel_type not in RELATION_TYPES:
                    rel_type = "references"

                # Use a savepoint so insert_link + update_suggestion_status are
                # atomic per item.  If update_suggestion_status fails after the
                # link row is written, the savepoint rollback prevents a
                # committed link with no status update.
                sp = f"accept_{sid.replace('-', '_')}"
                svc._conn.execute(f"SAVEPOINT {sp}")
                try:
                    link = svc.links.insert_link(
                        source_memory_id=sug.source_memory_id,
                        target_memory_id=sug.target_memory_id,
                        relation_type=rel_type,
                        reason="Accepted from link suggestion sweep",
                    )
                    suggestions.update_suggestion_status(sid, "accepted")
                except Exception:
                    svc._conn.execute(f"ROLLBACK TO {sp}")
                    raise
                else:
                    svc._conn.execute(f"RELEASE {sp}")

                accepted += 1
                results.append({
                    "id": sid, "status": "accepted",
                    "link_id": link.id,
                    "message": "Link created",
                })

            else:  # action == "reject"
                if sug is None:
                    skipped += 1
                    results.append({
                        "id": sid, "status": "skipped",
                        "link_id": None,
                        "message": "Suggestion not found",
                    })
                    continue
                if sug.status in ("rejected", "accepted"):
                    skipped += 1
                    msg = (
                        "Already rejected"
                        if sug.status == "rejected"
                        else "Already accepted (cannot reject)"
                    )
                    results.append({
                        "id": sid, "status": "skipped",
                        "link_id": None,
                        "message": msg,
                    })
                    continue

                suggestions.update_suggestion_status(sid, "rejected")
                rejected += 1
                results.append({
                    "id": sid, "status": "rejected",
                    "link_id": None,
                    "message": "Suggestion rejected",
                })

        except Exception as exc:
            log.warning("review_suggestion_item_failed", suggestion_id=sid, exc_info=True)
            errors.append({"id": sid, "error": str(exc)})
            results.append({
                "id": sid, "status": "error",
                "link_id": None,
                "message": str(exc),
            })

    if accepted or rejected:
        svc.commit()

    return {
        "results": results,
        "accepted": accepted,
        "rejected": rejected,
        "skipped": skipped,
        "errors": errors,
    }
