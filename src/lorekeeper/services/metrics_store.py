"""API metrics — extracted from LinkStore as part of LKPR-51."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lorekeeper.services.database import Database


class MetricsStore:
    """Per-hour API call counters for the dashboard metrics view."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def increment_metric(self, tool_name: str) -> None:
        """Increment the call counter for tool_name, bucketed to current UTC hour."""
        bucket = datetime.now(UTC).strftime("%Y-%m-%d %H:00")
        self._conn.execute(
            """
            INSERT INTO api_metrics (minute_bucket, tool_name, count)
            VALUES (?, ?, 1)
            ON CONFLICT(minute_bucket, tool_name) DO UPDATE SET count = count + 1
            """,
            (bucket, tool_name),
        )
        self._conn.commit()

    @staticmethod
    def _normalize_bucket(bucket: str) -> str:
        """Normalize a metric bucket string to 'YYYY-MM-DD HH:00' format."""
        for fmt in (
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(bucket, fmt).strftime("%Y-%m-%d %H:00")
            except ValueError:
                continue
        return bucket  # already normalized or unknown — return as-is

    def get_metrics(self, hours: int = 24) -> list[dict]:
        """Return all metric rows within the last `hours` hours, oldest first."""
        cutoff = (datetime.now(UTC) - timedelta(hours=hours)).strftime(
            "%Y-%m-%d %H:00"
        )
        rows = self._conn.execute(
            """
            SELECT minute_bucket, tool_name, SUM(count) as count
            FROM api_metrics
            WHERE minute_bucket >= ?
            GROUP BY minute_bucket, tool_name
            ORDER BY minute_bucket ASC
            """,
            (cutoff,),
        ).fetchall()
        # Normalize buckets — old rows may have ISO format (e.g. "2026-05-21T08:08:00")
        return [
            {
                "minute_bucket": self._normalize_bucket(row["minute_bucket"]),
                "tool_name": row["tool_name"],
                "count": row["count"],
            }
            for row in rows
        ]
