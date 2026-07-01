"""Config overrides — extracted from LinkStore as part of LKPR-51.

Stores dashboard-edited config values that survive process restarts.

LKPR-104 Phase 6b: transaction control (commit) is the caller's
responsibility, not the repository's — callers that need persistence
must call either their broader facade ``commit()`` or
``ConfigStore.commit()`` after invoking these methods. The
scheduler's ``PeriodicJob`` calls ``ConfigStore.commit()``
explicitly after each timer write.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from lorekeeper.infra.database import Database


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ConfigStore:
    """CRUD for the `config_overrides` table (JSON-serialized values)."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def get_overrides(self) -> dict[str, Any]:
        """Return all persisted config overrides as a {key: value} dict."""
        rows = self._conn.execute(
            "SELECT key, value FROM config_overrides"
        ).fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def set_override(self, key: str, value: object) -> None:
        """Upsert a single config override.

        Does not commit — the caller owns the transaction boundary
        (dashboard routes call ``svc.commit()`` after this).
        """
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
        """Remove a persisted override (falls back to env/default on restart).

        Does not commit — the caller owns the transaction boundary.
        """
        self._conn.execute(
            "DELETE FROM config_overrides WHERE key = ?", (key,)
        )

    def commit(self) -> None:
        """Flush pending writes to disk.

        Convenience for callers (e.g. ``PeriodicJob``) that only touch
        config overrides and have no broader facade `commit()` to call.
        """
        self._conn.commit()
