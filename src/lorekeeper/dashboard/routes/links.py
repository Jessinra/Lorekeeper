from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.domains.link.models import RelationType
from lorekeeper.server import get_service
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
    svc = get_service()
    links = svc.links.all_links()
    all_rows = svc.memories.all_memory_rows(include_deleted=True)
    title_map = {r["id"]: r["title"] for r in all_rows}
    deleted_ids = {r["id"] for r in all_rows if r["soft_deleted"]}
    if not include_deleted:
        links = [
            lnk for lnk in links
            if lnk.source_memory_id not in deleted_ids and lnk.target_memory_id not in deleted_ids
        ]
    return [
        {
            **serialize_memory_link(lnk),
            "source_title": title_map.get(lnk.source_memory_id, lnk.source_memory_id[:12] + "…"),
            "target_title": title_map.get(lnk.target_memory_id, lnk.target_memory_id[:12] + "…"),
        }
        for lnk in links
    ]


@router.post("/api/links", status_code=201)
def create_link(body: LinkCreate) -> dict[str, Any]:
    svc = get_service()
    if svc.memories.get_memory_row(body.source_memory_id) is None:
        raise HTTPException(status_code=404, detail="Source memory not found")
    if svc.memories.get_memory_row(body.target_memory_id) is None:
        raise HTTPException(status_code=404, detail="Target memory not found")
    link = svc.links.insert_link(
        source_memory_id=body.source_memory_id,
        target_memory_id=body.target_memory_id,
        relation_type=body.relation_type,
        reason=body.reason,
        score=body.score,
    )
    svc.commit()
    return serialize_memory_link(link)


@router.delete("/api/links/{link_id}")
def delete_link(link_id: str) -> dict[str, bool]:
    svc = get_service()
    if svc.links.get_link(link_id) is None:
        raise HTTPException(status_code=404, detail="Link not found")
    svc.links.delete_link(link_id)
    svc.commit()
    return {"ok": True}
