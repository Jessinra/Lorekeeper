from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


class DebugQueryRequest(BaseModel):
    query: str
    limit: int = 10
    min_score: float = 0.1
    include_deleted: bool = False


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


@router.post("/api/query/debug")
def debug_query(request: Request, body: DebugQueryRequest) -> dict[str, Any]:
    handler = _handler(request)

    start = time.monotonic()
    results = handler.debug_search(
        body.query,
        limit=body.limit,
        min_score=body.min_score,
        include_deleted=body.include_deleted,
    )
    elapsed_ms = round((time.monotonic() - start) * 1000)

    rows = []
    total_linked = 0
    for rank, result in enumerate(results, start=1):
        mem = result.memory
        link_count = len(result.links)
        total_linked += link_count

        rows.append({
            "rank": rank,
            "memory": {
                "id": mem.id,
                "title": mem.title,
                "namespace": mem.namespace,
                "score": mem.score,
                "usage_count": mem.usage_count,
                "content": mem.content,
                "link_count": link_count,
                "soft_deleted": mem.soft_deleted,
            },
            "combined_score": round(result.combined_score, 4),
            "semantic_score": round(result.w_semantic, 4),
            "keyword_score": round(result.w_keyword, 4),
            "memory_score": round(result.w_memory, 4),
            "usage_score": round(result.w_usage, 4),
        })

    return {
        "results": rows,
        "total_results": len(rows),
        "total_linked": total_linked,
        "elapsed_ms": elapsed_ms,
    }
