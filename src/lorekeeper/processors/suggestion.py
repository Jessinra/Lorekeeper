"""SuggestionProcessor — orchestrates link recommendation, pending list, and review.

Consolidates the batch loop that was duplicated between
``api/mcp/handlers/suggestion_handlers.py`` and
``dashboard/routes/suggestions.py`` into a single place.

Lives in the processors layer (between presentation and domains) and owns
validation, metrics, and commit boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.link.models import RELATION_TYPES

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.candidate import LinkCandidate
    from lorekeeper.domains.suggestion.models import LinkSuggestion
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
    from lorekeeper.domains.suggestion.service import SuggestionService
    from lorekeeper.infra.database import Database
    from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()

_MAX_SUGGESTIONS_LIMIT = 100
_VALID_REVIEW_ACTIONS = {"accept", "reject"}


@dataclass
class ReviewResult:
    """Result of a batch suggestion review — not serialized, no Pydantic."""

    results: list[dict[str, Any]] = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


class SuggestionProcessor:
    """Orchestrates link recommendation, pending-suggestion listing, and review.

    Single home for the batch accept/reject loop that was previously duplicated
    across MCP and dashboard presentation layers.
    """

    def __init__(
        self,
        suggestion_service: SuggestionService,
        suggestions: LinkSuggestionStore,
        metrics: MetricsStore,
        db: Database,
    ) -> None:
        self._suggestion_service = suggestion_service
        self._suggestions = suggestions
        self._metrics = metrics
        self._db = db

    # ── recommend_links ──────────────────────────────────────────────────────

    def recommend_links(
        self,
        lore_id: str,
        top_k: int | None = None,
    ) -> list[LinkCandidate]:
        """Return link candidates for a source memory.

        Validates input before reaching the domain service.
        Metric increment is owned by the domain service.
        """
        if not lore_id or not lore_id.strip():
            raise ValueError("lore_id is required")
        if top_k is not None:
            if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
                raise ValueError("top_k must be a positive integer")
            top_k = min(top_k, 50)  # hard cap
        return self._suggestion_service.recommend_links(
            lore_id=lore_id, top_k=top_k
        )

    # ── get_pending ──────────────────────────────────────────────────────────

    def get_pending(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> tuple[list[LinkSuggestion], int]:
        """Return pending suggestions and total count.

        Validates input, increments the metric, then delegates to the store.
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        limit = min(limit, _MAX_SUGGESTIONS_LIMIT)
        if not (0.0 <= min_score <= 1.0):
            raise ValueError("min_score must be between 0.0 and 1.0")

        self._metrics.increment_metric_safe("lore_get_suggestions")
        items = self._suggestions.get_pending_suggestions(
            limit=limit, min_score=min_score
        )
        total = self._suggestions.count_pending_suggestions()
        return items, total

    # ── list_pending / count_pending (dashboard pagination) ─────────────────

    def list_pending(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "weighted_score",
        sort_dir: str = "desc",
        memory_id: str | None = None,
        status: str = "pending",
    ) -> tuple[list[LinkSuggestion], int]:
        """Return a page of pending suggestions and the total matching count.

        Validates pagination/sort params (whitelist), then delegates to the
        store — optionally scoped to a single memory. Moved from
        ``dashboard/routes/suggestions.py::list_suggestions`` so the route
        no longer reaches into ``LinkSuggestionStore`` directly.
        """
        if not (1 <= limit <= 500):
            raise ValueError("limit must be between 1 and 500")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        if sort_by not in ("weighted_score", "created_at"):
            sort_by = "weighted_score"
        order = "ASC" if sort_dir.lower() == "asc" else "DESC"

        if memory_id:
            if status == "pending":
                total = self._suggestions.count_pending_suggestions_for_memory(memory_id)
            else:
                total = 0
            page = self._suggestions.get_suggestions_for_memory_paged(
                memory_id,
                status=status,
                sort_by=sort_by,
                sort_dir=order,
                limit=limit,
                offset=offset,
            )
        else:
            total = self._suggestions.count_suggestions_by_status(status)
            page = self._suggestions.get_pending_suggestions(
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_dir=order,
                status=status,
            )
        return page, total

    def count_pending(self, memory_id: str | None = None) -> int:
        """Return total pending suggestion count, optionally scoped to a memory."""
        if memory_id:
            return self._suggestions.count_pending_suggestions_for_memory(memory_id)
        return self._suggestions.count_pending_suggestions()

    # ── review (THE single batch loop) ───────────────────────────────────────

    def review(
        self,
        suggestion_ids: list[str],
        action: str,
    ) -> ReviewResult:
        """Accept or reject multiple suggestions in one call.

        This is THE single batch loop, unified from the two earlier
        implementations (MCP handler and dashboard route).  Semantics:
        - Not-found suggestions → ``skipped`` (MCP behaviour wins)
        - Conditional commit — only if at least one item was accepted or rejected
        - ``accept_one`` uses a SAVEPOINT per item so one failure doesn't
          poison already-processed items
        """
        if not suggestion_ids:
            raise ValueError("suggestion_ids must not be empty")
        if action not in _VALID_REVIEW_ACTIONS:
            raise ValueError(
                f"action must be 'accept' or 'reject', got {action!r}"
            )

        cleaned = [
            sid.strip() for sid in suggestion_ids if sid and sid.strip()
        ]
        if not cleaned:
            raise ValueError("suggestion_ids contained only empty strings")

        self._metrics.increment_metric_safe("lore_review_suggestion")

        result = ReviewResult()

        for sid in cleaned:
            try:
                sug = self._suggestions.get_suggestion(sid)

                if action == "accept":
                    if sug is None:
                        result.skipped += 1
                        result.results.append({
                            "id": sid,
                            "status": "skipped",
                            "link_id": None,
                            "message": "Suggestion not found",
                        })
                        continue
                    if sug.status == "accepted":
                        result.skipped += 1
                        result.results.append({
                            "id": sid,
                            "status": "skipped",
                            "link_id": None,
                            "message": "Already accepted",
                        })
                        continue

                    rel_type = sug.suggested_type
                    if rel_type not in RELATION_TYPES:
                        rel_type = "references"

                    link = self._suggestion_service.accept_one(
                        self._suggestions,
                        sug,
                        rel_type,
                        "Accepted from link suggestion sweep",
                    )

                    result.accepted += 1
                    result.results.append({
                        "id": sid,
                        "status": "accepted",
                        "link_id": link.id,
                        "message": "Link created",
                    })

                else:  # action == "reject"
                    if sug is None:
                        result.skipped += 1
                        result.results.append({
                            "id": sid,
                            "status": "skipped",
                            "link_id": None,
                            "message": "Suggestion not found",
                        })
                        continue
                    if sug.status in ("rejected", "accepted"):
                        result.skipped += 1
                        msg = (
                            "Already rejected"
                            if sug.status == "rejected"
                            else "Already accepted (cannot reject)"
                        )
                        result.results.append({
                            "id": sid,
                            "status": "skipped",
                            "link_id": None,
                            "message": msg,
                        })
                        continue

                    self._suggestions.update_suggestion_status(
                        sid, "rejected"
                    )
                    result.rejected += 1
                    result.results.append({
                        "id": sid,
                        "status": "rejected",
                        "link_id": None,
                        "message": "Suggestion rejected",
                    })

            except Exception as exc:
                log.warning(
                    "review_suggestion_item_failed",
                    suggestion_id=sid,
                    exc_info=True,
                )
                result.errors.append({"id": sid, "error": str(exc)})
                result.results.append({
                    "id": sid,
                    "status": "error",
                    "link_id": None,
                    "message": str(exc),
                })

        if result.accepted or result.rejected:
            self._db.commit()

        return result
