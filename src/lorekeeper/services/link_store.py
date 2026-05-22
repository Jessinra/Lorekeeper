import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog

from lorekeeper.models import MemoryLink

log = structlog.get_logger()

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

CREATE TABLE IF NOT EXISTS reflections (
  id                   TEXT PRIMARY KEY,
  created_at           TEXT NOT NULL,
  session_count        INTEGER NOT NULL,
  lessons_learnt       TEXT NOT NULL,
  good_patterns        TEXT,
  user_profile_updates TEXT,
  factual_discoveries  TEXT,
  summary              TEXT NOT NULL,
  memory_ids           TEXT
);

CREATE INDEX IF NOT EXISTS idx_reflections_created_at ON reflections(created_at);

CREATE TABLE IF NOT EXISTS sessions (
  session_id    TEXT PRIMARY KEY,
  session_date  TEXT,
  topic         TEXT,
  task_type     TEXT,
  reviewed_at   TEXT NOT NULL,
  reflection_id TEXT,
  FOREIGN KEY (reflection_id) REFERENCES reflections(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_reflection_id ON sessions(reflection_id);

CREATE TABLE IF NOT EXISTS api_metrics (
  minute_bucket  TEXT NOT NULL,
  tool_name      TEXT NOT NULL,
  count          INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (minute_bucket, tool_name)
);

CREATE INDEX IF NOT EXISTS idx_api_metrics_bucket ON api_metrics(minute_bucket);

CREATE TABLE IF NOT EXISTS config_overrides (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LinkStore:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Idempotent migrations run after schema creation."""
        self._migrate_dedup_links()
        self._migrate_dedup_memories()
        self._migrate_add_session_content_columns()

    def _migrate_add_session_content_columns(self) -> None:
        existing = {row[1] for row in self._conn.execute("PRAGMA table_info(sessions)")}
        new_cols = [
            ("transcript",    "TEXT"),
            ("what_was_done", "TEXT"),
            ("decisions",     "TEXT"),
            ("lessons_learnt","TEXT"),
            ("good_patterns", "TEXT"),
            ("user_profile",  "TEXT"),
            ("discoveries",   "TEXT"),
        ]
        added = []
        for col, col_type in new_cols:
            if col not in existing:
                self._conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
                added.append(col)
        if added:
            self._conn.commit()
            log.info("session_content_columns_added", cols=added)

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
        except sqlite3.IntegrityError as exc:
            # Re-raise FK violations — only swallow unique-constraint duplicates
            if "FOREIGN KEY" in str(exc).upper():
                raise
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

    # ── Reflections ───────────────────────────────────────────────────────────

    def insert_reflection(
        self,
        id: str,
        created_at: str,
        session_count: int,
        lessons_learnt: str,
        summary: str,
        good_patterns: str | None = None,
        user_profile_updates: str | None = None,
        factual_discoveries: str | None = None,
        memory_ids: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO reflections
              (id, created_at, session_count, lessons_learnt, good_patterns,
               user_profile_updates, factual_discoveries, summary, memory_ids)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (id, created_at, session_count, lessons_learnt, good_patterns,
             user_profile_updates, factual_discoveries, summary, memory_ids),
        )
        self._conn.commit()

    def get_reflection(self, reflection_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM reflections WHERE id = ?", (reflection_id,)
        ).fetchone()

    def all_reflections(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM reflections ORDER BY created_at DESC"
        ).fetchall()

    # ── Sessions ──────────────────────────────────────────────────────────────

    _SESSION_UPSERT_SQL = """
        INSERT INTO sessions
          (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
           transcript, what_was_done, decisions, lessons_learnt, good_patterns, user_profile, discoveries)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET
          session_date=COALESCE(excluded.session_date, session_date),
          topic=COALESCE(excluded.topic, topic),
          task_type=COALESCE(excluded.task_type, task_type),
          reviewed_at=excluded.reviewed_at,
          reflection_id=COALESCE(excluded.reflection_id, reflection_id),
          transcript=COALESCE(excluded.transcript, transcript),
          what_was_done=COALESCE(excluded.what_was_done, what_was_done),
          decisions=COALESCE(excluded.decisions, decisions),
          lessons_learnt=COALESCE(excluded.lessons_learnt, lessons_learnt),
          good_patterns=COALESCE(excluded.good_patterns, good_patterns),
          user_profile=COALESCE(excluded.user_profile, user_profile),
          discoveries=COALESCE(excluded.discoveries, discoveries)
    """

    def upsert_session(
        self,
        session_id: str,
        reviewed_at: str,
        session_date: str | None = None,
        topic: str | None = None,
        task_type: str | None = None,
        reflection_id: str | None = None,
        transcript: str | None = None,
        what_was_done: str | None = None,
        decisions: str | None = None,
        lessons_learnt: str | None = None,
        good_patterns: str | None = None,
        user_profile: str | None = None,
        discoveries: str | None = None,
    ) -> None:
        self._conn.execute(
            self._SESSION_UPSERT_SQL,
            (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
             transcript, what_was_done, decisions, lessons_learnt, good_patterns, user_profile, discoveries),
        )
        self._conn.commit()

    def upsert_sessions_bulk(self, rows: list[tuple]) -> None:
        """Insert/update multiple sessions in a single transaction.

        Each tuple: (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
                     transcript, what_was_done, decisions, lessons_learnt, good_patterns,
                     user_profile, discoveries)
        """
        self._conn.executemany(self._SESSION_UPSERT_SQL, rows)
        self._conn.commit()

    def all_processed_session_ids(self) -> set[str]:
        """Return all session IDs that have been marked as processed. Used by loop skill scripts."""
        rows = self._conn.execute("SELECT session_id FROM sessions").fetchall()
        return {r["session_id"] for r in rows}

    def all_sessions(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions ORDER BY reviewed_at DESC"
        ).fetchall()

    def sessions_with_content(self) -> list[sqlite3.Row]:
        """Sessions that have a topic (i.e. were matched to a session log)."""
        return self._conn.execute(
            "SELECT * FROM sessions WHERE topic IS NOT NULL ORDER BY session_date DESC, topic"
        ).fetchall()

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

    def sessions_for_reflection(self, reflection_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions WHERE reflection_id = ? ORDER BY session_date, session_id",
            (reflection_id,),
        ).fetchall()

    def close(self) -> None:
        self._conn.close()

    # ── API metrics ───────────────────────────────────────────────────────────

    def increment_metric(self, tool_name: str) -> None:
        """Increment the call counter for tool_name, bucketed to the current UTC hour."""
        bucket = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:00")
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
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(bucket, fmt).strftime("%Y-%m-%d %H:00")
            except ValueError:
                continue
        return bucket  # already normalized or unknown — return as-is

    def get_metrics(self, hours: int = 24) -> list[dict]:
        """Return all metric rows within the last `hours` hours, oldest first."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:00")
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
            {"minute_bucket": self._normalize_bucket(row["minute_bucket"]), "tool_name": row["tool_name"], "count": row["count"]}
            for row in rows
        ]


    # ── Config overrides ──────────────────────────────────────────────────────

    def get_config_overrides(self) -> dict:
        """Return all persisted config overrides as a {key: value} dict."""
        import json
        rows = self._conn.execute("SELECT key, value FROM config_overrides").fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def set_config_override(self, key: str, value: object) -> None:
        """Upsert a single config override, persisting it across restarts."""
        import json
        self._conn.execute(
            """
            INSERT INTO config_overrides (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), _now()),
        )
        self._conn.commit()

    def delete_config_override(self, key: str) -> None:
        """Remove a persisted config override (falls back to env/default on next restart)."""
        self._conn.execute("DELETE FROM config_overrides WHERE key = ?", (key,))
        self._conn.commit()


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
