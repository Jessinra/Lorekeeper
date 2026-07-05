"""MemorySearchService integration tests.

Relocated from tests/test_orchestrator.py (Step 6 of LKPR-105).
Uses real SQLite (via build_stores) and a FakeEngine.
"""
import pytest

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from tests._helpers import FakeEngine, build_app, build_stores


@pytest.fixture
def svc(tmp_path):
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    yield build_app(store, engine, kw, settings), engine
    store.close()


def test_search_excludes_soft_deleted(svc):
    service, engine = svc
    r = service.write_service.insert(
        memories=[{"title": "deleted mem", "description": "d", "content": "c"}],
        links=[],
    )
    mid = r["inserted_memories"][0]["id"]
    service.memory_processor.forget(memory_ids=[mid], reason="outdated")

    engine._search_results = [{"lore_id": mid, "score": 0.9}]
    results = service.search("deleted", include_deleted=False)
    assert len(results) == 0

    results = service.search("deleted", include_deleted=True)
    assert len(results) == 1


def _make_svc(tmp_path, db_name: str, namespace: str):
    """Helper: create an App with a given namespace."""
    store = build_stores(tmp_path / db_name)
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings(namespace=namespace)
    return build_app(store, engine, kw, settings), store


def test_agent_reads_own_and_shared(tmp_path):
    """Diana agent should see diana + shared memories, not bella's."""
    # Seed the DB directly with memories from multiple namespaces
    store = build_stores(tmp_path / "multi.db")
    try:
        store.memories.upsert_memory_row(id="a", title="diana mem", description="d", content="c",
                                created_at="2026-01-01T00:00:00+00:00",
                                updated_at="2026-01-01T00:00:00+00:00",
                                namespace="diana")
        store.memories.upsert_memory_row(id="b", title="shared mem", description="d", content="c",
                                created_at="2026-01-01T00:00:00+00:00",
                                updated_at="2026-01-01T00:00:00+00:00",
                                namespace="shared")
        store.memories.upsert_memory_row(id="c", title="bella mem", description="d", content="c",
                                created_at="2026-01-01T00:00:00+00:00",
                                updated_at="2026-01-01T00:00:00+00:00",
                                namespace="bella")

        engine = FakeEngine()
        kw = KeywordIndex()
        settings = Settings(namespace="diana")
        svc = build_app(store, engine, kw, settings)

        memories = svc.cache.all_memories()
        ids = set(memories.keys())
        assert "a" in ids   # own namespace
        assert "b" in ids   # shared
        assert "c" not in ids  # bella's — invisible
    finally:
        store.close()


def test_no_namespace_sees_all(tmp_path):
    """With namespace='shared' (default), _all_memories returns all rows."""
    store = build_stores(tmp_path / "all.db")
    try:
        store.memories.upsert_memory_row(id="a", title="t1", description="d", content="c",
                                created_at="2026-01-01T00:00:00+00:00",
                                updated_at="2026-01-01T00:00:00+00:00",
                                namespace="diana")
        store.memories.upsert_memory_row(id="b", title="t2", description="d", content="c",
                                created_at="2026-01-01T00:00:00+00:00",
                                updated_at="2026-01-01T00:00:00+00:00",
                                namespace="shared")

        engine = FakeEngine()
        kw = KeywordIndex()
        settings = Settings(namespace="shared")
        svc = build_app(store, engine, kw, settings)

        memories = svc.cache.all_memories()
        assert len(memories) == 2  # sees all
    finally:
        store.close()


# ── LKPR-80: sort_by crash-guard on ids-path ─────────────────────────────────


def test_ids_sort_by_recent_malformed_updated_at_does_not_crash(svc):
    """ids-path sort_by='recent' must not raise on a malformed updated_at.

    Offending row should sort last.
    """
    service, _engine = svc

    # Insert two memories with known updated_at
    r = service.write_service.insert([
        {"title": "good memory", "content": "c", "description": "d"},
        {"title": "bad timestamp memory", "content": "c", "description": "d"},
    ], links=[])
    ids_inserted = [m["id"] for m in r["inserted_memories"]]

    # Patch one memory's updated_at to a malformed value directly in the DB.
    bad_id = ids_inserted[1]
    service.db.conn.execute(
        "UPDATE memories SET updated_at = 'NOT-A-DATE' WHERE id = ?", (bad_id,)
    )
    service.db.conn.commit()

    # This must not raise despite the bad timestamp.
    results = service.search_service.search_by_ids(ids=ids_inserted, sort_by="recent")
    result_ids = [r.memory.id for r in results]

    # Both returned — no crash.
    assert len(result_ids) == 2
    # The bad-timestamp memory should sort last (datetime.min fallback).
    assert result_ids.index(ids_inserted[0]) < result_ids.index(bad_id)
