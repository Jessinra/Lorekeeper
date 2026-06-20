"""Memory link CRUD.

Post-LKPR-51, this module owns only the `memory_links` table. Memory rows,
reflections, sessions, metrics, and config overrides each have their own
focused store. The shared `Database` class owns connection lifecycle and
migrations — `LinkStore` just executes link queries on the connection it
gets from `Database`.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from lorekeeper.models import TYPE_MIGRATION_MAP, LinkSuggestion, MemoryLink
from lorekeeper.services.database import Database

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


class LinkSuggestionStore:
    """CRUD for the `link_suggestions` table (LKPR-99).

    Stores candidate link pairs generated by the sweep engine. All suggestions
    use canonical pair ordering: min(id1, id2) as source, max(id1, id2) as
    target — enforced by insert_suggestion / upsert_suggestion.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    # ── Pair ordering ───────────────────────────────────────────────────────

    @staticmethod
    def _canonical(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)

    # ── CRUD ────────────────────────────────────────────────────────────────

    def insert_suggestion(
        self,
        source_memory_id: str,
        target_memory_id: str,
        source_title: str,
        target_title: str,
        weighted_score: float,
        cosine_score: float = 0.0,
        bm25_score: float = 0.0,
        entity_score: float = 0.0,
        temporal_score: float = 0.0,
        suggested_type: str | None = None,
        confidence: str = "standard",
        status: str = "pending",
        id: str | None = None,
    ) -> LinkSuggestion:
        src, tgt = self._canonical(source_memory_id, target_memory_id)
        now = _now()
        s = LinkSuggestion(
            id=id or str(uuid.uuid4()),
            source_memory_id=src,
            target_memory_id=tgt,
            source_title=source_title,
            target_title=target_title,
            weighted_score=weighted_score,
            cosine_score=cosine_score,
            bm25_score=bm25_score,
            entity_score=entity_score,
            temporal_score=temporal_score,
            suggested_type=suggested_type,
            confidence=confidence,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._conn.execute(
            """INSERT INTO link_suggestions
               (id, source_memory_id, target_memory_id, source_title, target_title,
                weighted_score, cosine_score, bm25_score, entity_score, temporal_score,
                suggested_type, confidence, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s.id, s.source_memory_id, s.target_memory_id,
             s.source_title, s.target_title,
             s.weighted_score, s.cosine_score, s.bm25_score,
             s.entity_score, s.temporal_score,
             s.suggested_type, s.confidence, s.status,
             s.created_at, s.updated_at),
        )
        return s

    def upsert_suggestion(
        self,
        source_memory_id: str,
        target_memory_id: str,
        source_title: str,
        target_title: str,
        weighted_score: float,
        cosine_score: float = 0.0,
        bm25_score: float = 0.0,
        entity_score: float = 0.0,
        temporal_score: float = 0.0,
        suggested_type: str | None = None,
        confidence: str = "standard",
        status: str = "pending",
        id: str | None = None,
    ) -> LinkSuggestion:
        src, tgt = self._canonical(source_memory_id, target_memory_id)
        now = _now()
        s = LinkSuggestion(
            id=id or str(uuid.uuid4()),
            source_memory_id=src,
            target_memory_id=tgt,
            source_title=source_title,
            target_title=target_title,
            weighted_score=weighted_score,
            cosine_score=cosine_score,
            bm25_score=bm25_score,
            entity_score=entity_score,
            temporal_score=temporal_score,
            suggested_type=suggested_type,
            confidence=confidence,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._conn.execute(
            """INSERT OR REPLACE INTO link_suggestions
               (id, source_memory_id, target_memory_id, source_title, target_title,
                weighted_score, cosine_score, bm25_score, entity_score, temporal_score,
                suggested_type, confidence, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s.id, s.source_memory_id, s.target_memory_id,
             s.source_title, s.target_title,
             s.weighted_score, s.cosine_score, s.bm25_score,
             s.entity_score, s.temporal_score,
             s.suggested_type, s.confidence, s.status,
             s.created_at, s.updated_at),
        )
        return s

    def get_suggestion(self, suggestion_id: str) -> LinkSuggestion | None:
        row = self._conn.execute(
            "SELECT * FROM link_suggestions WHERE id = ?", (suggestion_id,)
        ).fetchone()
        return _row_to_suggestion(row) if row else None

    def get_suggestions_for_memory(
        self, memory_id: str, status: str | None = None
    ) -> list[LinkSuggestion]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM link_suggestions "
                "WHERE (source_memory_id = ? OR target_memory_id = ?) AND status = ?",
                (memory_id, memory_id, status),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM link_suggestions "
                "WHERE source_memory_id = ? OR target_memory_id = ?",
                (memory_id, memory_id),
            ).fetchall()
        return [_row_to_suggestion(r) for r in rows]

    def all_pending_suggestions(self) -> list[LinkSuggestion]:
        rows = self._conn.execute(
            "SELECT * FROM link_suggestions WHERE status = 'pending' "
            "ORDER BY weighted_score DESC"
        ).fetchall()
        return [_row_to_suggestion(r) for r in rows]

    def update_suggestion_status(
        self, suggestion_id: str, status: str
    ) -> None:
        self._conn.execute(
            "UPDATE link_suggestions SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), suggestion_id),
        )

    def delete_suggestion(self, suggestion_id: str) -> None:
        self._conn.execute(
            "DELETE FROM link_suggestions WHERE id = ?", (suggestion_id,)
        )

    def rejected_pairs(self) -> set[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT source_memory_id, target_memory_id FROM link_suggestions "
            "WHERE status = 'rejected'"
        ).fetchall()
        return {(r["source_memory_id"], r["target_memory_id"]) for r in rows}

    def prune_expired(self, ttl_days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=ttl_days)
        cursor = self._conn.execute(
            "DELETE FROM link_suggestions WHERE updated_at < ?",
            (cutoff.isoformat(),),
        )
        return cursor.rowcount


def _row_to_suggestion(row: sqlite3.Row) -> LinkSuggestion:
    return LinkSuggestion(
        id=row["id"],
        source_memory_id=row["source_memory_id"],
        target_memory_id=row["target_memory_id"],
        source_title=row["source_title"],
        target_title=row["target_title"],
        weighted_score=row["weighted_score"],
        cosine_score=row["cosine_score"],
        bm25_score=row["bm25_score"],
        entity_score=row["entity_score"],
        temporal_score=row["temporal_score"],
        suggested_type=row["suggested_type"],
        confidence=row["confidence"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
