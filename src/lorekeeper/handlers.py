import structlog
from lorekeeper.schemas import search_result_to_dict
from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()


def handle_search(
    svc: MemoryService,
    query: str,
    limit: int = 10,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
) -> dict:
    results = svc.search(query, limit, min_score, include_links, include_deleted)
    return {
        "results": [search_result_to_dict(r) for r in results],
        "total_matched": len(results),
        "query": query,
    }


def handle_insert(
    svc: MemoryService,
    memories: list[dict],
    links: list[dict],
    force: bool = False,
) -> dict:
    return svc.insert(memories, links, force)


def handle_update(
    svc: MemoryService,
    memory_feedback: list[dict],
    link_feedback: list[dict],
) -> dict:
    return svc.update(memory_feedback, link_feedback)
