from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    min_score: float = 0.1


def _handler(request: Request) -> Any:
    return request.app.state.dashboard_handler


@router.post("/api/search")
def search(request: Request, body: SearchRequest) -> list[dict[str, Any]]:
    return _handler(request).search(body.query, limit=body.limit, min_score=body.min_score)
