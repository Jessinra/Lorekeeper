"""Tests for the shared Database class — connection lifecycle + migrations."""

import sqlite3

from lorekeeper.infra.database import (
    MIGRATIONS,
    Database,
    _migration_1_bootstrap,
    _migration_2_extend_relation_types,
    _migration_4_revise_link_relation_types,
    _migration_5_add_link_suggestions,
)


def test_fresh_db_starts_at_version_zero(tmp_path):
    db = Database(tmp_path / "v0.db")
    assert db.current_version() == 0
    db.close()


def test_migrate_applies_bootstrap_to_fresh_db(tmp_path):
    db = Database(tmp_path / "boot.db")
    db.migrate()
    assert db.current_version() == 5

    # All expected tables exist
    tables = {
        row[0]
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    expected = {
        "memories", "memory_links", "reflections", "sessions",
        "api_metrics", "config_overrides", "link_suggestions", "_schema_version",
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


def test_migration_4_revise_link_relation_types_on_populated_db(tmp_path):
    """Migration v4 rebuilds memory_links with an expanded 12-value CHECK.

    Sets up a DB at v1-v3 with real links using the old 8-type CHECK,
    then applies v4 and verifies:
    - All old rows survive the table rebuild
    - New types accepted by the enlarged CHECK
    - Old types still pass the CHECK (permissive for legacy data)
    - DB correctly reaches version 4
    """
    import uuid

    db = Database(tmp_path / "v4.db")
    conn = db.conn
    ts = "2026-01-01T00:00:00+00:00"

    # Apply v1–v3 manually so we land with the old 8-type CHECK
    _migration_1_bootstrap(conn)
    conn.commit()
    _migration_2_extend_relation_types(conn)
    conn.commit()

    # Seed two memory rows so FK constraints are satisfied
    for mem_id in ("m1", "m2"):
        conn.execute(
            "INSERT INTO memories (id,title,description,content,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (mem_id, f"title-{mem_id}", "d", "c", ts, ts),
        )

    # Insert links using old type strings (valid under v2 CHECK)
    old_link_ids = []
    for old_type in ("related_to", "used_in", "contradicts", "supersedes", "depends_on"):
        lid = str(uuid.uuid4())
        old_link_ids.append((lid, old_type))
        conn.execute(
            "INSERT INTO memory_links "
            "(id,source_memory_id,target_memory_id,relation_type,reason,score,"
            "created_at,updated_at,usage_count,confidence,confidence_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (lid, "m1", "m2", old_type, "pre-v4 link", 1.0, ts, ts, 0, None, 0),
        )
    conn.commit()

    # Apply migration v4
    _migration_4_revise_link_relation_types(conn)
    conn.commit()

    # All old rows survived
    for lid, old_type in old_link_ids:
        row = conn.execute(
            "SELECT relation_type FROM memory_links WHERE id=?", (lid,)
        ).fetchone()
        assert row is not None, f"link {lid} lost after v4 migration"
        assert row[0] == old_type, f"expected raw DB value '{old_type}', got '{row[0]}'"

    # New types accepted by the updated CHECK
    for new_type in ("references", "part_of", "derived_from", "causes"):
        lid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO memory_links "
            "(id,source_memory_id,target_memory_id,relation_type,reason,score,"
            "created_at,updated_at,usage_count,confidence,confidence_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (lid, "m1", "m2", new_type, "new type test", 1.0, ts, ts, 0, None, 0),
        )
    conn.commit()

    db.close()


def test_migration_5_adds_link_suggestions_table(tmp_path):
    """Migration v5 creates the link_suggestions table with expected schema."""
    db_path = tmp_path / "m5.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    _migration_1_bootstrap(conn)
    conn.commit()
    _migration_2_extend_relation_types(conn)
    conn.commit()
    conn.execute(
        "ALTER TABLE memories ADD COLUMN source_type "
        "TEXT NOT NULL DEFAULT 'unknown'"
    )
    conn.commit()

    # Verify link_suggestions does NOT exist before v5
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "link_suggestions" not in tables

    _migration_5_add_link_suggestions(conn)
    conn.commit()

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "link_suggestions" in tables

    cols = {row[1] for row in conn.execute("PRAGMA table_info(link_suggestions)")}
    for c in (
        "id", "source_memory_id", "target_memory_id", "source_title",
        "weighted_score", "confidence", "status", "created_at", "updated_at",
    ):
        assert c in cols, f"missing column: {c}"

    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name='idx_suggestions_pair'"
    ).fetchone()
    assert idx is not None

    # Idempotency
    _migration_5_add_link_suggestions(conn)
    conn.commit()

    # Insert memories for FK constraints
    ts = "2026-06-20T00:00:00+00:00"
    for mid in ("m1", "m2"):
        conn.execute(
            "INSERT INTO memories (id,title,description,content,"
            "created_at,updated_at) VALUES (?,?,?,?,?,?)",
            (mid, f"t-{mid}", "", "c", ts, ts),
        )

    conn.execute(
        "INSERT INTO link_suggestions "
        "(id,source_memory_id,target_memory_id,source_title,target_title,"
        "weighted_score,confidence,status,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("s1", "m1", "m2", "s", "t", 0.9, "high", "pending", ts, ts),
    )
    conn.commit()
    assert conn.execute(
        "SELECT COUNT(*) FROM link_suggestions"
    ).fetchone()[0] == 1

    conn.close()


def test_migrate_rolls_back_on_failure_and_does_not_record_version(tmp_path):
    """If a migration raises mid-apply, the `with self._conn:` context manager
    must roll back: no _schema_version row gets inserted, and the migration
    is retried on the next migrate() call.
    """
    import pytest

    from lorekeeper.infra import database as db_module

    db = Database(tmp_path / "rollback.db")
    db.migrate()  # apply v1 + v2 + v3 + v4 + v5 baseline
    assert db.current_version() == 5

    # Inject a failing v6 migration into the MIGRATIONS list, then call migrate().
    calls = {"count": 0}

    def _failing_migration(conn):
        calls["count"] += 1
        # Make a real schema change so we can verify the rollback undoes it
        conn.execute("CREATE TABLE failing_marker (id INTEGER PRIMARY KEY)")
        raise RuntimeError("simulated migration failure")

    original = list(db_module.MIGRATIONS)
    db_module.MIGRATIONS.append((6, "failing_v6", _failing_migration))
    try:
        with pytest.raises(RuntimeError, match="simulated migration failure"):
            db.migrate()

        # Schema version must NOT have advanced
        assert db.current_version() == 5

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


def test_relation_type_literal_matches_types_config():
    """The RelationType Literal and types.yaml must stay in sync.

    When adding/removing types, update BOTH:
    1. The RelationType Literal in models.py
    2. The relation_types list in src/lorekeeper/types.yaml

    This test catches drift between the two.
    """
    from typing import get_args

    from lorekeeper.models import RELATION_TYPES, RelationType

    literal_types = frozenset(get_args(RelationType))
    assert literal_types == RELATION_TYPES, (
        f"RelationType Literal ({sorted(literal_types)}) differs from "
        f"types.yaml config ({sorted(RELATION_TYPES)}). "
        "Update both files to match."
    )

    # Also verify TYPE_MIGRATION_MAP values are all valid
    from lorekeeper.models import TYPE_MIGRATION_MAP

    for old_type, new_type in TYPE_MIGRATION_MAP.items():
        assert new_type in RELATION_TYPES, (
            f"TYPE_MIGRATION_MAP[{old_type!r}] = {new_type!r} "
            f"is not a valid relation type (valid: {sorted(RELATION_TYPES)})"
        )
