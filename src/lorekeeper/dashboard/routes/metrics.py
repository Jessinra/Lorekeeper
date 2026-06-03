from typing import Any

from fastapi import APIRouter

from lorekeeper.server import get_service

router = APIRouter()


@router.get("/api/metrics")
def get_metrics(hours: int = 24) -> dict[str, Any]:
    """Return per-minute API call counts bucketed by tool, for the last `hours` hours."""
    store = get_service().metrics
    rows = store.get_metrics(hours=hours)
    buckets: list[str] = []
    tools: set[str] = set()
    data: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = row["minute_bucket"]
        tool = row["tool_name"]
        count = row["count"]
        tools.add(tool)
        if bucket not in data:
            data[bucket] = {}
            buckets.append(bucket)
        data[bucket][tool] = count
    return {
        "hours": hours,
        "buckets": buckets,
        "tools": sorted(tools),
        "data": data,
    }
