"""Tests for MemoryCache — in-process memory row cache + BM25 rebuild coupling."""

from __future__ import annotations

from lorekeeper.domains.memory.cache import MemoryCache
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex


def _insert_memory(memories: MemoryStore, id: str, title: str,
                   soft_deleted: bool = False) -> None:
    """Insert a minimal memory row into the store."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    memories._conn.execute(
        """INSERT OR IGNORE INTO memories
           (id, title, description, content, created_at, updated_at,
            soft_deleted, source_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (id, title, "desc", "content", now, now,
         1 if soft_deleted else 0, "observed"),
    )
    memories._conn.commit()


def _count_rows(memories: MemoryStore) -> int:
    """Count total memory rows (including soft_deleted)."""
    return memories._conn.execute(
        "SELECT COUNT(*) FROM memories"
    ).fetchone()[0]


def test_cache_starts_dirty(tmp_path):
    """Cache starts with None — first call populates from DB."""
    db = Database(tmp_path / "test.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    # Cache is dirty — no rows yet
    _insert_memory(mems, "mem-1", "Test Memory")
    result = cache.all_memories()
    assert len(result) == 1
    assert "mem-1" in result


def test_cache_second_call_no_reload(tmp_path):
    """Second call to all_memories returns cached data without re-query."""
    db = Database(tmp_path / "test2.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    _insert_memory(mems, "mem-1", "Test Memory")
    cache.all_memories()  # populate cache

    # Insert another row — should NOT appear in cache until invalidated
    _insert_memory(mems, "mem-2", "Test Memory 2")
    result = cache.all_memories()
    assert "mem-2" not in result  # cache hit — still has old data
    assert len(result) == 1


def test_invalidate_reloads(tmp_path):
    """Invalidate marks cache dirty; next call reloads from DB."""
    db = Database(tmp_path / "test3.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    _insert_memory(mems, "mem-1", "First")
    cache.all_memories()  # populate
    _insert_memory(mems, "mem-2", "Second")

    cache.invalidate()
    result = cache.all_memories()
    assert len(result) == 2
    assert "mem-2" in result


def test_include_deleted_filters(tmp_path):
    """include_deleted=False filters out soft-deleted memories."""
    db = Database(tmp_path / "test4.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    _insert_memory(mems, "mem-1", "Active")
    _insert_memory(mems, "mem-2", "Deleted", soft_deleted=True)

    all_mems = cache.all_memories(include_deleted=True)
    assert len(all_mems) == 2

    active = cache.all_memories(include_deleted=False)
    assert len(active) == 1
    assert "mem-2" not in active


def test_rebuild_kw_invalidates_and_rebuilds(tmp_path):
    """rebuild_kw() invalidates cache and rebuilds keyword index.

    BM25 IDF formula: log((N - df + 0.5) / (df + 0.5)).
    With 3 documents, a term in 1 doc has df=1, N=3, so IDF = log(2.5/1.5) > 0.
    """
    db = Database(tmp_path / "test5.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    _insert_memory(mems, "mem-1", "Alpha Memory Special")
    _insert_memory(mems, "mem-2", "Beta Memory Special")
    _insert_memory(mems, "mem-3", "Gamma Unique Topic")

    # rebuild should populate cache + BM25
    cache.rebuild_kw()
    result = cache.all_memories()
    assert len(result) == 3
    assert "mem-1" in result

    # BM25 search should work after rebuild
    # "Alpha" appears in 1 of 3 docs -> IDF > 0
    hits = kw.search_normalized("Alpha")
    assert "mem-1" in hits
    assert hits["mem-1"] > 0


def test_include_deleted_true_returns_dict_copy(tmp_path):
    """include_deleted=True returns a copy, not the internal cache dict."""
    db = Database(tmp_path / "test6.db")
    db.migrate()
    mems = MemoryStore(db)
    kw = KeywordIndex()
    cache = MemoryCache(mems, kw, None)

    _insert_memory(mems, "mem-1", "Test")
    result = cache.all_memories(include_deleted=True)
    # Mutating the returned dict should not affect the cache
    result.pop("mem-1", None)

    # Cache still has the entry
    result2 = cache.all_memories(include_deleted=True)
    assert "mem-1" in result2
