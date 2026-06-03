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
        """Return all metric rows within the last `hours` hours, oldest first.

        Buckets are normalized to `YYYY-MM-DD HH:00` before filtering and
        grouping. This handles legacy rows stored in ISO format (e.g.
        `2026-05-21T08:08:00`) which would otherwise:
          - be missed/included incorrectly by a raw lexicographic WHERE
            (`T` > ` ` in ASCII, so `2026-05-21T...` sorts after `2026-05-21 ...`)
          - double-count the same hour under multiple string formats in GROUP BY

        We pull rows since a conservative cutoff (using the canonical format,
        which is lexicographically <= any ISO-format string for the same time),
        then re-normalize, re-filter and re-aggregate in Python. At Lorekeeper
        scale (thousands of rows max) this is trivial.
        """
        now = datetime.now(UTC)
        cutoff_dt = now - timedelta(hours=hours)
        cutoff = cutoff_dt.strftime("%Y-%m-%d %H:00")

        # Pull ALL rows from the DB without WHERE — the legacy-ISO comparison
        # bug means we can't trust lexicographic filtering. At this scale the
        # full scan is fine; we filter in Python after normalization.
        rows = self._conn.execute(
            "SELECT minute_bucket, tool_name, count FROM api_metrics"
        ).fetchall()

        # Aggregate by (normalized_bucket, tool_name), filter by cutoff
        agg: dict[tuple[str, str], int] = {}
        for row in rows:
            normalized = self._normalize_bucket(row["minute_bucket"])
            if normalized < cutoff:
                continue
            key = (normalized, row["tool_name"])
            agg[key] = agg.get(key, 0) + int(row["count"])

        # Emit oldest-first
        return [
            {"minute_bucket": bucket, "tool_name": tool, "count": count}
            for (bucket, tool), count in sorted(agg.items())
        ]
