from typing import Any

from fastapi import APIRouter, HTTPException, Request

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


@router.get("/api/reflections")
def list_reflections(request: Request) -> list[dict[str, Any]]:
    return _handler(request).list_reflections()


@router.get("/api/reflections/{reflection_id}")
def get_reflection_detail(request: Request, reflection_id: str) -> dict[str, Any]:
    result = _handler(request).get_reflection_detail(reflection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return result


@router.get("/api/sessions")
def list_sessions(
    request: Request,
    q: str | None = None,
    task: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """List sessions with optional search, task-type filter, and pagination."""
    return _handler(request).list_sessions_paginated(q=q, task=task, page=page, page_size=page_size)


@router.get("/api/sessions/{session_id}")
def get_session_detail(request: Request, session_id: str) -> dict[str, Any]:
    result = _handler(request).get_session_detail(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return result
