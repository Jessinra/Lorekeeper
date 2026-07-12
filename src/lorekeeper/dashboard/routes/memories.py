from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


@router.get("/api/memories")
def list_memories(
    request: Request,
    include_deleted: bool = False,
    page: int | None = Query(None, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    q: str = "",
    namespace: str | None = None,
    filter: str | None = None,
    sort: str = "updated_at",
    sort_dir: str = "desc",
) -> dict[str, Any] | list[dict[str, Any]]:
    handler = _handler(request)
    if page is not None:
        # Paginated mode
        return handler.list_memories_paginated(
            page=page, per_page=per_page, query=q,
            namespace=namespace, include_deleted=include_deleted,
            filter_preset=filter, sort=sort, sort_dir=sort_dir,
        )
    # Legacy mode — return flat list
    return handler.list_memories(include_deleted=include_deleted)


@router.get("/api/memories/counts")
def memory_counts(request: Request) -> dict[str, int]:
    return _handler(request).get_memory_counts()


@router.get("/api/namespaces")
def namespaces(request: Request) -> list[str]:
    return _handler(request).list_namespaces()


@router.get("/api/memories/{memory_id}")
def get_memory(request: Request, memory_id: str) -> dict[str, Any]:
    result = _handler(request).get_memory(memory_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return result


@router.patch("/api/memories/{memory_id}")
def update_memory(request: Request, memory_id: str, body: MemoryUpdate) -> dict[str, bool]:
    fields = body.model_dump(exclude_none=True)
    if "soft_deleted" in fields:
        fields["soft_deleted"] = int(fields["soft_deleted"])
    try:
        return _handler(request).update_memory(memory_id, fields)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found") from None


@router.delete("/api/memories/{memory_id}")
def delete_memory(request: Request, memory_id: str) -> dict[str, bool]:
    try:
        return _handler(request).delete_memory(memory_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found") from None
