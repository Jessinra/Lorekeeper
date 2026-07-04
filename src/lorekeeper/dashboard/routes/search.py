from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from lorekeeper.server import get_memory_processor
from lorekeeper.shared.serializers import serialize_search_result

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_score: float = 0.1


@router.post("/api/search")
def search(body: SearchRequest) -> list[dict[str, Any]]:
    results = get_memory_processor().search(
        body.query, limit=body.limit, min_score=body.min_score,
        include_links=False,
    )
    return [
        serialize_search_result(
            r,
            truncate_content=300,
            exclude_memory_fields={"created_at", "updated_at", "confidence", "confidence_count"},
            exclude_relevance_fields={"decay_factor"},
            round_relevance=4,
            include_links=False,
        )
        for r in results
    ]
