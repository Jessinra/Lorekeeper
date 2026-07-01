"""MCP handlers for the Suggestion domain — recommend links, review suggestions.

Extracted from handlers.py (LKPR-104 Phase 6a). Input sanitization and
validation happen here, before reaching the domain service.

Note: handle_review_suggestion still reaches into svc._conn directly for the
per-item SAVEPOINT (accept path) — this is the same transaction-boundary
violation flagged for dashboard/routes/suggestions.py. Fixing it is deferred
to Phase 6b (a behavior-preserving bug fix, kept separate from this
mechanical handler split) — it will route through
SuggestionService.accept_batch()/reject_batch() using Database.transaction()
instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.link.models import RELATION_TYPES
from lorekeeper.shared.serializers import serialize_link_candidate, serialize_suggestion

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
    from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()

_MAX_SUGGESTIONS_LIMIT = 100
_VALID_REVIEW_ACTIONS = {"accept", "reject"}


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
