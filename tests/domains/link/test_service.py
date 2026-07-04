"""LinkService integration tests.

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
    return build_app(store, engine, kw, settings), engine


def test_insert_link_between_memories(svc):
    service, _ = svc
    r = service.write_service.insert(
        memories=[
            {"title": "mem A", "description": "a", "content": "a"},
            {"title": "mem B", "description": "b", "content": "b"},
        ],
        links=[],
    )
    id_a = r["inserted_memories"][0]["id"]
    id_b = r["inserted_memories"][1]["id"]

    r2 = service.write_service.insert(
        memories=[],
        links=[{"source_memory_id": id_a, "target_memory_id": id_b,
                "relation_type": "references", "reason": "they relate"}],
    )
    assert len(r2["inserted_links"]) == 1
