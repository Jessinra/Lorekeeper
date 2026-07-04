import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from lorekeeper.domains.memory.models import Memory
from lorekeeper.server import get_link_store, get_memory_processor, get_memory_store
from lorekeeper.shared.serializers import serialize_memory, serialize_memory_link

router = APIRouter()


def _parse_dump(raw: bytes) -> tuple[list[Any], list[Any]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}") from e
    if not isinstance(data.get("memories"), list) or not isinstance(data.get("links"), list):
        raise HTTPException(status_code=422, detail='File must have "memories" and "links" arrays')
    return data["memories"], data["links"]


@router.get("/api/export")
def export_dump(include_deleted: bool = False) -> Response:
    memories = get_memory_store()
    links_store = get_link_store()
    now = datetime.now(UTC)
    memories_list = [
        serialize_memory(Memory(**dict(r)))
        for r in memories.all_memory_rows(include_deleted=include_deleted)
    ]
    links_list = [serialize_memory_link(lnk) for lnk in links_store.all_links()]
    payload = {
        "version": "2",
        "exported_at": now.isoformat(),
        "memories": memories_list,
        "links": links_list,
    }
    filename = f"lorekeeper-{now.strftime('%Y-%m-%d')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/import/preview")
async def import_preview(file: UploadFile = File(...)) -> dict[str, Any]:
    memories_data, links_data = _parse_dump(await file.read())
    return get_memory_processor().import_dump(memories_data, links_data, dry_run=True)


@router.post("/api/import/confirm")
async def import_confirm(file: UploadFile = File(...)) -> dict[str, Any]:
    memories_data, links_data = _parse_dump(await file.read())
    return get_memory_processor().import_dump(memories_data, links_data, dry_run=False)
