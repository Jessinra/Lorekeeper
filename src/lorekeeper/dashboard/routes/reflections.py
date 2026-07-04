from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.server import get_reflection_processor
from lorekeeper.shared.serializers import serialize_reflection, serialize_session

router = APIRouter()


@router.get("/api/reflections")
def list_reflections() -> list[dict[str, Any]]:
    proc = get_reflection_processor()
    return [serialize_reflection(dict(r)) for r in proc.list_reflections()]


@router.get("/api/reflections/{reflection_id}")
def get_reflection_detail(reflection_id: str) -> dict[str, Any]:
    proc = get_reflection_processor()
    row = proc.get_reflection(reflection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    sessions = proc.sessions_for_reflection(reflection_id)
    return {
        "reflection": serialize_reflection(dict(row)),
        "sessions": [serialize_session(dict(s)) for s in sessions],
    }


@router.get("/api/sessions")
def list_sessions(with_content: bool = True) -> list[dict[str, Any]]:
    proc = get_reflection_processor()
    rows = proc.list_sessions(with_content=with_content)
    return [serialize_session(dict(s)) for s in rows]


@router.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict[str, Any]:
    proc = get_reflection_processor()
    row = proc.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    reflection = None
    if row["reflection_id"]:
        ref_row = proc.get_reflection(row["reflection_id"])
        if ref_row:
            reflection = {
                "id": ref_row["id"],
                "created_at": ref_row["created_at"],
                "summary": ref_row["summary"],
            }
    return {"session": serialize_session(dict(row)), "reflection": reflection}
