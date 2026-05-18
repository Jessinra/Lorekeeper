from typing import Any


def search_result_to_dict(result: Any) -> dict:
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
