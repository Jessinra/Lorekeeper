"""Dashboard API routes for suggestion review and sweep control."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.server import get_service, get_suggestion_processor, get_suggestions_store

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
    store = get_suggestions_store()

    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 500",
        )
    if offset < 0:
        raise HTTPException(
            status_code=422, detail="offset must be non-negative"
        )

    # Validate sort params (whitelist to prevent SQL injection)
    if sort_by not in ("weighted_score", "created_at"):
        sort_by = "weighted_score"
    order = "ASC" if sort_dir.lower() == "asc" else "DESC"

    # Use COUNT query for accurate total (avoids loading all rows into Python),
    # then fetch only the requested page with DB-side sorting.
    if memory_id:
        total = store.count_pending_suggestions_for_memory(memory_id)
        page = store.get_suggestions_for_memory_paged(
            memory_id,
            status="pending",
            sort_by=sort_by,
            sort_dir=order,
            limit=limit,
            offset=offset,
        )
    else:
        total = store.count_pending_suggestions()
        page = store.get_pending_suggestions(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=order,
        )

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
    store = get_suggestions_store()
    if memory_id:
        return {"count": store.count_pending_suggestions_for_memory(memory_id)}
    return {"count": store.count_pending_suggestions()}


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
    svc = get_service()
    svc.config.set_override(
        "sweep_next_run_at", datetime.now(UTC).isoformat()
    )
    svc.commit()
    return {"ok": True}


@router.get("/api/sweep/status")
def sweep_status() -> dict[str, str | None]:
    """Return last and next sweep run timestamps."""
    svc = get_service()
    store = get_suggestions_store()
    overrides = svc.config.get_overrides()
    last_run = overrides.get("sweep_last_run_at")
    next_run = overrides.get("sweep_next_run_at")

    # If no last_run recorded, use the newest suggestion's created_at as a
    # proxy — that's the most recent time the sweep produced output.
    if not last_run:
        last_run = store.get_newest_suggestion_created_at()

    return {
        "last_run_at": str(last_run) if last_run else None,
        "next_run_at": str(next_run) if next_run else None,
    }
