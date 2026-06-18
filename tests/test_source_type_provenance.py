"""
LKPR-18 — source_type provenance tagging tests.

Covers:
  - source_type persisted on lore_insert (default + explicit)
  - source_type emitted in serialized search results
  - source_type filter in lore_search (query path + ids path)
  - invalid source_type raises ValueError at the server layer
  - migration 3 backfills pre-existing rows as 'unknown'
"""
import sqlite3

import pytest

from lorekeeper.config import Settings
from lorekeeper.models import SOURCE_TYPES, WRITE_SOURCE_TYPES
from lorekeeper.server import _handle_insert, _handle_search
from lorekeeper.services.database import _migration_3_add_source_type
from lorekeeper.services.keyword_index import KeywordIndex
from tests._helpers import build_service, build_stores


class FakeEngine:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._search_results: list[dict] = []

    def probe_score_scale(self) -> None:
        pass

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
        self._store[lore_id] = text
        return lore_id

    def search(self, query: str, limit: int = 200) -> list[dict]:
        return self._search_results[:limit]

    def get_all(self) -> list[dict]:
        return [{"lore_id": k, "mem0_id": k} for k in self._store]

    def normalize_score(self, raw: float) -> float:
        return raw

    def find_mem0_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None


@pytest.fixture
def svc(tmp_path):
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_service(store, engine, kw, settings)


# ── Default source_type on insert ────────────────────────────────────────────


def test_insert_default_source_type_is_observed(svc):
    """lore_insert without source_type should store 'observed'."""
    r = _handle_insert(
        svc,
        memories=[{"title": "default source", "content": "no source_type given"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]
    row = svc.memories.get_memory_row(mem_id)
    assert row["source_type"] == "observed"


def test_insert_explicit_source_type_persisted(svc):
    """Write-time source_type set explicitly in memory dict must be stored as-is."""
    for st in WRITE_SOURCE_TYPES:
        r = _handle_insert(
            svc,
            memories=[{"title": f"typed-{st}", "content": "content", "source_type": st}],
            links=[],
        )
        mem_id = r["inserted_memories"][0]["id"]
        row = svc.memories.get_memory_row(mem_id)
        assert row["source_type"] == st, f"Expected {st!r}, got {row['source_type']!r}"


# ── source_type in serialised output ─────────────────────────────────────────


def test_search_result_contains_source_type_field(svc):
    """Full-format search result must include source_type in the memory dict."""
    r = svc.insert(
        memories=[{"title": "emit-st", "content": "emit source type test"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]
    result = _handle_search(svc, "", ids=[mem_id])
    assert len(result["results"]) == 1
    mem = result["results"][0]["memory"]
    assert "source_type" in mem


def test_search_result_source_type_matches_stored_value(svc):
    """source_type in serialized result must match what was stored."""
    r = _handle_insert(
        svc,
        memories=[{
            "title": "user-stated-mem",
            "content": "told by user",
            "source_type": "user_stated",
        }],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]
    result = _handle_search(svc, "", ids=[mem_id])
    mem = result["results"][0]["memory"]
    assert mem["source_type"] == "user_stated"


# ── source_type filter — query path ──────────────────────────────────────────


def test_source_type_filter_returns_only_matching(svc):
    """source_type filter on query path must exclude non-matching memories."""
    _handle_insert(
        svc,
        memories=[
            {"title": "obs-mem", "content": "observation content", "source_type": "observed"},
            {"title": "inf-mem", "content": "inferred content", "source_type": "inferred"},
        ],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": row["id"], "score": 0.9} for row in all_rows]

    result = _handle_search(svc, "content", source_type="inferred")
    titles = {item["memory"]["title"] for item in result["results"]}
    assert "inf-mem" in titles
    assert "obs-mem" not in titles


def test_source_type_filter_no_matches_returns_empty(svc):
    """source_type filter with no matching memories returns empty results."""
    _handle_insert(
        svc,
        memories=[{"title": "just-obs", "content": "only observed", "source_type": "observed"}],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": row["id"], "score": 0.9} for row in all_rows]

    result = _handle_search(svc, "observed", source_type="consolidated")
    assert result["results"] == []


# ── source_type filter — ids path ─────────────────────────────────────────────


def test_source_type_filter_in_ids_path(svc):
    """ids path with source_type filter must exclude non-matching memories."""
    r = _handle_insert(
        svc,
        memories=[
            {"title": "ids-obs", "content": "ids observed", "source_type": "observed"},
            {"title": "ids-inj", "content": "ids injected", "source_type": "injected"},
        ],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]

    result = _handle_search(svc, "", ids=ids, source_type="injected")
    titles = {item["memory"]["title"] for item in result["results"]}
    assert "ids-inj" in titles
    assert "ids-obs" not in titles


# ── invalid source_type raises at handler layer ───────────────────────────────


def test_search_invalid_source_type_raises_value_error(svc):
    """Invalid source_type must raise ValueError at the handler layer."""
    with pytest.raises(ValueError, match="Unknown source_type"):
        _handle_search(svc, "test", source_type="made_up")


def test_search_valid_source_types_do_not_raise(svc):
    """All valid SOURCE_TYPES must be accepted by _handle_search without error."""
    for st in SOURCE_TYPES:
        # No exception — empty results are fine
        result = _handle_search(svc, "test", source_type=st)
        assert "results" in result


def test_insert_invalid_source_type_raises_value_error(svc):
    """Invalid source_type in lore_insert memory dict must raise ValueError at the handler layer."""
    with pytest.raises(ValueError, match="invalid source_type"):
        _handle_insert(
            svc,
            memories=[{"title": "bad-type", "content": "test", "source_type": "totally_made_up"}],
            links=[],
        )


def test_insert_unknown_source_type_is_rejected(svc):
    """'unknown' source_type must be rejected on insert — it is reserved for migration backfill."""
    with pytest.raises(ValueError, match="invalid source_type"):
        _handle_insert(
            svc,
            memories=[{"title": "unknown-type", "content": "test", "source_type": "unknown"}],
            links=[],
        )


def test_insert_valid_source_types_do_not_raise(svc):
    """All write-time WRITE_SOURCE_TYPES must be accepted by _handle_insert without error.

    'unknown' is excluded — it is reserved for migration backfill and must NOT be
    accepted on new inserts.
    """
    for st in WRITE_SOURCE_TYPES:
        result = _handle_insert(
            svc,
            memories=[{"title": f"valid-{st}", "content": "test", "source_type": st}],
            links=[],
        )
        assert result["inserted_memories"][0]["id"]


# ── migration backfill test ───────────────────────────────────────────────────


def test_migration_3_backfills_existing_rows_as_unknown(tmp_path):
    """Migration 3 must add source_type='unknown' to rows inserted before migration."""
    db_path = tmp_path / "pre_migration.db"

    # Build the DB at schema version 2 (without source_type column).
    # We do this by connecting directly, running migrations 1+2 manually,
    # then inserting a row — before migration 3 touches it.
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Bootstrap schema (migration 1 subset — just memories table without source_type)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version VALUES (0);

        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            description TEXT,
            score REAL NOT NULL DEFAULT 5.0,
            soft_deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            last_used TEXT,
            usage_count INTEGER NOT NULL DEFAULT 0,
            tags TEXT,
            metadata TEXT
        );
    """)

    # Insert a row without source_type (simulates pre-migration data)
    conn.execute(
        "INSERT INTO memories (id, title, content) VALUES (?, ?, ?)",
        ("pre-mig-id", "pre-migration memory", "some content"),
    )
    conn.commit()

    # Run migration 3
    _migration_3_add_source_type(conn)
    conn.commit()

    # Verify the column exists and the backfilled row has 'unknown'
    row = conn.execute("SELECT source_type FROM memories WHERE id = 'pre-mig-id'").fetchone()
    assert row is not None
    assert row["source_type"] == "unknown"
    conn.close()


def test_migration_3_is_idempotent(tmp_path):
    """Running migration 3 twice must not raise an error."""
    db_path = tmp_path / "idempotent.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL
        );
    """)
    conn.commit()

    # Run twice — should not raise
    _migration_3_add_source_type(conn)
    _migration_3_add_source_type(conn)
    conn.commit()
    conn.close()


def test_new_rows_get_observed_not_unknown(svc):
    """Rows written via the service after migration must default to 'observed', not 'unknown'."""
    r = _handle_insert(
        svc,
        memories=[{"title": "post-mig", "content": "inserted normally"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]
    row = svc.memories.get_memory_row(mem_id)
    assert row["source_type"] == "observed"
    assert row["source_type"] != "unknown"
