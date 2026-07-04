from typing import Any

from fastapi import APIRouter

from lorekeeper.server import get_admin_processor

router = APIRouter()


@router.get("/api/metrics")
def get_metrics(hours: int = 24) -> dict[str, Any]:
    """Return per-minute API call counts bucketed by tool, for the last `hours` hours."""
    return get_admin_processor().get_metrics(hours=hours)
