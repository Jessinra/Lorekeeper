"""MCP handlers for the Memory domain — search, insert.

Thin shims: validation + metrics live in the MemoryProcessor; these functions
receive a processor instance and handle serialization only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.shared.serializers import (
    serialize_search_result,
    serialize_search_result_title,
)

if TYPE_CHECKING:
    from lorekeeper.processors.memory import MemoryProcessor


def handle_search(
    processor: MemoryProcessor,
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
    """Pass-through + serialize. Validation/metrics handled by processor."""
    results = processor.search(
        query=query, limit=limit, min_score=min_score,
        include_links=include_links, include_deleted=include_deleted,
        refine_from=refine_from, search_format=format, ids=ids,
        created_after=created_after, updated_after=updated_after,
        sort_by=sort_by, source_type=source_type,
    )
    # When ids=[], processor returns empty list — serialize as empty results
    serialized = []
    if format == "title":
        serialized = [serialize_search_result_title(r) for r in results]
    else:
        serialized = [serialize_search_result(r, include_links=include_links) for r in results]
    return {"results": serialized, "total_matched": len(serialized), "query": query}


def handle_insert(
    processor: MemoryProcessor,
    memories: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Pass-through + return. Validation/metrics handled by processor."""
    return processor.insert(memories=memories, links=links, force=force)
