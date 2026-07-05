from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


def _handler(request: Request) -> Any:
    return request.app.state.dashboard_handler


@router.get("/api/memories")
def list_memories(request: Request, include_deleted: bool = False) -> list[dict[str, Any]]:
    return _handler(request).list_memories(include_deleted=include_deleted)


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
