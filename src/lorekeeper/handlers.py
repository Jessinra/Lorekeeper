import structlog

from lorekeeper.serializers import serialize_search_result
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
) -> dict:
    results = svc.search(
        query, limit, min_score, include_links, include_deleted,
        refine_from=refine_from,
    )
    return {
        "results": [serialize_search_result(r) for r in results],
        "total_matched": len(results),
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


