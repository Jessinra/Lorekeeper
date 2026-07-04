"""Dashboard API routes for suggestion review and sweep control."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.server import get_admin_processor, get_suggestion_processor

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────


class BatchAction(BaseModel):
    suggestion_ids: list[str]
    action: str  # "accept" | "reject"


class BatchResultItem(BaseModel):
    id: str
    status: str  # "accepted" | "rejected" | "error"
    message: str


class BatchResponse(BaseModel):
    results: list[BatchResultItem]
    accepted: int = 0
    rejected: int = 0
    errors: list[str] = []


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/api/suggestions")
def list_suggestions(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "weighted_score",
    sort_dir: str = "desc",
    memory_id: str | None = None,
) -> dict[str, Any]:
    """List pending suggestions with pagination."""
    try:
        page, total = get_suggestion_processor().list_pending(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
            memory_id=memory_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return {
        "items": [
            {
                "id": r.id,
                "source_memory_id": r.source_memory_id,
                "source_title": r.source_title,
                "target_memory_id": r.target_memory_id,
                "target_title": r.target_title,
                "weighted_score": r.weighted_score,
                "cosine_score": r.cosine_score,
                "bm25_score": r.bm25_score,
                "entity_score": r.entity_score,
                "temporal_score": r.temporal_score,
                "confidence": r.confidence,
                "created_at": r.created_at,
            }
            for r in page
        ],
        "total": total,
        "offset": offset,
    }


@router.get("/api/suggestions/count")
def count_suggestions(memory_id: str | None = None) -> dict[str, int]:
    """Return total pending suggestion count, optionally filtered by memory."""
    return {"count": get_suggestion_processor().count_pending(memory_id=memory_id)}


@router.post("/api/suggestions/batch")
def batch_suggestions(body: BatchAction) -> BatchResponse:
    """Accept or reject multiple suggestions at once."""
    action = body.action.lower()
    if action not in ("accept", "reject"):
        raise HTTPException(
            status_code=422,
            detail="action must be 'accept' or 'reject'",
        )

    processor = get_suggestion_processor()
    result = processor.review(
        suggestion_ids=body.suggestion_ids, action=action
    )

    mapped_results: list[BatchResultItem] = []
    for r in result.results:
        mapped_results.append(
            BatchResultItem(
                id=r["id"],
                status=r["status"],
                message=r["message"],
            )
        )

    return BatchResponse(
        results=mapped_results,
        accepted=result.accepted,
        rejected=result.rejected,
        errors=[e["error"] for e in result.errors],
    )


@router.post("/api/sweep/trigger")
def trigger_sweep() -> dict[str, bool]:
    """Trigger the sweep scheduler immediately by resetting its timer."""
    get_admin_processor().trigger_sweep()
    return {"ok": True}


@router.get("/api/sweep/status")
def sweep_status() -> dict[str, str | None]:
    """Return last and next sweep run timestamps."""
    return get_admin_processor().sweep_status()
