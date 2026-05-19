import structlog
from lorekeeper.services.orchestrator import MemoryService
from lorekeeper.services.search import SearchResult

log = structlog.get_logger()


def _result_to_dict(result: SearchResult) -> dict:
    m = result.memory
    return {
        "memory": {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "content": m.content,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
            "usage_count": m.usage_count,
            "score": m.score,
            "soft_deleted": m.soft_deleted,
            "confidence": m.confidence,
            "confidence_count": m.confidence_count,
        },
        "relevance": {
            "combined_score": result.combined_score,
            "semantic_score": result.semantic_score,
            "keyword_score": result.keyword_score,
        },
        "links": [
            {
                "id": lnk.id,
                "source_memory_id": lnk.source_memory_id,
                "target_memory_id": lnk.target_memory_id,
                "relation_type": lnk.relation_type,
                "reason": lnk.reason,
                "score": lnk.score,
                "created_at": lnk.created_at,
                "updated_at": lnk.updated_at,
                "usage_count": lnk.usage_count,
                "confidence": lnk.confidence,
                "confidence_count": lnk.confidence_count,
            }
            for lnk in result.links
        ],
    }


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
        "results": [_result_to_dict(r) for r in results],
        "total_matched": len(results),
        "query": query,
    }


