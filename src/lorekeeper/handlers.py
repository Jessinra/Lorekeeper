import structlog

from lorekeeper.serializers import serialize_search_result, serialize_search_result_title
from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()


def handle_search(
    svc: MemoryService,
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,
    format: str = "full",
    ids: list[str] | None = None,
) -> dict:
    _VALID_FORMATS = {"full", "title"}
    if format not in _VALID_FORMATS:
        raise ValueError(f"Unknown format {format!r}. Must be one of: {sorted(_VALID_FORMATS)}")

    # When ids is provided, skip the search pipeline — bulk SQL lookup
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
        )
        if format == "title":
            serialized = [serialize_search_result_title(r) for r in results]
        else:
            serialized = [serialize_search_result(r, include_links=include_links) for r in results]
        return {
            "results": serialized,
            "total_matched": len(serialized),
            "query": query,
        }

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
    )
    if format == "title":
        serialized = [serialize_search_result_title(r) for r in results]
    else:
        serialized = [serialize_search_result(r, include_links=include_links) for r in results]
    return {
        "results": serialized,
        "total_matched": len(serialized),
        "query": query,
    }


def handle_insert(
    svc: MemoryService,
    memories: list[dict],
    links: list[dict],
    force: bool = False,
) -> dict:
    for i, m in enumerate(memories):
        if "title" not in m:
            raise ValueError(
                f"memory at index {i} is missing required field: 'title'"
            )
    return svc.insert(memories, links, force)


def handle_remember(svc: MemoryService, thought: str) -> dict:
    return svc.remember(thought)


