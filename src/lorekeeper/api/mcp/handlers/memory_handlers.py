"""MCP handlers for the Memory domain — search, insert.

Extracted from handlers.py (LKPR-104 Phase 6a). Input sanitization and
validation happen here, before reaching the domain service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.domains.memory.models import SOURCE_TYPES, WRITE_SOURCE_TYPES
from lorekeeper.domains.memory.ranking import VALID_SORT_BY, parse_filter_dt
from lorekeeper.shared.serializers import (
    serialize_search_result,
    serialize_search_result_title,
)

if TYPE_CHECKING:
    from lorekeeper.services.orchestrator import MemoryService

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
