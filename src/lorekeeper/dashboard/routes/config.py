import types
from typing import Any, Union, get_args, get_origin

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.server import get_admin_processor

router = APIRouter()


def _unwrap_optional(tp: Any) -> Any:
    """Unwrap Optional[T] / Union[T, None] | T | None to T."""
    origin = get_origin(tp)
    if origin is Union or origin is types.UnionType:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        return non_none[0] if len(non_none) == 1 else tp
    return tp


@router.get("/api/config")
def get_config() -> dict[str, Any]:
    return get_admin_processor().get_config()


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


@router.patch("/api/config")
def update_config(body: ConfigUpdate) -> dict[str, bool]:
    """Update config overrides with type validation.
    Read-only keys (data_dir, embedding_model) are silently skipped.
    Returns 422 with detail on type mismatch.
    """
    admin = get_admin_processor()
    for key, value in body.model_dump(exclude_none=True).items():
        try:
            admin.set_config(key, value)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
    return {"ok": True}
