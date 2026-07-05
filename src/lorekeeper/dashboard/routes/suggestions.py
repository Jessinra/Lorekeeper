"""Dashboard API routes for suggestion review and sweep control."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lorekeeper.dashboard.handler import DashboardHandler

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


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/api/suggestions")
def list_suggestions(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "weighted_score",
    sort_dir: str = "desc",
    memory_id: str | None = None,
) -> dict[str, Any]:
    """List pending suggestions with pagination."""
    try:
        return _handler(request).list_suggestions(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir, memory_id=memory_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/api/suggestions/count")
def count_suggestions(request: Request, memory_id: str | None = None) -> dict[str, int]:
    """Return total pending suggestion count, optionally filtered by memory."""
    return _handler(request).count_suggestions(memory_id=memory_id)


@router.post("/api/suggestions/batch")
def batch_suggestions(request: Request, body: BatchAction) -> BatchResponse:
    """Accept or reject multiple suggestions at once."""
    action = body.action.lower()
    if action not in ("accept", "reject"):
        raise HTTPException(
            status_code=422,
            detail="action must be 'accept' or 'reject'",
        )

    result = _handler(request).batch_suggestions(
        suggestion_ids=body.suggestion_ids, action=action
    )

    mapped_results = [
        BatchResultItem(id=r["id"], status=r["status"], message=r["message"])
        for r in result["results"]
    ]

    return BatchResponse(
        results=mapped_results,
        accepted=result["accepted"],
        rejected=result["rejected"],
        errors=result["errors"],
    )


@router.post("/api/sweep/trigger")
def trigger_sweep(request: Request) -> dict[str, bool]:
    """Trigger the sweep scheduler immediately by resetting its timer."""
    return _handler(request).trigger_sweep()


@router.get("/api/sweep/status")
def sweep_status(request: Request) -> dict[str, str | None]:
    """Return last and next sweep run timestamps."""
    return _handler(request).sweep_status()
