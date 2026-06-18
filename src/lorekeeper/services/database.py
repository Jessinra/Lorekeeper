"""Shared SQLite database — connection lifecycle and versioned migrations.

This module owns the SQLite connection and schema evolution for Lorekeeper.
All focused stores (MemoryStore, LinkStore, ReflectionStore, MetricsStore,
ConfigStore) take a `Database` instance and share its single connection.

Migrations are tracked in the `_schema_version` table. The current `migrate()`
implementation applies a single bootstrap migration (version 1) that captures
all schema and idempotent fixups previously embedded in `LinkStore.__init__`.
Future schema changes should be added as new entries in `MIGRATIONS` with
incrementing version numbers.

TODO: After all in-flight migrations (v1 bootstrap, v2 extend_relation_types)
are stable, fold their DDL into BASE_SCHEMA so new installations start with
the final schema directly. Existing DBs should only run migrations that
actually upgrade legacy data — not recreate what BASE_SCHEMA already has.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import structlog

log = structlog.get_logger()

BASE_SCHEMA = """
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
    return datetime.now(UTC).isoformat()


# ── Migration 1 — bootstrap (base schema + historical idempotent fixups) ──────


def _ensure_last_used_column(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    if "last_used" not in existing:
        conn.execute("ALTER TABLE memories ADD COLUMN last_used TEXT")
        log.info("memories_last_used_column_added")


def _ensure_namespace_column(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    if "namespace" not in existing:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN namespace TEXT NOT NULL DEFAULT 'shared'"
        )
        log.info("memories_namespace_column_added")


def _ensure_namespace_scoped_unique_title(conn: sqlite3.Connection) -> None:
    """Migrate unique title index to namespace-scoped unique index."""
    old_idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='idx_memories_unique_title'"
    ).fetchone()
    if not old_idx:
        # No prior unique-title index — create namespace-scoped one
        conn.execute(
            "CREATE UNIQUE INDEX idx_memories_unique_title "
            "ON memories(namespace, title)"
        )
        return
    idx_info = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' "
        "AND name='idx_memories_unique_title'"
    ).fetchone()
    if idx_info and "(namespace, title)" in idx_info["sql"]:
        return  # already namespace-scoped
    conn.execute("DROP INDEX IF EXISTS idx_memories_unique_title")
    conn.execute(
        "CREATE UNIQUE INDEX idx_memories_unique_title "
        "ON memories(namespace, title)"
    )
    log.info("memories_unique_title_migrated_to_namespace_scoped")


def _ensure_session_content_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    new_cols = [
        ("transcript",     "TEXT"),
        ("what_was_done",  "TEXT"),
        ("decisions",      "TEXT"),
        ("lessons_learnt", "TEXT"),
        ("good_patterns",  "TEXT"),
        ("user_profile",   "TEXT"),
        ("discoveries",    "TEXT"),
    ]
    added = []
    for col, col_type in new_cols:
        if col not in existing:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
            added.append(col)
    if added:
        log.info("session_content_columns_added", cols=added)


def _ensure_unique_link_pair(conn: sqlite3.Connection) -> None:
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='idx_links_unique_pair'"
    ).fetchone()
    if idx:
        return
    # Deduplicate any existing duplicates before creating the unique index.
    # On a fresh DB this is a no-op; on legacy DBs it cleans up dupes.
    conn.execute(
        """
        DELETE FROM memory_links WHERE rowid NOT IN (
            SELECT MIN(rowid) FROM memory_links
            GROUP BY source_memory_id, target_memory_id, relation_type
        )
        """
    )
    conn.execute(
        "CREATE UNIQUE INDEX idx_links_unique_pair "
        "ON memory_links(source_memory_id, target_memory_id, relation_type)"
    )


def _ensure_unique_title_seed(conn: sqlite3.Connection) -> None:
    """Legacy dedup step: keep the highest-score row per title on first install.

    On fresh DBs this is a no-op (empty table). On legacy DBs without any
    unique-title index, it dedupes before _ensure_namespace_scoped_unique_title
    creates the namespace-scoped variant. Runs BEFORE the namespace-scoped index
    is created so duplicate non-namespaced titles don't block index creation.
    """
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='idx_memories_unique_title'"
    ).fetchone()
    if idx:
        return  # already deduped via prior install of unique index
    conn.execute(
        """
        DELETE FROM memories WHERE rowid NOT IN (
            SELECT rowid FROM memories m1
            WHERE rowid = (
                SELECT rowid FROM memories m2
                WHERE m2.title = m1.title
                ORDER BY m2.score DESC, m2.created_at ASC
                LIMIT 1
            )
        )
        """
    )


def _migration_1_bootstrap(conn: sqlite3.Connection) -> None:
    """Bootstrap migration — base schema + all historical idempotent fixups.

    Captures everything that LinkStore.__init__ previously did:
    - Apply base schema (CREATE TABLE IF NOT EXISTS for all tables)
    - Dedup any duplicate memory_links rows + add unique pair index
    - Dedup any duplicate memory rows by title (legacy DBs only)
    - Add `last_used` and `namespace` columns to memories
    - Migrate unique title index to namespace-scoped
    - Add session content columns (transcript, decisions, etc.)

    Every step is idempotent — safe to re-apply (though normal flow runs once).
    """
    conn.executescript(BASE_SCHEMA)
    _ensure_unique_link_pair(conn)
    _ensure_unique_title_seed(conn)
    _ensure_session_content_columns(conn)
    _ensure_last_used_column(conn)
    _ensure_namespace_column(conn)
    _ensure_namespace_scoped_unique_title(conn)


def _migration_2_extend_relation_types(conn: sqlite3.Connection) -> None:
    """Extend memory_links CHECK constraint to include all 8 relation types.

    models.py already defines 8 types (added contradicts, supersedes, depends_on)
    but the DB CHECK constraint only allowed 5. SQLite can't ALTER CONSTRAINT,
    so we rebuild the table:
      - Rename old table
      - Create new table with updated CHECK
      - Copy data
      - Drop old table

    Idempotency: if memory_links_old already exists (crash mid-migration on a
    previous run), we skip the RENAME and proceed from the CREATE step so that
    a restart recovers cleanly rather than crashing on "table already exists".
    """
    # Idempotency guard: detect a half-applied previous run
    old_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_links_old'"
    ).fetchone()

    if not old_exists:
        # Normal path — rename first
        conn.execute("ALTER TABLE memory_links RENAME TO memory_links_old")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memory_links (
          id                TEXT PRIMARY KEY,
          source_memory_id  TEXT NOT NULL,
          target_memory_id  TEXT NOT NULL,
          relation_type     TEXT NOT NULL CHECK (relation_type IN
                            ('related_to','used_in','used_for','used_by','used_as',
                             'contradicts','supersedes','depends_on')),
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

        INSERT OR IGNORE INTO memory_links SELECT * FROM memory_links_old;

        DROP TABLE memory_links_old;

        CREATE INDEX IF NOT EXISTS idx_links_source ON memory_links(source_memory_id);
        CREATE INDEX IF NOT EXISTS idx_links_target ON memory_links(target_memory_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_links_unique_pair
            ON memory_links(source_memory_id, target_memory_id, relation_type);
    """)
    log.info("link_relation_types_extended", count=8)


def _migration_3_add_source_type(conn: sqlite3.Connection) -> None:
    """Add source_type column to memories — backfill existing rows as 'unknown'.

    New rows will be written with explicit source_type values by the application;
    rows inserted before this migration get 'unknown' (pre-provenance sentinel).
    Uses column-existence guard so a double-apply is safe.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    if "source_type" not in existing:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN source_type TEXT NOT NULL DEFAULT 'unknown'"
        )
        log.info("memories_source_type_column_added")


# Each entry: (version, name, callable taking sqlite3.Connection).
# Append new migrations here with incrementing version numbers.
MIGRATIONS: list[tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "bootstrap_schema_and_fixups", _migration_1_bootstrap),
    (2, "extend_relation_types", _migration_2_extend_relation_types),
    (3, "add_source_type_to_memories", _migration_3_add_source_type),
]


class Database:
    """Shared SQLite connection + versioned migration runner.

    Used by all focused stores (MemoryStore, LinkStore, ReflectionStore,
    MetricsStore, ConfigStore). Each store accepts a `Database` instance
    and shares its single connection.

    Migrations are tracked via the `_schema_version` table. Pending migrations
    apply in order at `migrate()` time. Each migration runs in its own
    transaction (commit per migration).
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        """Direct access to the underlying sqlite3 connection.

        Stores use this to issue SQL. The Database owns lifecycle (open/close)
        and migrations; stores own their domain queries.
        """
        return self._conn

    def migrate(self) -> None:
        """Apply all pending migrations in version order.

        Each migration runs inside an explicit transaction (BEGIN ... COMMIT/
        ROLLBACK). On success the migration's changes plus the
        `_schema_version` insert commit together; on exception the entire
        transaction rolls back and the exception is re-raised.

        Caveat: migrations that call `executescript()` (notably the bootstrap
        migration) — Python's sqlite3 module COMMITs any pending transaction
        before `executescript()` runs. As a result, migrations that internally
        use `executescript` cannot be rolled back as a whole. The fixup helpers
        used by Migration 1 are all written to be idempotent (CREATE TABLE IF
        NOT EXISTS, column-existence guards, etc.) so a partial-apply followed
        by retry is safe.

        For future migrations that need atomic rollback semantics, use
        `conn.execute()` for individual DDL/DML statements rather than
        `executescript()`.
        """
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        # Ensure the create above is committed before we start per-migration txns
        self._conn.commit()

        current = self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM _schema_version"
        ).fetchone()[0]

        for version, name, fn in MIGRATIONS:
            if version <= current:
                continue
            log.info("schema_migration_applying", version=version, name=name)
            # Explicit BEGIN — Python's sqlite3 doesn't auto-begin for DDL,
            # so without this the migration's CREATE/ALTER statements would
            # execute outside any transaction and could not be rolled back.
            self._conn.execute("BEGIN")
            try:
                fn(self._conn)
                self._conn.execute(
                    "INSERT INTO _schema_version (version, applied_at) "
                    "VALUES (?, ?)",
                    (version, _now()),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                log.exception(
                    "schema_migration_failed", version=version, name=name
                )
                raise
            log.info("schema_migration_applied", version=version, name=name)

    def current_version(self) -> int:
        """Return the highest applied migration version (0 if never migrated)."""
        row = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_version'"
        ).fetchone()
        if row is None:
            return 0
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM _schema_version"
        ).fetchone()
        return int(row[0])

    def close(self) -> None:
        self._conn.close()
