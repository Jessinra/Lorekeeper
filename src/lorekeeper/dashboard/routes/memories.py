from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lorekeeper.domains.memory.models import Memory
from lorekeeper.server import get_db, get_link_store, get_memory_store
from lorekeeper.shared.serializers import serialize_memory, serialize_memory_link

router = APIRouter()


@router.get("/api/memories")
def list_memories(include_deleted: bool = False) -> list[dict[str, Any]]:
    memories = get_memory_store()
    links = get_link_store()
    rows = memories.all_memory_rows(include_deleted=include_deleted)
    link_counts: dict[str, int] = {}
    for lnk in links.all_links():
        link_counts[lnk.source_memory_id] = link_counts.get(lnk.source_memory_id, 0) + 1
        link_counts[lnk.target_memory_id] = link_counts.get(lnk.target_memory_id, 0) + 1
    result = []
    for r in rows:
        mem = serialize_memory(Memory(**r))
        mem["link_count"] = link_counts.get(r["id"], 0)
        result.append(mem)
    return result


@router.get("/api/memories/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    memories = get_memory_store()
    links = get_link_store()
    row = memories.get_memory_row(memory_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    mem_links = links.links_for_memory(memory_id)
    return {
        "memory": serialize_memory(Memory(**dict(row))),
        "links": [serialize_memory_link(lnk) for lnk in mem_links],
    }


class MemoryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    score: float | None = None
    soft_deleted: bool | None = None


@router.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, bool]:
    memories = get_memory_store()
    db = get_db()
    if memories.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    fields = body.model_dump(exclude_none=True)
    if "soft_deleted" in fields:
        fields["soft_deleted"] = int(fields["soft_deleted"])
    memories.update_memory_fields(memory_id, **fields)
    db.conn.commit()
    return {"ok": True}


@router.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str) -> dict[str, bool]:
    memories = get_memory_store()
    db = get_db()
    if memories.get_memory_row(memory_id) is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    memories.delete_memory_row(memory_id)
    db.conn.commit()
    return {"ok": True}
