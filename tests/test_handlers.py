"""
Handler layer tests.
Validates that input validation happens early — before reaching the orchestrator.
"""
import pytest

from lorekeeper.config import Settings
from lorekeeper.handlers import handle_insert, handle_search
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore  # noqa: F401  # legacy import
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


def test_handle_insert_missing_title_raises_at_handler_layer(svc):
    with pytest.raises(ValueError, match="missing required field: 'title'"):
        handle_insert(svc, memories=[{"content": "no title here"}], links=[])


def test_handle_insert_missing_title_includes_index_in_message(svc):
    with pytest.raises(ValueError, match="memory at index 1"):
        handle_insert(
            svc,
            memories=[
                {"title": "valid memory", "content": "ok"},
                {"content": "missing title"},
            ],
            links=[],
        )


def test_handle_insert_valid_memory_succeeds(svc):
    result = handle_insert(
        svc,
        memories=[{"title": "test", "content": "some content"}],
        links=[],
    )
    assert len(result["inserted_memories"]) == 1
    assert result["errors"] == []


# ── MCP error paths ────────────────────────────────────────────────────────


def test_handle_insert_no_memories(svc):
    """Empty memories list should succeed with no inserted items."""
    result = handle_insert(svc, memories=[], links=[])
    assert result["inserted_memories"] == []
    assert result["errors"] == []


def test_handle_insert_invalid_inline_link_format(svc):
    """Inline links as a string (not list) should be caught and returned as error."""
    result = handle_insert(
        svc,
        memories=[{"title": "test", "links": "not-a-list"}],
        links=[],
    )
    assert len(result["errors"]) == 1
    assert "expected a list" in result["errors"][0]["error"]


def test_search_refine_from_exceeds_cap(svc):
    """refine_from with >200 IDs should raise ValueError at handler layer."""
    oversize = [str(i) for i in range(201)]
    with pytest.raises(ValueError, match="refine_from exceeds cap of 200 IDs"):
        handle_search(svc, "test", refine_from=oversize)


def test_search_refine_from_empty_is_noop(svc):
    """refine_from with an empty list should succeed (no filtering)."""
    svc.insert(
        memories=[{"title": "m1", "content": "one"}],
        links=[],
    )
    result = handle_search(svc, "test", refine_from=[])
    assert result["total_matched"] >= 0
