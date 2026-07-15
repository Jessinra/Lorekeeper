from __future__ import annotations

import math
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from lorekeeper.dashboard.handler import DashboardHandler
from lorekeeper.infra.settings import Settings

router = APIRouter()


class DebugQueryRequest(BaseModel):
    query: str
    limit: int = 10
    min_score: float = 0.1
    include_deleted: bool = False


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


def _signal_contributions(
    semantic: float,
    keyword: float,
    memory_score: float,
    usage_count: int,
    settings: Settings,
) -> dict[str, float]:
    """Compute the per-signal weighted contributions that sum to combined_score."""
    cap = settings.usage_normalisation_cap
    log_usage = math.log2(1 + usage_count) / math.log2(1 + cap) if usage_count > 0 else 0.0
    return {
        "semantic_score": settings.w_semantic * semantic,
        "keyword_score": settings.w_keyword * keyword,
        "memory_score": settings.w_memory * (memory_score / 10.0),
        "usage_score": settings.w_usage * log_usage,
    }


@router.post("/api/query/debug")
def debug_query(request: Request, body: DebugQueryRequest) -> dict[str, Any]:
    handler = _handler(request)
    settings = handler._settings

    start = time.monotonic()
    results = handler._memp.search(
        body.query,
        limit=body.limit,
        min_score=body.min_score,
        include_deleted=body.include_deleted,
        include_links=True,
    )
    elapsed_ms = round((time.monotonic() - start) * 1000)

    rows = []
    total_linked = 0
    for rank, result in enumerate(results, start=1):
        mem = result.memory
        link_count = len(result.links)
        total_linked += link_count

        contributions = _signal_contributions(
            result.semantic_score,
            result.keyword_score,
            mem.score,
            mem.usage_count,
            settings,
        )

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
            **{k: round(v, 4) for k, v in contributions.items()},
        })

    return {
        "results": rows,
        "total_results": len(rows),
        "total_linked": total_linked,
        "elapsed_ms": elapsed_ms,
    }
