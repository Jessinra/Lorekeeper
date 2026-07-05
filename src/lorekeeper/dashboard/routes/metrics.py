from typing import Any

from fastapi import APIRouter, Request

from lorekeeper.dashboard.handler import DashboardHandler

router = APIRouter()


def _handler(request: Request) -> DashboardHandler:
    return request.app.state.dashboard_handler  # type: ignore[no-any-return]


@router.get("/api/metrics")
def get_metrics(request: Request, hours: int = 24) -> dict[str, Any]:
    """Return per-minute API call counts bucketed by tool, for the last `hours` hours."""
    return _handler(request).get_metrics(hours=hours)
