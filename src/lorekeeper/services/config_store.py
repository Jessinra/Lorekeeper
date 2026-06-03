"""Config overrides — extracted from LinkStore as part of LKPR-51.

Stores dashboard-edited config values that survive process restarts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from lorekeeper.services.database import Database


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConfigStore:
    """CRUD for the `config_overrides` table (JSON-serialized values)."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def get_overrides(self) -> dict:
        """Return all persisted config overrides as a {key: value} dict."""
        rows = self._conn.execute(
            "SELECT key, value FROM config_overrides"
        ).fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def set_override(self, key: str, value: object) -> None:
        """Upsert a single config override, persisting it across restarts."""
        self._conn.execute(
            """
            INSERT INTO config_overrides (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), _now()),
        )

    def delete_override(self, key: str) -> None:
        """Remove a persisted override (falls back to env/default on restart)."""
        self._conn.execute(
            "DELETE FROM config_overrides WHERE key = ?", (key,)
        )
