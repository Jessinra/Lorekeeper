"""MemoryProcessor — orchestrates search, insert, remember, update, forget, import.

Consolidates validation + metrics that were previously split between
``api/mcp/handlers/memory_handlers.py`` and the domain services.

Lives in the processors layer (between presentation and domains) and owns
validation, metrics, and commit boundaries.  Returns domain objects —
serialization is the caller's responsibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.memory.models import SOURCE_TYPES, WRITE_SOURCE_TYPES
from lorekeeper.domains.memory.ranking import VALID_SORT_BY, parse_filter_dt

if TYPE_CHECKING:
    from lorekeeper.domains.memory.import_service import ImportService
    from lorekeeper.domains.memory.ranking import SearchResult
    from lorekeeper.domains.memory.service import (
        MemorySearchService,
        MemoryWriteService,
    )
    from lorekeeper.infra.database import Database
    from lorekeeper.infra.settings import Settings
    from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()

_VALID_SEARCH_FORMATS = {"full", "title"}
_VALID_FORGET_REASONS = {"duplicate", "hallucinated", "outdated", "expired", "unspecified"}


class MemoryProcessor:
    """Orchestrates memory-domain operations — search, insert, remember, update, forget, import.

    Validates inputs, increments metrics, manages commit boundaries, then delegates
    to the appropriate domain service.  Returns domain objects (not serialized payloads).
    The caller (MCP handler, dashboard route) is responsible for serialization.
    """

    def __init__(
        self,
        search_service: MemorySearchService,
        write_service: MemoryWriteService,
        import_service: ImportService,
        metrics: MetricsStore,
        db: Database,
        settings: Settings,
    ) -> None:
        self._search_service = search_service
        self._write_service = write_service
        self._import_service = import_service
        self._metrics = metrics
        self._db = db
        self._settings = settings

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        limit: int | None = None,
        min_score: float = 0.1,
        include_links: bool = True,
        include_deleted: bool = False,
        refine_from: list[str] | None = None,
        search_format: str = "full",
        ids: list[str] | None = None,
        created_after: str | None = None,
        updated_after: str | None = None,
        sort_by: str = "relevance",
        source_type: str | None = None,
    ) -> list[SearchResult]:
        """Validate + route to search_by_ids or search, increment metric.

        Returns a list of ``SearchResult`` domain objects.  Serialization
        (format, links, etc.) is handled by the caller.
        """
        if search_format not in _VALID_SEARCH_FORMATS:
            raise ValueError(
                f"Unknown format {search_format!r}. Must be one of: {sorted(_VALID_SEARCH_FORMATS)}"
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
        dt_created_after = (
            parse_filter_dt(created_after, "created_after") if created_after else None
        )
        dt_updated_after = (
            parse_filter_dt(updated_after, "updated_after") if updated_after else None
        )

        self._metrics.increment_metric_safe("lore_search")

        # When ids provided — skip search pipeline, bulk SQL lookup
        if ids is not None:
            if not ids:
                return []
            if len(ids) > self._settings.max_search_ids:
                raise ValueError(
                    f"ids exceeds cap of {self._settings.max_search_ids} IDs "
                    f"(got {len(ids)})"
                )
            return self._search_service.search_by_ids(
                ids,
                include_deleted=include_deleted,
                include_links=include_links and search_format != "title",
                created_after=dt_created_after,
                updated_after=dt_updated_after,
                sort_by=sort_by,
                source_type=source_type,
            )

        # Guard against empty query when ids is not provided
        if not query or not query.strip():
            raise ValueError("query is required when ids is not provided")

        if refine_from is not None and len(refine_from) > self._settings.max_refine_from_ids:
            raise ValueError(
                f"refine_from exceeds cap of {self._settings.max_refine_from_ids} IDs "
                f"(got {len(refine_from)})"
            )
        return self._search_service.search(
            query, limit, min_score, include_links, include_deleted,
            refine_from=refine_from,
            search_format=search_format,
            created_after=dt_created_after,
            updated_after=dt_updated_after,
            sort_by=sort_by,
            source_type=source_type,
        )

    # ── insert ────────────────────────────────────────────────────────────────

    def insert(
        self,
        memories: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Validate + insert memories and/or links.

        Validates memory structure (title required, source_type valid) before
        reaching the domain service.  Metric is incremented once per call.
        """
        memories = memories or []
        links = links or []
        for i, m in enumerate(memories):
            if "title" not in m:
                raise ValueError(
                    f"memory at index {i} is missing required field: 'title'"
                )
            if "source_type" in m and m["source_type"] not in WRITE_SOURCE_TYPES:
                raise ValueError(
                    f"memory at index {i} has invalid source_type {m['source_type']!r}. "
                    f"Must be one of: {sorted(WRITE_SOURCE_TYPES)}"
                )
        self._metrics.increment_metric_safe("lore_insert")
        return self._write_service.insert(memories, links, force)

    # ── remember ──────────────────────────────────────────────────────────────

    def remember(self, thought: str, source_type: str = "observed") -> dict[str, Any]:
        """Validate + fast one-shot insert with auto-extracted fields."""
        if source_type not in WRITE_SOURCE_TYPES:
            raise ValueError(
                f"Unknown source_type {source_type!r}. Must be one of: {sorted(WRITE_SOURCE_TYPES)}"
            )
        self._metrics.increment_metric_safe("lore_remember")
        return self._write_service.remember(thought, source_type=source_type)

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        memory_feedback: list[dict[str, Any]] | None = None,
        link_feedback: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Rate memories and links — drives the quality signal loop."""
        self._metrics.increment_metric_safe("lore_update")
        return self._write_service.update(memory_feedback or [], link_feedback or [])

    # ── forget ────────────────────────────────────────────────────────────────

    def forget(self, memory_ids: list[str], reason: str = "unspecified") -> dict[str, Any]:
        """Validate + soft-delete one or more memories by ID."""
        if not memory_ids:
            raise ValueError("memory_ids must not be empty")
        if reason not in _VALID_FORGET_REASONS:
            raise ValueError(
                f"Unknown reason {reason!r}. Must be one of: {sorted(_VALID_FORGET_REASONS)}"
            )
        self._metrics.increment_metric_safe("lore_forget")
        return self._write_service.forget(memory_ids, reason)

    # ── dashboard field update ────────────────────────────────────────────────

    def update_memory_fields(self, memory_id: str, fields: dict[str, Any]) -> dict[str, bool]:
        """Update a memory's scalar fields (dashboard route).

        Validates existence, delegates to write_service which owns the
        commit boundary, and increments the metric.
        """
        self._metrics.increment_metric_safe("dashboard_update_memory")
        return self._write_service.update_memory_fields(memory_id, **fields)

    # ── dashboard delete ─────────────────────────────────────────────────────

    def delete_memory(self, memory_id: str) -> dict[str, bool]:
        """Permanently delete a memory row (dashboard route).

        Validates existence, delegates to write_service which owns the
        commit boundary, and increments the metric.
        """
        self._metrics.increment_metric_safe("dashboard_delete_memory")
        return self._write_service.delete_memory(memory_id)

    # ── import_dump (backup restore) ──────────────────────────────────────────

    def import_dump(
        self,
        memories: list[dict[str, Any]],
        links: list[dict[str, Any]],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Import memories and links from a backup dump."""
        return self._import_service.import_dump(memories, links, dry_run=dry_run)
