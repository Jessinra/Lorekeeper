import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from lorekeeper.models import MemoryLink

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memories (
  id               TEXT PRIMARY KEY,
  title            TEXT NOT NULL,
  description      TEXT NOT NULL,
  content          TEXT NOT NULL,
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL,
  usage_count      INTEGER NOT NULL DEFAULT 0,
  score            REAL    NOT NULL DEFAULT 1.0,
  soft_deleted     INTEGER NOT NULL DEFAULT 0,
  confidence       REAL,
  confidence_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_soft_deleted ON memories(soft_deleted);

CREATE TABLE IF NOT EXISTS memory_links (
  id                TEXT PRIMARY KEY,
  source_memory_id  TEXT NOT NULL,
  target_memory_id  TEXT NOT NULL,
  relation_type     TEXT NOT NULL CHECK (relation_type IN
                      ('related_to','used_in','used_for','used_by','used_as')),
  reason            TEXT NOT NULL,
  score             REAL    NOT NULL DEFAULT 1.0,
  created_at        TEXT    NOT NULL,
  updated_at        TEXT    NOT NULL,
  usage_count       INTEGER NOT NULL DEFAULT 0,
  confidence        REAL,
  confidence_count  INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
  FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_memory_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LinkStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Idempotent migrations run after schema creation."""
        self._migrate_dedup_links()
        self._migrate_dedup_memories()

    def _migrate_dedup_links(self) -> None:
        idx = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_links_unique_pair'"
        ).fetchone()
        if idx:
            return
        self._conn.execute("""
            DELETE FROM memory_links WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM memory_links
                GROUP BY source_memory_id, target_memory_id, relation_type
            )
        """)
        self._conn.execute("""
            CREATE UNIQUE INDEX idx_links_unique_pair
            ON memory_links(source_memory_id, target_memory_id, relation_type)
        """)
        self._conn.commit()

    def _migrate_dedup_memories(self) -> None:
        idx = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_memories_unique_title'"
        ).fetchone()
        if idx:
            return
        # Keep the highest-score row per title; delete the rest
        self._conn.execute("""
            DELETE FROM memories WHERE rowid NOT IN (
                SELECT rowid FROM memories m1
                WHERE rowid = (
                    SELECT rowid FROM memories m2
                    WHERE m2.title = m1.title
                    ORDER BY m2.score DESC, m2.created_at ASC
                    LIMIT 1
                )
            )
        """)
        self._conn.execute("""
            CREATE UNIQUE INDEX idx_memories_unique_title ON memories(title)
        """)
        self._conn.commit()

    # ── Memory rows (managed here so FKs are satisfied) ──────────────────────

    def upsert_memory_row(
        self,
        id: str,
        title: str,
        description: str,
        content: str,
        created_at: str,
        updated_at: str,
        usage_count: int = 0,
        score: float = 1.0,
        soft_deleted: bool = False,
        confidence: float | None = None,
        confidence_count: int = 0,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO memories
              (id, title, description, content, created_at, updated_at,
               usage_count, score, soft_deleted, confidence, confidence_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, description=excluded.description,
              content=excluded.content, updated_at=excluded.updated_at,
              usage_count=excluded.usage_count, score=excluded.score,
              soft_deleted=excluded.soft_deleted, confidence=excluded.confidence,
              confidence_count=excluded.confidence_count
            """,
            (id, title, description, content, created_at, updated_at,
             usage_count, score, int(soft_deleted), confidence, confidence_count),
        )
        self._conn.commit()

    def get_memory_row(self, id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (id,)
        ).fetchone()

    def get_memory_row_by_title(self, title: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM memories WHERE title = ? AND soft_deleted = 0 ORDER BY score DESC LIMIT 1",
            (title,),
        ).fetchone()

    def all_memory_rows(self, include_deleted: bool = False) -> list[sqlite3.Row]:
        if include_deleted:
            return self._conn.execute("SELECT * FROM memories").fetchall()
        return self._conn.execute(
            "SELECT * FROM memories WHERE soft_deleted = 0"
        ).fetchall()

    def update_memory_fields(self, id: str, **fields: object) -> None:
        allowed = {
            "score", "usage_count", "soft_deleted",
            "confidence", "confidence_count", "updated_at",
            "title", "description", "content",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if not cols:
            return
        cols["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in cols)
        self._conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id = ?",
            (*cols.values(), id),
        )
        self._conn.commit()

    def delete_memory_row(self, id: str) -> None:
        self._conn.execute("DELETE FROM memories WHERE id = ?", (id,))
        self._conn.commit()

    # ── Links ─────────────────────────────────────────────────────────────────

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
                   score, created_at, updated_at, usage_count, confidence, confidence_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (link.id, link.source_memory_id, link.target_memory_id,
                 link.relation_type, link.reason, link.score, link.created_at, link.updated_at,
                 link.usage_count, link.confidence, link.confidence_count),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            # Duplicate (source, target, relation_type) — return the existing link
            row = self._conn.execute(
                """
                SELECT * FROM memory_links
                WHERE source_memory_id = ? AND target_memory_id = ? AND relation_type = ?
                """,
                (link.source_memory_id, link.target_memory_id, link.relation_type),
            ).fetchone()
            if row:
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
        self._conn.commit()

    def all_links(self) -> list[MemoryLink]:
        rows = self._conn.execute(
            "SELECT * FROM memory_links ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_link(r) for r in rows]

    def delete_link(self, link_id: str) -> None:
        self._conn.execute("DELETE FROM memory_links WHERE id = ?", (link_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _row_to_link(row: sqlite3.Row) -> MemoryLink:
    return MemoryLink(
        id=row["id"],
        source_memory_id=row["source_memory_id"],
        target_memory_id=row["target_memory_id"],
        relation_type=row["relation_type"],
        reason=row["reason"],
        score=row["score"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        usage_count=row["usage_count"],
        confidence=row["confidence"],
        confidence_count=row["confidence_count"],
    )
