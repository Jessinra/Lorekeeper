from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


def _handler(request: Request) -> Any:
    return request.app.state.dashboard_handler


class ConfigUpdate(BaseModel):
    duplicate_threshold: float | None = None
    w_semantic: float | None = None
    w_keyword: float | None = None
    w_memory: float | None = None
    w_usage: float | None = None
    score_bump_up: float | None = None
    score_bump_down: float | None = None
    score_min: float | None = None
    score_max: float | None = None
    soft_delete_confidence_threshold: int | None = None
    confidence_window_size: int | None = None
    search_limit: int | None = None
    max_links_per_memory: int | None = None
    usage_normalisation_cap: int | None = None
    decay_lambda: float | None = None
    new_memory_default_score: float | None = None
    auto_link_enabled: bool | None = None
    auto_link_k: int | None = None
    auto_link_threshold: float | None = None


@router.get("/api/config")
def get_config(request: Request) -> dict[str, Any]:
    return _handler(request).get_config()


@router.patch("/api/config")
def update_config(request: Request, body: ConfigUpdate) -> dict[str, bool]:
    """Update config overrides with type validation."""
    handler = _handler(request)
    for key, value in body.model_dump(exclude_none=True).items():
        try:
            handler.set_config(key, value)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
    return {"ok": True}
