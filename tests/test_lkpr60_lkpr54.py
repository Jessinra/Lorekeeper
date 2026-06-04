"""
Tests for LKPR-60 (_all_memories cache) and LKPR-54 (lore_forget).
"""
import pytest

from lorekeeper.config import Settings
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


# ── LKPR-60: memory cache ─────────────────────────────────────────────────────


def test_cache_initially_none(svc):
    assert svc._memory_cache is None


def test_cache_populated_after_all_memories_call(svc):
    svc.insert(memories=[{"title": "alpha", "content": "content a"}], links=[])
    _ = svc._all_memories()
    assert svc._memory_cache is not None


def test_cache_invalidated_by_rebuild_kw(svc):
    svc.insert(memories=[{"title": "beta", "content": "content b"}], links=[])
    _ = svc._all_memories()
    assert svc._memory_cache is not None
    svc._rebuild_kw()
    # _rebuild_kw invalidates then re-populates the cache; cache is non-None after
    assert svc._memory_cache is not None


def test_cache_returns_consistent_data(svc):
    svc.insert(memories=[{"title": "gamma", "content": "content g"}], links=[])
    first = svc._all_memories()
    second = svc._all_memories()
    assert first.keys() == second.keys()


def test_include_deleted_false_filters_soft_deleted(svc):
    result = svc.insert(memories=[{"title": "to-delete", "content": "bye"}], links=[])
    mid = result["inserted_memories"][0]["id"]

    # Soft-delete via update
    svc.update(
        memory_feedback=[{"id": mid, "useful": False, "confidence": 1}],
        link_feedback=[],
    )

    # Manually force soft_deleted=1 (confidence threshold might not trigger)
    svc.memories.update_memory_fields(mid, soft_deleted=1)
    svc._invalidate_cache()

    visible = svc._all_memories(include_deleted=False)
    assert mid not in visible

    all_mems = svc._all_memories(include_deleted=True)
    assert mid in all_mems


# ── LKPR-54: lore_forget ──────────────────────────────────────────────────────


def test_forget_soft_deletes_memory(svc):
    result = svc.insert(memories=[{"title": "stale fact", "content": "old"}], links=[])
    mid = result["inserted_memories"][0]["id"]

    out = svc.forget([mid], reason="outdated")
    assert mid in out["forgotten"]
    assert out["not_found"] == []
    assert out["errors"] == []

    visible = svc._all_memories(include_deleted=False)
    assert mid not in visible


def test_forget_multiple_ids(svc):
    r1 = svc.insert(memories=[{"title": "m1", "content": "c1"}], links=[])
    r2 = svc.insert(memories=[{"title": "m2", "content": "c2"}], links=[])
    mid1 = r1["inserted_memories"][0]["id"]
    mid2 = r2["inserted_memories"][0]["id"]

    out = svc.forget([mid1, mid2], reason="duplicate")
    assert set(out["forgotten"]) == {mid1, mid2}


def test_forget_unknown_id_goes_to_not_found(svc):
    out = svc.forget(["00000000-0000-0000-0000-000000000000"])
    assert "00000000-0000-0000-0000-000000000000" in out["not_found"]
    assert out["forgotten"] == []


def test_handle_forget_empty_ids_raises(svc):
    with pytest.raises(ValueError, match="memory_ids must not be empty"):
        svc.forget(memory_ids=[])


def test_handle_forget_invalid_reason_raises(svc):
    result = svc.insert(memories=[{"title": "x", "content": "y"}], links=[])
    mid = result["inserted_memories"][0]["id"]
    with pytest.raises(ValueError, match="Unknown reason"):
        svc.forget(memory_ids=[mid], reason="oops")


def test_forget_invalidates_cache(svc):
    result = svc.insert(memories=[{"title": "cached", "content": "data"}], links=[])
    mid = result["inserted_memories"][0]["id"]

    # Warm the cache
    _ = svc._all_memories()
    assert svc._memory_cache is not None

    svc.forget([mid], reason="outdated")

    # After forget, cache was rebuilt (non-None but not stale)
    visible = svc._all_memories(include_deleted=False)
    assert mid not in visible


def test_forgotten_memory_excluded_from_search(svc):
    result = svc.insert(memories=[{"title": "ephemeral", "content": "temporary fact"}], links=[])
    mid = result["inserted_memories"][0]["id"]

    svc.forget([mid], reason="expired")

    search_result = svc.search(query="ephemeral temporary", include_deleted=False)
    found_ids = [r.id for r in search_result]
    assert mid not in found_ids
