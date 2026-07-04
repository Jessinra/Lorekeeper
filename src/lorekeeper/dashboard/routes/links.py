from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.domains.link.models import RelationType
from lorekeeper.server import get_link_processor
from lorekeeper.shared.serializers import serialize_memory_link

router = APIRouter()


class LinkCreate(BaseModel):
    source_memory_id: str
    target_memory_id: str
    relation_type: RelationType
    reason: str
    score: float = 1.0


@router.get("/api/links")
def list_all_links(include_deleted: bool = False) -> list[dict[str, Any]]:
    return get_link_processor().list_links(include_deleted=include_deleted)


@router.post("/api/links", status_code=201)
def create_link(body: LinkCreate) -> dict[str, Any]:
    try:
        link = get_link_processor().create_link(
            source_memory_id=body.source_memory_id,
            target_memory_id=body.target_memory_id,
            relation_type=body.relation_type,
            reason=body.reason,
            score=body.score,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return serialize_memory_link(link)


@router.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict[str, bool]:
    try:
        get_link_processor().delete_link(link_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True}
