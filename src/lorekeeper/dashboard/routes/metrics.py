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


@router.get("/api/metrics/tool-calls")
def get_tool_calls(request: Request, hours: int = 168) -> dict[str, Any]:
    """Return heatmap-shaped tool call data for the last `hours` hours (default 7 days)."""
    return _handler(request).get_tool_calls(hours=hours)
