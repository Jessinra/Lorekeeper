"""
Orchestrator integration tests.
Uses real SQLite (via LinkStore) and a fake MemoryEngine.
"""
import pytest

from lorekeeper.config import Settings
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.orchestrator import MemoryService


class FakeEngine:
    """Minimal stub: stores text by lore_id, returns configurable search results."""

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
    store = LinkStore(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return MemoryService(engine, store, kw, settings), engine


def test_insert_and_search(svc):
    service, engine = svc
    result = service.insert(
        memories=[{
            "title": "checkout flow",
            "description": "how checkout works",
            "content": "steps...",
        }],
        links=[],
    )
    assert len(result["inserted_memories"]) == 1
    mem_id = result["inserted_memories"][0]["id"]

    # Point fake engine to return this memory on search
    engine._search_results = [{"lore_id": mem_id, "score": 0.9}]
    results = service.search("checkout", limit=5)
    assert len(results) == 1
    assert results[0].memory.title == "checkout flow"


def test_update_bumps_score(svc):
    service, _engine = svc
    result = service.insert(
        memories=[{"title": "test memory", "description": "d", "content": "c"}],
        links=[],
    )
    mid = result["inserted_memories"][0]["id"]
    row_before = service._store.get_memory_row(mid)

    service.update(memory_feedback=[{"id": mid, "useful": True}], link_feedback=[])
    row_after = service._store.get_memory_row(mid)

    assert row_after["score"] > row_before["score"]


def test_soft_delete_on_low_confidence_not_useful(svc):
    service, _ = svc
    result = service.insert(
        memories=[{"title": "bad memory", "description": "d", "content": "c"}],
        links=[],
    )
    mid = result["inserted_memories"][0]["id"]

    update_result = service.update(
        memory_feedback=[{"id": mid, "useful": False, "confidence": 1}],
        link_feedback=[],
    )
    assert update_result["soft_deleted_memories"] == 1
    row = service._store.get_memory_row(mid)
    assert row["soft_deleted"] == 1


def test_insert_link_between_memories(svc):
    service, _ = svc
    r = service.insert(
        memories=[
            {"title": "mem A", "description": "a", "content": "a"},
            {"title": "mem B", "description": "b", "content": "b"},
        ],
        links=[],
    )
    id_a = r["inserted_memories"][0]["id"]
    id_b = r["inserted_memories"][1]["id"]

    r2 = service.insert(
        memories=[],
        links=[{"source_memory_id": id_a, "target_memory_id": id_b,
                "relation_type": "related_to", "reason": "they relate"}],
    )
    assert len(r2["inserted_links"]) == 1


def test_search_excludes_soft_deleted(svc):
    service, engine = svc
    r = service.insert(
        memories=[{"title": "deleted mem", "description": "d", "content": "c"}],
        links=[],
    )
    mid = r["inserted_memories"][0]["id"]
    service._store.update_memory_fields(mid, soft_deleted=1)

    engine._search_results = [{"lore_id": mid, "score": 0.9}]
    results = service.search("deleted", include_deleted=False)
    assert len(results) == 0

    results = service.search("deleted", include_deleted=True)
    assert len(results) == 1
