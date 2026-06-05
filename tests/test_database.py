"""Tests for the shared Database class — connection lifecycle + migrations."""

import sqlite3

from lorekeeper.services.database import (
    MIGRATIONS,
    Database,
    _migration_1_bootstrap,
    _migration_2_extend_relation_types,
)


def test_fresh_db_starts_at_version_zero(tmp_path):
    db = Database(tmp_path / "v0.db")
    assert db.current_version() == 0
    db.close()


def test_migrate_applies_bootstrap_to_fresh_db(tmp_path):
    db = Database(tmp_path / "boot.db")
    db.migrate()
    assert db.current_version() == 2

    # All expected tables exist
    tables = {
        row[0]
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    expected = {
        "memories", "memory_links", "reflections", "sessions",
        "api_metrics", "config_overrides", "_schema_version",
    }
    assert expected.issubset(tables)
    db.close()


def test_migrate_is_idempotent(tmp_path):
    db = Database(tmp_path / "idem.db")
    db.migrate()
    db.migrate()
    db.migrate()
    # Only one row in _schema_version per version
    versions = db.conn.execute(
        "SELECT version, COUNT(*) FROM _schema_version GROUP BY version"
    ).fetchall()
    assert all(count == 1 for _, count in versions)
    db.close()


def test_bootstrap_creates_namespace_scoped_unique_title_index(tmp_path):
    db = Database(tmp_path / "ns.db")
    db.migrate()
    idx_sql = db.conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' "
        "AND name='idx_memories_unique_title'"
    ).fetchone()
    assert idx_sql is not None
    assert "(namespace, title)" in idx_sql["sql"]
    db.close()


def test_bootstrap_creates_unique_link_pair_index(tmp_path):
    db = Database(tmp_path / "links.db")
    db.migrate()
    idx = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='idx_links_unique_pair'"
    ).fetchone()
    assert idx is not None
    db.close()


def test_bootstrap_adds_namespace_and_last_used_columns(tmp_path):
    db = Database(tmp_path / "cols.db")
    db.migrate()
    cols = {row[1] for row in db.conn.execute("PRAGMA table_info(memories)")}
    assert "namespace" in cols
    assert "last_used" in cols
    db.close()


def test_bootstrap_adds_session_content_columns(tmp_path):
    db = Database(tmp_path / "sess.db")
    db.migrate()
    cols = {row[1] for row in db.conn.execute("PRAGMA table_info(sessions)")}
    for expected in (
        "transcript", "what_was_done", "decisions",
        "lessons_learnt", "good_patterns", "user_profile", "discoveries",
    ):
        assert expected in cols
    db.close()


def test_wal_mode_and_foreign_keys_enabled(tmp_path):
    db = Database(tmp_path / "wal.db")
    journal_mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    fk = db.conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert journal_mode.lower() == "wal"
    assert fk == 1
    db.close()


def test_unknown_version_in_db_is_treated_as_floor(tmp_path):
    """If _schema_version already has higher version than known MIGRATIONS,
    migrate() must not regress — it just skips since nothing is pending."""
    db = Database(tmp_path / "future.db")
    db.migrate()
    db.conn.execute(
        "INSERT INTO _schema_version (version, applied_at) VALUES (99, ?)",
        ("2099-01-01T00:00:00+00:00",),
    )
    db.conn.commit()
    # Re-running migrate should be a no-op (no version > 99 in MIGRATIONS)
    db.migrate()
    assert db.current_version() == 99
    db.close()


def test_bootstrap_dedups_duplicate_memory_titles_on_legacy_db(tmp_path):
    """Simulate a legacy DB that has duplicate-title memories pre-bootstrap.

    Build the DB manually without the unique index, seed dupes, then run
    bootstrap directly — it should keep the highest-score row per title.
    """
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE memories (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          description TEXT NOT NULL,
          content TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          usage_count INTEGER NOT NULL DEFAULT 0,
          score REAL NOT NULL DEFAULT 1.0,
          soft_deleted INTEGER NOT NULL DEFAULT 0,
          confidence REAL,
          confidence_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    ts = "2026-01-01T00:00:00+00:00"
    conn.execute(
        "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("a", "dup-title", "d", "c", ts, ts, 0, 3.0, 0, None, 0),
    )
    conn.execute(
        "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("b", "dup-title", "d", "c", ts, ts, 0, 7.0, 0, None, 0),
    )
    conn.commit()

    # Apply bootstrap directly on this connection — should dedup
    _migration_1_bootstrap(conn)
    conn.commit()

    rows = conn.execute("SELECT id, score FROM memories").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "b"  # highest score wins
    assert rows[0][1] == 7.0
    conn.close()


def test_migration_2_extends_relation_types_on_populated_db(tmp_path):
    """Migration 2 must survive being applied to a DB with existing link rows.

    Simulates the real-world upgrade: apply only migration 1 manually, seed a
    link row using the old schema's relation types, then apply migration 2 and
    verify the row survived and the new types are now accepted.
    """
    db_path = tmp_path / "m2.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Apply migration 1 only (bootstrap)
    _migration_1_bootstrap(conn)
    conn.commit()

    ts = "2026-01-01T00:00:00+00:00"
    # Insert a memory to satisfy FK constraints
    conn.execute(
        "INSERT INTO memories (id,title,description,content,created_at,updated_at,"
        "usage_count,score,soft_deleted,confidence,confidence_count,namespace) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("mem-a", "A", "", "content a", ts, ts, 0, 5.0, 0, None, 0, "shared"),
    )
    conn.execute(
        "INSERT INTO memories (id,title,description,content,created_at,updated_at,"
        "usage_count,score,soft_deleted,confidence,confidence_count,namespace) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        ("mem-b", "B", "", "content b", ts, ts, 0, 5.0, 0, None, 0, "shared"),
    )
    # Insert a link with a relation type that must survive migration 2
    conn.execute(
        "INSERT INTO memory_links (id,source_memory_id,target_memory_id,relation_type,"
        "reason,score,created_at,updated_at,usage_count,confidence,confidence_count) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("lnk-1", "mem-a", "mem-b", "related_to", "test", 1.0, ts, ts, 0, None, 0),
    )
    conn.commit()

    # Apply migration 2
    _migration_2_extend_relation_types(conn)
    conn.commit()

    # Existing row must still be there
    row = conn.execute("SELECT * FROM memory_links WHERE id='lnk-1'").fetchone()
    assert row is not None
    assert row["relation_type"] == "related_to"

    # New relation types must now be accepted by the CHECK constraint
    for new_type in ("contradicts", "supersedes", "depends_on"):
        conn.execute(
            "INSERT INTO memory_links (id,source_memory_id,target_memory_id,relation_type,"
            "reason,score,created_at,updated_at,usage_count,confidence,confidence_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (f"lnk-{new_type}", "mem-a", "mem-b", new_type, "test", 1.0, ts, ts, 0, None, 0),
        )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM memory_links").fetchone()[0]
    assert count == 4  # original + 3 new types

    conn.close()


def test_migrations_list_versions_strictly_increasing():
    versions = [v for v, _, _ in MIGRATIONS]
    assert versions == sorted(set(versions))
    assert versions[0] == 1


def test_migrate_rolls_back_on_failure_and_does_not_record_version(tmp_path):
    """If a migration raises mid-apply, the `with self._conn:` context manager
    must roll back: no _schema_version row gets inserted, and the migration
    is retried on the next migrate() call.
    """
    import pytest

    from lorekeeper.services import database as db_module

    db = Database(tmp_path / "rollback.db")
    db.migrate()  # apply v1 + v2 baseline
    assert db.current_version() == 2

    # Inject a failing v2 migration into the MIGRATIONS list, then call migrate().
    calls = {"count": 0}

    def _failing_migration(conn):
        calls["count"] += 1
        # Make a real schema change so we can verify the rollback undoes it
        conn.execute("CREATE TABLE failing_marker (id INTEGER PRIMARY KEY)")
        raise RuntimeError("simulated migration failure")

    original = list(db_module.MIGRATIONS)
    db_module.MIGRATIONS.append((3, "failing_v3", _failing_migration))
    try:
        with pytest.raises(RuntimeError, match="simulated migration failure"):
            db.migrate()

        # Schema version must NOT have advanced
        assert db.current_version() == 2

        # The CREATE TABLE inside the failed migration must have been rolled back
        table = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='failing_marker'"
        ).fetchone()
        assert table is None, "failed migration's schema change was not rolled back"

        # And the failing migration was attempted exactly once
        assert calls["count"] == 1
    finally:
        # Restore registry so other tests aren't affected
        db_module.MIGRATIONS[:] = original
        db.close()
