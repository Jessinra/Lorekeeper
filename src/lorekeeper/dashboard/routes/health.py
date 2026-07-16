from typing import Any

from fastapi import APIRouter, Request

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


@router.get("/api/health")
def get_health(request: Request) -> dict[str, Any]:
    """Return health overview stats for the home page dashboard."""
    return _handler(request).get_health()
