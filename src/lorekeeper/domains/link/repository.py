"""Memory link CRUD.

Post-LKPR-51, this module owns only the ``memory_links`` table. Memory rows,
reflections, sessions, metrics, and config overrides each have their own
focused store. The shared ``Database`` class owns connection lifecycle and
migrations — ``LinkStore`` just executes link queries on the connection it
gets from ``Database``.

**LinkSuggestionStore** was extracted to ``suggestion_store.py`` (LKPR-99).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import structlog

from lorekeeper.domains.link.models import TYPE_MIGRATION_MAP, MemoryLink
from lorekeeper.infra.database import Database

log = structlog.get_logger()


def _now() -> str:
    return datetime.now(UTC).isoformat()


class LinkStore:
    """CRUD for the `memory_links` table."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def insert_link(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relation_type: str,
        reason: str,
        score: float = 1.0,
        id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        usage_count: int = 0,
        confidence: float | None = None,
        confidence_count: int = 0,
    ) -> MemoryLink:
        now = _now()
        link = MemoryLink(
            id=id or str(uuid.uuid4()),
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relation_type=relation_type,  # type: ignore[arg-type]
            reason=reason,
            score=score,
            created_at=created_at or now,
            updated_at=updated_at or now,
            usage_count=usage_count,
            confidence=confidence,
            confidence_count=confidence_count,
        )
        try:
            self._conn.execute(
                """
                INSERT INTO memory_links
                  (id, source_memory_id, target_memory_id, relation_type, reason,
                   score, created_at, updated_at, usage_count, confidence,
                   confidence_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (link.id, link.source_memory_id, link.target_memory_id,
                 link.relation_type, link.reason, link.score,
                 link.created_at, link.updated_at,
                 link.usage_count, link.confidence, link.confidence_count),
            )
        except sqlite3.IntegrityError as exc:
            # Re-raise FK violations — only swallow the expected unique-pair
            # duplicate case (same source + target + relation_type already exists).
            if "FOREIGN KEY" in str(exc).upper():
                raise
            # Look up the existing link for the duplicate-pair case. If found,
            # return it (idempotent insert). If NOT found, the IntegrityError
            # was something else (e.g. UUID collision on `id`) — re-raise so
            # the real failure isn't hidden.
            row = self._conn.execute(
                """
                SELECT * FROM memory_links
                WHERE source_memory_id = ? AND target_memory_id = ?
                  AND relation_type = ?
                """,
                (link.source_memory_id, link.target_memory_id, link.relation_type),
            ).fetchone()
            if row is None:
                raise
            return _row_to_link(row)
        return link

    def links_for_memory(self, memory_id: str) -> list[MemoryLink]:
        rows = self._conn.execute(
            """
            SELECT * FROM memory_links
            WHERE source_memory_id = ? OR target_memory_id = ?
            """,
            (memory_id, memory_id),
        ).fetchall()
        return [_row_to_link(r) for r in rows]

    def get_link(self, link_id: str) -> MemoryLink | None:
        row = self._conn.execute(
            "SELECT * FROM memory_links WHERE id = ?", (link_id,)
        ).fetchone()
        return _row_to_link(row) if row else None

    def update_link_fields(self, link_id: str, **fields: object) -> None:
        allowed = {"score", "usage_count", "confidence", "confidence_count", "reason"}
        cols = {k: v for k, v in fields.items() if k in allowed}
        if not cols:
            return
        cols["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in cols)
        self._conn.execute(
            f"UPDATE memory_links SET {set_clause} WHERE id = ?",
            (*cols.values(), link_id),
        )

    def all_links(self) -> list[MemoryLink]:
        rows = self._conn.execute(
            "SELECT * FROM memory_links ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_link(r) for r in rows]

    def delete_link(self, link_id: str) -> None:
        self._conn.execute(
            "DELETE FROM memory_links WHERE id = ?", (link_id,)
        )

    def count_links_for_memory(self, memory_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM memory_links WHERE source_memory_id = ? OR target_memory_id = ?",
            (memory_id, memory_id),
        ).fetchone()
        return row[0] if row else 0

    def count_links_for_memories(self, memory_ids: list[str]) -> dict[str, int]:
        """Batch link counts for multiple memory IDs — one query, no N+1.

        Returns {memory_id: count} for every ID in the input list.
        IDs with zero links are included as 0.
        """
        if not memory_ids:
            return {}
        placeholders = ",".join("?" * len(memory_ids))
        in_clause = f"IN ({placeholders})"
        rows = self._conn.execute(
            f"""
            SELECT id, COUNT(*) AS cnt FROM (
                SELECT source_memory_id AS id FROM memory_links WHERE source_memory_id {in_clause}
                UNION ALL
                SELECT target_memory_id AS id FROM memory_links WHERE target_memory_id {in_clause}
            ) GROUP BY id
            """,
            (*memory_ids, *memory_ids),
        ).fetchall()
        result: dict[str, int] = dict.fromkeys(memory_ids, 0)
        for r in rows:
            result[r[0]] = r[1]
        return result


def _row_to_link(row: sqlite3.Row) -> MemoryLink:
    raw_type = row["relation_type"]
    normalized_type = TYPE_MIGRATION_MAP.get(raw_type, raw_type)
    return MemoryLink(
        id=row["id"],
        source_memory_id=row["source_memory_id"],
        target_memory_id=row["target_memory_id"],
        relation_type=normalized_type,
        reason=row["reason"],
        score=row["score"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        usage_count=row["usage_count"],
        confidence=row["confidence"],
        confidence_count=row["confidence_count"],
    )



