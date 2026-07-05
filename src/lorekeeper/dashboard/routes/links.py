from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from lorekeeper.domains.link.models import RelationType

router = APIRouter()


class LinkCreate(BaseModel):
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    reason: str
    score: float = 1.0


def _handler(request: Request) -> Any:
    return request.app.state.dashboard_handler


@router.get("/api/links")
def list_all_links(request: Request, include_deleted: bool = False) -> list[dict[str, Any]]:
    return _handler(request).list_all_links(include_deleted=include_deleted)


@router.post("/api/links", status_code=201)
def create_link(request: Request, body: LinkCreate) -> dict[str, Any]:
    try:
        return _handler(request).create_link(
            source_memory_id=body.source_memory_id,
            target_memory_id=body.target_memory_id,
            relation_type=body.relation_type,
            reason=body.reason,
            score=body.score,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/api/links/{link_id}")
def delete_link(request: Request, link_id: str) -> dict[str, bool]:
    try:
        return _handler(request).delete_link(link_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
