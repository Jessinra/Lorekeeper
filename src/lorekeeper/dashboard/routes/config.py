import types
from typing import Any, Union, get_args, get_origin

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.server import get_service

router = APIRouter()

_READONLY_KEYS = {"data_dir", "embedding_model"}


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
    s = get_service().settings
    overridden_keys = set(get_service().config.get_overrides().keys())
    return {
        "data_dir": str(s.data_dir),
        "embedding_model": s.embedding_model,
        "duplicate_threshold": s.duplicate_threshold,
        "w_semantic": s.w_semantic,
        "w_keyword": s.w_keyword,
        "w_memory": s.w_memory,
        "w_usage": s.w_usage,
        "score_bump_up": s.score_bump_up,
        "score_bump_down": s.score_bump_down,
        "score_min": s.score_min,
        "score_max": s.score_max,
        "soft_delete_confidence_threshold": s.soft_delete_confidence_threshold,
        "confidence_window_size": s.confidence_window_size,
        "search_limit": s.search_limit,
        "max_links_per_memory": s.max_links_per_memory,
        "usage_normalisation_cap": s.usage_normalisation_cap,
        "decay_lambda": s.decay_lambda,
        "new_memory_default_score": s.new_memory_default_score,
        "auto_link_enabled": s.auto_link_enabled,
        "auto_link_k": s.auto_link_k,
        "auto_link_threshold": s.auto_link_threshold,
        "_overridden_keys": sorted(overridden_keys),
    }


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
    _TYPE_MAP = {k: _unwrap_optional(v.annotation) for k, v in ConfigUpdate.model_fields.items()}
    svc = get_service()
    s = svc.settings
    for key, value in body.model_dump(exclude_none=True).items():
        if key in _READONLY_KEYS:
            continue
        expected = _TYPE_MAP.get(key)
        if expected is not None and not isinstance(value, expected):
            raise HTTPException(
                status_code=422,
                detail=f"Config '{key}' expects {expected.__name__}, got {type(value).__name__}",
            )
        setattr(s, key, value)
        svc.config.set_override(key, value)
    svc.commit()
    return {"ok": True}
