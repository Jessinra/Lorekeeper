from typing import Any

from fastapi import APIRouter, HTTPException

from lorekeeper.serializers import serialize_reflection, serialize_session
from lorekeeper.server import get_service

router = APIRouter()


@router.get("/api/reflections")
def list_reflections() -> list[dict[str, Any]]:
    store = get_service().reflections
    return [serialize_reflection(dict(r)) for r in store.all_reflections()]


@router.get("/api/reflections/{reflection_id}")
def get_reflection_detail(reflection_id: str) -> dict[str, Any]:
    store = get_service().reflections
    row = store.get_reflection(reflection_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    sessions = store.sessions_for_reflection(reflection_id)
    return {
        "reflection": serialize_reflection(dict(row)),
        "sessions": [serialize_session(dict(s)) for s in sessions],
    }


@router.get("/api/sessions")
def list_sessions(with_content: bool = True) -> list[dict[str, Any]]:
    store = get_service().reflections
    rows = store.sessions_with_content() if with_content else store.all_sessions()
    return [serialize_session(dict(s)) for s in rows]


@router.get("/api/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict[str, Any]:
    store = get_service().reflections
    row = store.get_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    reflection = None
    if row["reflection_id"]:
        ref_row = store.get_reflection(row["reflection_id"])
        if ref_row:
            reflection = {
                "id": ref_row["id"],
                "created_at": ref_row["created_at"],
                "summary": ref_row["summary"],
            }
    return {"session": serialize_session(dict(row)), "reflection": reflection}
