"""
Handler layer tests.
Validates that input validation happens early — before reaching the orchestrator.
"""
import pytest

from lorekeeper.config import Settings
from lorekeeper.server import _handle_insert, _handle_search
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


def test_handle_insert_missing_title_raises_at_handler_layer(svc):
    with pytest.raises(ValueError, match="missing required field: 'title'"):
        _handle_insert(svc, memories=[{"content": "no title here"}], links=[])


def test_handle_insert_missing_title_includes_index_in_message(svc):
    with pytest.raises(ValueError, match="memory at index 1"):
        _handle_insert(
            svc,
            memories=[
                {"title": "valid memory", "content": "ok"},
                {"content": "missing title"},
            ],
            links=[],
        )


def test_handle_insert_valid_memory_succeeds(svc):
    result = _handle_insert(
        svc,
        memories=[{"title": "test", "content": "some content"}],
        links=[],
    )
    assert len(result["inserted_memories"]) == 1
    assert result["errors"] == []


# ── MCP error paths ────────────────────────────────────────────────────────


def test_handle_insert_no_memories(svc):
    """Empty memories list should succeed with no inserted items."""
    result = _handle_insert(svc, memories=[], links=[])
    assert result["inserted_memories"] == []
    assert result["errors"] == []


def test_handle_insert_invalid_inline_link_format(svc):
    """Inline links as a string (not list) should be caught and returned as error."""
    result = _handle_insert(
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
        _handle_search(svc, "test", refine_from=oversize)


def test_search_refine_from_empty_is_noop(svc):
    """refine_from with an empty list should succeed (no filtering)."""
    svc.insert(
        memories=[{"title": "m1", "content": "one"}],
        links=[],
    )
    result = _handle_search(svc, "test", refine_from=[])
    assert result["total_matched"] >= 0


# ── format=title tests ───────────────────────────────────────────────────────


def test_search_title_format_returns_compact_results(svc):
    """format='title' returns only id, title, score — no content or full memory."""
    svc.insert(
        memories=[{"title": "alpha", "content": "alpha content long enough to distinguish"},
                   {"title": "beta", "content": "beta content different topic"}],
        links=[],
    )
    # Configure fake engine to return memory IDs
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(svc, "alpha", format="title")
    assert "results" in result
    assert len(result["results"]) >= 1
    for item in result["results"]:
        # Title mode has id, title, score — flat dict
        assert "id" in item
        assert "title" in item
        assert "score" in item
        assert "content" not in item
        assert "memory" not in item
        assert "relevance" not in item


def test_search_title_format_backward_compatible(svc):
    """Omitting format (default='full') returns full memory bodies as before."""
    svc.insert(
        memories=[{"title": "gamma", "content": "gamma content"}],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(svc, "gamma")
    assert "results" in result
    for item in result["results"]:
        assert "memory" in item  # full serialization
        assert "relevance" in item


def test_search_title_format_with_empty_results(svc):
    """format='title' with no matches returns empty results."""
    result = _handle_search(svc, "nonexistent_zzz", format="title")
    assert result["results"] == []


# ── ids param tests ──────────────────────────────────────────────────────────


def test_search_by_ids_returns_matching_memories(svc):
    """ids param returns full memories for the given IDs directly from SQL."""
    r = svc.insert(
        memories=[{"title": "mem one", "content": "content one"},
                   {"title": "mem two", "content": "content two"},
                   {"title": "mem three", "content": "content three"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    # Pick first two
    target_ids = ids[:2]

    result = _handle_search(svc, "", ids=target_ids)
    assert len(result["results"]) == 2
    returned_ids = {item["memory"]["id"] for item in result["results"]}
    assert set(target_ids) == returned_ids


def test_search_by_ids_empty_list_returns_empty(svc):
    """Empty ids list returns no results."""
    result = _handle_search(svc, "", ids=[])
    assert result["results"] == []


def test_search_by_ids_nonexistent_silently_ignored(svc):
    """Non-existent IDs in ids list are silently skipped."""
    result = _handle_search(svc, "", ids=["nonexistent-id"])
    assert result["results"] == []


def test_search_by_ids_with_title_format(svc):
    """ids + format='title' returns compact results for specific IDs."""
    r = svc.insert(
        memories=[{"title": "pick me", "content": "content to pick"},
                   {"title": "not me", "content": "other content"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    target_id = ids[0]

    result = _handle_search(svc, "", ids=[target_id], format="title")
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert item["id"] == target_id
    assert item["title"] == "pick me"
    assert "content" not in item
    assert "memory" not in item


# ── format validation ─────────────────────────────────────────────────────────


def test_search_invalid_format_raises():
    """Invalid format value raises ValueError before any db access."""
    from unittest.mock import MagicMock

    fake_svc = MagicMock()
    with pytest.raises(ValueError, match="Unknown format"):
        _handle_search(fake_svc, "query", format="xml")


# ── ids cap ───────────────────────────────────────────────────────────────────


def test_search_by_ids_exceeds_cap_raises(svc):
    """ids with >50 IDs raises ValueError at handler layer."""
    oversize = [str(i) for i in range(51)]
    with pytest.raises(ValueError, match="ids exceeds cap of 50 IDs"):
        _handle_search(svc, "query", ids=oversize)


# ── empty query guard ─────────────────────────────────────────────────────────


def test_search_empty_query_without_ids_raises(svc):
    """Empty query with no ids raises ValueError."""
    with pytest.raises(ValueError, match="query is required"):
        _handle_search(svc, "")


def test_search_blank_query_without_ids_raises(svc):
    """Whitespace-only query with no ids raises ValueError."""
    with pytest.raises(ValueError, match="query is required"):
        _handle_search(svc, "   ")


def test_search_empty_query_with_ids_succeeds(svc):
    """Empty query with ids is fine — ids path doesn't need a query."""
    result = _handle_search(svc, "", ids=[])
    assert result["results"] == []


# ── include_links in ids path ─────────────────────────────────────────────────


def test_search_by_ids_include_links_fetches_actual_links(svc):
    """ids path with include_links=True fetches and returns actual links."""
    r = svc.insert(
        memories=[{"title": "src", "content": "source"},
                   {"title": "tgt", "content": "target"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    svc.links.insert_link(ids[0], ids[1], "related_to", "test link")

    result = _handle_search(svc, "", ids=[ids[0]], include_links=True)
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert "links" in item
    assert len(item["links"]) == 1
    assert item["links"][0]["target_memory_id"] == ids[1]


# ── usage_count increment via ids path ────────────────────────────────────────


def test_search_by_ids_increments_usage_count(svc):
    """Bulk ID lookup increments usage_count on each returned memory."""
    r = svc.insert(
        memories=[{"title": "tracked", "content": "track me"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]

    before_row = svc.memories.get_memory_row(mem_id)
    before_count = before_row["usage_count"]

    _handle_search(svc, "", ids=[mem_id])

    after_row = svc.memories.get_memory_row(mem_id)
    assert after_row["usage_count"] == before_count + 1


# ── dedup IDs in search_by_ids ───────────────────────────────────────────────


def test_search_by_ids_dedup_with_usage_count(svc):
    """Duplicate IDs in ids list should not cause extra usage_count bumps or duplicate results."""
    r = svc.insert(
        memories=[{"title": "dedup-me", "content": "test"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]

    before_row = svc.memories.get_memory_row(mem_id)
    before_count = before_row["usage_count"]

    result = _handle_search(svc, "", ids=[mem_id, mem_id, mem_id])

    assert len(result["results"]) == 1  # no duplicates

    after_row = svc.memories.get_memory_row(mem_id)
    assert after_row["usage_count"] == before_count + 1  # bumped only once
