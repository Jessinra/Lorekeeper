import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


def _parse_dump(raw: bytes) -> tuple[list[Any], list[Any]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}") from e
    if not isinstance(data.get("memories"), list) or not isinstance(data.get("links"), list):
        raise HTTPException(status_code=422, detail='File must have "memories" and "links" arrays')
    return data["memories"], data["links"]


@router.get("/api/export")
def export_dump(request: Request, include_deleted: bool = False) -> Response:
    now = datetime.now(UTC)
    dump = _handler(request).export_dump(include_deleted=include_deleted)
    payload = {
        "version": "2",
        "exported_at": now.isoformat(),
        "memories": dump["memories"],
        "links": dump["links"],
    }
    filename = f"lorekeeper-{now.strftime('%Y-%m-%d')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/import/preview")
async def import_preview(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    memories_data, links_data = _parse_dump(await file.read())
    return _handler(request).import_preview(memories_data, links_data)


@router.post("/api/import/confirm")
async def import_confirm(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    memories_data, links_data = _parse_dump(await file.read())
    return _handler(request).import_confirm(memories_data, links_data)
