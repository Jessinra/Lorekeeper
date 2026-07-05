"""
Handler layer tests.
Validates that input validation happens early — before reaching the orchestrator.
"""
from unittest.mock import patch

import pytest

from lorekeeper.api.mcp.handlers.memory_handlers import (
    handle_insert as _handle_insert,
)
from lorekeeper.api.mcp.handlers.memory_handlers import (
    handle_search as _handle_search,
)
from lorekeeper.api.mcp.handlers.suggestion_handlers import (
    handle_get_suggestions as _handle_get_suggestions,
)
from lorekeeper.api.mcp.handlers.suggestion_handlers import (
    handle_recommend_links as _handle_recommend_links,
)
from lorekeeper.api.mcp.handlers.suggestion_handlers import (
    handle_review_suggestion as _handle_review_suggestion,
)
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.processors.memory import MemoryProcessor
from lorekeeper.processors.suggestion import SuggestionProcessor
from tests._helpers import build_app, build_stores


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

    def find_vector_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None


@pytest.fixture
def stores(tmp_path):
    s = build_stores(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def svc(stores):
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_app(stores, engine, kw, settings)


@pytest.fixture
def memory_processor(svc, stores):
    return MemoryProcessor(
        search_service=svc.memory_search_service,
        write_service=svc.memory_write_service,
        import_service=svc.import_service,
        metrics=stores.metrics,
        db=stores.db,
        settings=Settings(),
    )


@pytest.fixture
def processor(svc, stores):
    return SuggestionProcessor(
        suggestion_service=svc.suggestion_service,
        suggestions=stores.suggestions,
        metrics=stores.metrics,
        db=stores.db,
    )


def test_handle_insert_missing_title_includes_index_in_message(svc, memory_processor):
    with pytest.raises(ValueError, match="memory at index 1"):
        _handle_insert(
            memory_processor,
            memories=[
                {"title": "valid memory", "content": "ok"},
                {"content": "missing title"},
            ],
            links=[],
        )


def test_handle_insert_valid_memory_succeeds(svc, memory_processor):
    result = _handle_insert(
        memory_processor,
        memories=[{"title": "test", "content": "some content"}],
        links=[],
    )
    assert len(result["inserted_memories"]) == 1
    assert result["errors"] == []


# ── MCP error paths ────────────────────────────────────────────────────────


def test_handle_insert_no_memories(svc, memory_processor):
    """Empty memories list should succeed with no inserted items."""
    result = _handle_insert(memory_processor, memories=[], links=[])
    assert result["inserted_memories"] == []
    assert result["errors"] == []


def test_handle_insert_invalid_inline_link_format(svc, memory_processor):
    """Inline links as a string (not list) should be caught and returned as error."""
    result = _handle_insert(
        memory_processor,
        memories=[{"title": "test", "links": "not-a-list"}],
        links=[],
    )
    assert len(result["errors"]) == 1
    assert "expected a list" in result["errors"][0]["error"]


def test_search_refine_from_exceeds_cap(svc, memory_processor):
    """refine_from with >200 IDs should raise ValueError at handler layer."""
    oversize = [str(i) for i in range(201)]
    with pytest.raises(ValueError, match="refine_from exceeds cap of 200 IDs"):
        _handle_search(memory_processor, "test", refine_from=oversize)


def test_search_refine_from_empty_is_noop(svc, memory_processor):
    """refine_from with an empty list should succeed (no filtering)."""
    svc.write_service.insert(
        memories=[{"title": "m1", "content": "one"}],
        links=[],
    )
    result = _handle_search(memory_processor, "test", refine_from=[])
    assert result["total_matched"] >= 0


# ── format=title tests ───────────────────────────────────────────────────────


def test_search_title_format_returns_compact_results(svc, memory_processor):
    """format='title' returns only id, title, score — no content or full memory."""
    svc.write_service.insert(
        memories=[{"title": "alpha", "content": "alpha content long enough to distinguish"},
                   {"title": "beta", "content": "beta content different topic"}],
        links=[],
    )
    # Configure fake engine to return memory IDs
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(memory_processor, "alpha", format="title")
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


def test_search_title_format_backward_compatible(svc, memory_processor):
    """Omitting format (default='full') returns full memory bodies as before."""
    svc.write_service.insert(
        memories=[{"title": "gamma", "content": "gamma content"}],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(memory_processor, "gamma")
    assert "results" in result
    for item in result["results"]:
        assert "memory" in item  # full serialization
        assert "relevance" in item


def test_search_title_format_with_empty_results(svc, memory_processor):
    """format='title' with no matches returns empty results."""
    result = _handle_search(memory_processor, "nonexistent_zzz", format="title")
    assert result["results"] == []


# ── ids param tests ──────────────────────────────────────────────────────────


def test_search_by_ids_returns_matching_memories(svc, memory_processor):
    """ids param returns full memories for the given IDs directly from SQL."""
    r = svc.write_service.insert(
        memories=[{"title": "mem one", "content": "content one"},
                   {"title": "mem two", "content": "content two"},
                   {"title": "mem three", "content": "content three"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    # Pick first two
    target_ids = ids[:2]

    result = _handle_search(memory_processor, "", ids=target_ids)
    assert len(result["results"]) == 2
    returned_ids = {item["memory"]["id"] for item in result["results"]}
    assert set(target_ids) == returned_ids


def test_search_by_ids_empty_list_returns_empty(svc, memory_processor):
    """Empty ids list returns no results."""
    result = _handle_search(memory_processor, "", ids=[])
    assert result["results"] == []


def test_search_by_ids_nonexistent_silently_ignored(svc, memory_processor):
    """Non-existent IDs in ids list are silently skipped."""
    result = _handle_search(memory_processor, "", ids=["nonexistent-id"])
    assert result["results"] == []


def test_search_by_ids_with_title_format(svc, memory_processor):
    """ids + format='title' returns compact results for specific IDs."""
    r = svc.write_service.insert(
        memories=[{"title": "pick me", "content": "content to pick"},
                   {"title": "not me", "content": "other content"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    target_id = ids[0]

    result = _handle_search(memory_processor, "", ids=[target_id], format="title")
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert item["id"] == target_id
    assert item["title"] == "pick me"
    assert "content" not in item
    assert "memory" not in item


# ── format validation ─────────────────────────────────────────────────────────


# ── ids cap ───────────────────────────────────────────────────────────────────


def test_search_by_ids_exceeds_cap_raises(svc, memory_processor):
    """ids with >50 IDs raises ValueError at handler layer."""
    oversize = [str(i) for i in range(51)]
    with pytest.raises(ValueError, match="ids exceeds cap of 50 IDs"):
        _handle_search(memory_processor, "query", ids=oversize)


# ── empty query guard ─────────────────────────────────────────────────────────


def test_search_empty_query_without_ids_raises(svc, memory_processor):
    """Empty query with no ids raises ValueError."""
    with pytest.raises(ValueError, match="query is required"):
        _handle_search(memory_processor, "")


def test_search_blank_query_without_ids_raises(svc, memory_processor):
    """Whitespace-only query with no ids raises ValueError."""
    with pytest.raises(ValueError, match="query is required"):
        _handle_search(memory_processor, "   ")


def test_search_empty_query_with_ids_succeeds(svc, memory_processor):
    """Empty query with ids is fine — ids path doesn't need a query."""
    result = _handle_search(memory_processor, "", ids=[])
    assert result["results"] == []


# ── include_links in ids path ─────────────────────────────────────────────────


def test_search_by_ids_include_links_fetches_actual_links(svc, memory_processor):
    """ids path with include_links=True fetches and returns actual links."""
    r = svc.write_service.insert(
        memories=[{"title": "src", "content": "source"},
                   {"title": "tgt", "content": "target"}],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    svc.links.insert_link(ids[0], ids[1], "references", "test link")

    result = _handle_search(memory_processor, "", ids=[ids[0]], include_links=True)
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert "links" in item
    assert len(item["links"]) == 1
    assert item["links"][0]["target_memory_id"] == ids[1]


# ── usage_count increment via ids path ────────────────────────────────────────


def test_search_by_ids_increments_usage_count(svc, memory_processor):
    """Bulk ID lookup increments usage_count on each returned memory."""
    r = svc.write_service.insert(
        memories=[{"title": "tracked", "content": "track me"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]

    before_row = svc.memories.get_memory_row(mem_id)
    before_count = before_row["usage_count"]

    _handle_search(memory_processor, "", ids=[mem_id])

    after_row = svc.memories.get_memory_row(mem_id)
    assert after_row["usage_count"] == before_count + 1


# ── dedup IDs in search_by_ids ───────────────────────────────────────────────


def test_search_by_ids_dedup_with_usage_count(svc, memory_processor):
    """Duplicate IDs in ids list should not cause extra usage_count bumps or duplicate results."""
    r = svc.write_service.insert(
        memories=[{"title": "dedup-me", "content": "test"}],
        links=[],
    )
    mem_id = r["inserted_memories"][0]["id"]

    before_row = svc.memories.get_memory_row(mem_id)
    before_count = before_row["usage_count"]

    result = _handle_search(memory_processor, "", ids=[mem_id, mem_id, mem_id])

    assert len(result["results"]) == 1  # no duplicates

    after_row = svc.memories.get_memory_row(mem_id)
    assert after_row["usage_count"] == before_count + 1  # bumped only once


# ── _handle_recommend_links input validation ──────────────────────────────────


def test_recommend_links_empty_lore_id_raises(processor):
    with pytest.raises(ValueError, match="lore_id is required"):
        _handle_recommend_links(processor, lore_id="")


def test_recommend_links_whitespace_lore_id_raises(processor):
    with pytest.raises(ValueError, match="lore_id is required"):
        _handle_recommend_links(processor, lore_id="   ")


def test_recommend_links_zero_top_k_raises(processor):
    with pytest.raises(ValueError, match="positive integer"):
        _handle_recommend_links(processor, lore_id="abc", top_k=0)


def test_recommend_links_negative_top_k_raises(processor):
    with pytest.raises(ValueError, match="positive integer"):
        _handle_recommend_links(processor, lore_id="abc", top_k=-5)


def test_recommend_links_top_k_capped_at_50(processor):
    """top_k > 50 must be silently capped — no error, result count <= 50."""
    with patch.object(
        processor._suggestion_service,
        'recommend_links',
        wraps=processor._suggestion_service.recommend_links,
    ) as mock_domain:
        result = _handle_recommend_links(processor, lore_id="nonexistent-id", top_k=999)
        # Verify the domain service received the capped value (spy catches the actual arg)
        mock_domain.assert_called_once_with(lore_id="nonexistent-id", top_k=50)
    # nonexistent lore_id returns empty candidates — just verify no exception and cap applied
    assert result["count"] == 0
    assert result["source_lore_id"] == "nonexistent-id"


def test_recommend_links_valid_call_returns_shape(processor):
    """Valid call must return dict with candidates, count, source_lore_id.

    Invariant: count must equal len(candidates).
    """
    result = _handle_recommend_links(processor, lore_id="some-id")
    assert "candidates" in result
    assert "count" in result
    assert "source_lore_id" in result
    # Invariant: count must always equal the actual number of candidates returned.
    assert result["count"] == len(result["candidates"])


# ── LKPR-61: created_after / updated_after validation tests ─────────────────


def test_created_after_invalid_iso_string_raises(svc, memory_processor):
    with pytest.raises(ValueError, match="Invalid ISO timestamp for 'created_after'"):
        _handle_search(memory_processor, "test", created_after="not-a-date")


def test_updated_after_invalid_iso_string_raises(svc, memory_processor):
    with pytest.raises(ValueError, match="Invalid ISO timestamp for 'updated_after'"):
        _handle_search(memory_processor, "test", updated_after="2026/06/01")


def test_created_after_non_utc_offset_raises(svc, memory_processor):
    with pytest.raises(ValueError, match="Non-UTC timezone offset"):
        _handle_search(memory_processor, "test", created_after="2026-06-01T00:00:00+05:30")


def test_created_after_utc_z_notation_accepted(svc, memory_processor):
    """Z suffix is UTC — should not raise."""
    result = _handle_search(memory_processor, "test", created_after="2026-06-01T00:00:00Z")
    assert "results" in result


def test_created_after_naive_string_treated_as_utc(svc, memory_processor):
    """Naive ISO strings (no tz) are treated as UTC — should not raise."""
    result = _handle_search(memory_processor, "test", created_after="2026-06-01T00:00:00")
    assert "results" in result


def test_created_after_plus_zero_utc_accepted(svc, memory_processor):
    """+00:00 offset is UTC — should not raise."""
    result = _handle_search(memory_processor, "test", created_after="2026-06-01T00:00:00+00:00")
    assert "results" in result


def test_created_after_filters_in_full_pipeline(svc, memory_processor):
    """Integration: created_after actually filters results end-to-end via handler."""
    r = svc.write_service.insert(
        memories=[
            {"title": "old mem", "content": "old content"},
            {"title": "new mem", "content": "new content"},
        ],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    old_id, new_id = ids[0], ids[1]

    # Backdate "old mem" to Jan 2026 and set "new mem" to June 2026 directly in DB.
    svc._conn.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ("2026-01-01T00:00:00+00:00", old_id),
    )
    svc._conn.execute(
        "UPDATE memories SET created_at = ? WHERE id = ?",
        ("2026-06-01T00:00:00+00:00", new_id),
    )
    svc._conn.commit()
    svc._invalidate_cache()

    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": row["id"], "score": 0.9} for row in all_rows]

    result = _handle_search(memory_processor, "content", created_after="2026-03-01T00:00:00")
    titles = {item["memory"]["title"] for item in result["results"]}
    assert "new mem" in titles
    assert "old mem" not in titles


# ── LKPR-80: sort_by validation tests ────────────────────────────────────────


def test_sort_by_unknown_value_raises(svc, memory_processor):
    with pytest.raises(ValueError, match="Unknown sort_by"):
        _handle_search(memory_processor, "test", sort_by="magic")


def test_sort_by_valid_values_do_not_raise(svc, memory_processor):
    """All three valid sort_by values must be accepted without error."""
    for valid in ("relevance", "recent", "frequent"):
        result = _handle_search(memory_processor, "test", sort_by=valid)
        assert "results" in result


def test_sort_by_recent_returns_results(svc, memory_processor):
    """sort_by='recent' round-trip via handler — at least returns valid shape."""
    svc.write_service.insert(
        memories=[{"title": "r1", "content": "content r1"},
                  {"title": "r2", "content": "content r2"}],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(memory_processor, "content r1", sort_by="recent")
    assert isinstance(result["results"], list)


def test_sort_by_frequent_returns_results(svc, memory_processor):
    """sort_by='frequent' round-trip via handler — at least returns valid shape."""
    svc.write_service.insert(
        memories=[{"title": "f1", "content": "content f1"}],
        links=[],
    )
    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": r["id"], "score": 0.9} for r in all_rows]
    result = _handle_search(memory_processor, "content f1", sort_by="frequent")
    assert isinstance(result["results"], list)


def test_sort_by_and_created_after_compose_in_handler(svc, memory_processor):
    """sort_by and created_after work together end-to-end."""
    r = svc.write_service.insert(
        memories=[
            {"title": "old entry", "content": "entry old"},
            {"title": "recent entry", "content": "entry recent"},
        ],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    old_id, new_id = ids[0], ids[1]

    svc._conn.execute(
        "UPDATE memories SET created_at = ?, updated_at = ? WHERE id = ?",
        ("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", old_id),
    )
    svc._conn.execute(
        "UPDATE memories SET created_at = ?, updated_at = ? WHERE id = ?",
        ("2026-06-01T00:00:00+00:00", "2026-06-15T00:00:00+00:00", new_id),
    )
    svc._conn.commit()
    svc._invalidate_cache()

    all_rows = svc.memories.all_memory_rows()
    svc._engine._search_results = [{"lore_id": row["id"], "score": 0.9} for row in all_rows]

    result = _handle_search(
        memory_processor, "entry",
        created_after="2026-03-01T00:00:00", sort_by="recent",
    )
    titles = [item["memory"]["title"] for item in result["results"]]
    assert "old entry" not in titles
    assert "recent entry" in titles


# ── LKPR-100: suggestion tool handler tests ───────────────────────────────────


class TestSuggestionHandlers:
    """Handler-level tests for lore_get_suggestions and lore_review_suggestion.

    Each test wires the handler helpers directly with a real stores.suggestions
    instance — no mocking of the store layer. This validates that:
      - input validation fires before any store access
      - the store is read/written correctly via the handler path
      - edge cases (already-accepted, already-rejected, not-found, batch) behave correctly
    """

    @pytest.fixture
    def suggestion_stores(self, tmp_path):
        return build_stores(tmp_path / "suggestions_test.db")

    @pytest.fixture
    def suggestion_svc(self, suggestion_stores):
        engine = FakeEngine()
        kw = KeywordIndex()
        settings = Settings()
        return build_app(suggestion_stores, engine, kw, settings)

    @pytest.fixture
    def suggestion_processor(self, suggestion_svc, suggestion_stores):
        return SuggestionProcessor(
            suggestion_service=suggestion_svc.suggestion_service,
            suggestions=suggestion_stores.suggestions,
            metrics=suggestion_stores.metrics,
            db=suggestion_stores.db,
        )

    def _insert_memory(self, stores, mem_id: str, title: str = "Memory") -> None:
        """Insert a minimal memory row so FK constraints on link_suggestions pass."""
        from datetime import UTC, datetime
        now = datetime.now(UTC).isoformat()
        stores.db.conn.execute(
            """INSERT OR IGNORE INTO memories
               (id, title, content, description, source_type, score, soft_deleted,
                usage_count, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (mem_id, title, "", "", "observed", 5.0, 0, 0, now, now),
        )
        stores.db.conn.commit()

    def _make_suggestion(self, stores, src_id="src-1", tgt_id="tgt-1",
                          score=0.8, suggested_type="references", status="pending"):
        self._insert_memory(stores, src_id, f"Source {src_id}")
        self._insert_memory(stores, tgt_id, f"Target {tgt_id}")
        return stores.suggestions.insert_suggestion(
            source_memory_id=src_id,
            target_memory_id=tgt_id,
            source_title="Source Memory",
            target_title="Target Memory",
            weighted_score=score,
            suggested_type=suggested_type,
            status=status,
        )

    # ── _handle_get_suggestions input validation ──────────────────────────────

    def test_get_suggestions_zero_limit_raises(self, suggestion_processor):
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _handle_get_suggestions(suggestion_processor, limit=0)

    def test_get_suggestions_negative_limit_raises(self, suggestion_processor):
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _handle_get_suggestions(suggestion_processor, limit=-1)

    def test_get_suggestions_bool_limit_raises(self, suggestion_processor):
        """bool is a subclass of int — True/False must be rejected."""
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            _handle_get_suggestions(suggestion_processor, limit=True)

    def test_get_suggestions_min_score_out_of_range_raises(
        self, suggestion_processor, suggestion_stores
    ):
        with pytest.raises(ValueError, match="min_score must be between"):
            _handle_get_suggestions(suggestion_processor, min_score=1.5)

    def test_get_suggestions_negative_min_score_raises(
        self, suggestion_processor, suggestion_stores
    ):
        with pytest.raises(ValueError, match="min_score must be between"):
            _handle_get_suggestions(suggestion_processor, min_score=-0.1)

    # ── _handle_get_suggestions happy path ───────────────────────────────────

    def test_get_suggestions_returns_pending_only(self, suggestion_processor, suggestion_stores):
        """Only status='pending' suggestions are returned."""
        self._make_suggestion(suggestion_stores, src_id="a", tgt_id="b", score=0.9)
        self._make_suggestion(
            suggestion_stores, src_id="c", tgt_id="d", score=0.7, status="accepted"
        )
        self._make_suggestion(
            suggestion_stores, src_id="e", tgt_id="f", score=0.5, status="rejected"
        )

        result = _handle_get_suggestions(suggestion_processor)
        assert result["count"] == 1
        assert result["total_pending"] == 1
        assert result["suggestions"][0]["source_memory_id"] == "a"

    def test_get_suggestions_empty_store_returns_empty(
        self, suggestion_processor, suggestion_stores
    ):
        result = _handle_get_suggestions(suggestion_processor)
        assert result["suggestions"] == []
        assert result["count"] == 0
        assert result["total_pending"] == 0

    def test_get_suggestions_limit_caps_results(self, suggestion_processor, suggestion_stores):
        for i in range(5):
            self._make_suggestion(
                suggestion_stores, src_id=f"s{i}", tgt_id=f"t{i}", score=0.5 + i * 0.1
            )
        result = _handle_get_suggestions(
            suggestion_processor, limit=3
        )
        assert result["count"] == 3
        assert result["total_pending"] == 5  # total not affected by limit

    def test_get_suggestions_min_score_filters(self, suggestion_processor, suggestion_stores):
        self._make_suggestion(suggestion_stores, src_id="hi", tgt_id="hi2", score=0.9)
        self._make_suggestion(suggestion_stores, src_id="lo", tgt_id="lo2", score=0.3)
        result = _handle_get_suggestions(
            suggestion_processor, min_score=0.5
        )
        assert result["count"] == 1
        assert result["suggestions"][0]["source_memory_id"] == "hi"

    def test_get_suggestions_response_shape(self, suggestion_processor, suggestion_stores):
        sug = self._make_suggestion(suggestion_stores)
        result = _handle_get_suggestions(suggestion_processor)
        assert "suggestions" in result
        assert "count" in result
        assert "total_pending" in result
        item = result["suggestions"][0]
        assert item["id"] == sug.id
        assert "source_memory_id" in item
        assert "target_memory_id" in item
        assert "weighted_score" in item
        assert "suggested_type" in item

    # ── _handle_review_suggestion input validation ────────────────────────────

    def test_review_empty_ids_raises(self, suggestion_processor, suggestion_stores):
        with pytest.raises(ValueError, match="suggestion_ids must not be empty"):
            _handle_review_suggestion(suggestion_processor,
                                       suggestion_ids=[], action="accept")

    def test_review_invalid_action_raises(self, suggestion_processor, suggestion_stores):
        with pytest.raises(ValueError, match="action must be 'accept' or 'reject'"):
            _handle_review_suggestion(suggestion_processor,
                                       suggestion_ids=["some-id"], action="approve")

    def test_review_whitespace_only_ids_raises(self, suggestion_processor, suggestion_stores):
        with pytest.raises(ValueError, match="suggestion_ids contained only empty strings"):
            _handle_review_suggestion(suggestion_processor,
                                       suggestion_ids=["   ", ""], action="accept")

    # ── _handle_review_suggestion accept path ────────────────────────────────

    def test_review_accept_creates_link(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        """Accepting a suggestion creates a real memory_links row."""
        sug = self._make_suggestion(suggestion_stores)
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )
        assert result["accepted"] == 1
        assert result["rejected"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == []
        assert result["results"][0]["status"] == "accepted"
        link_id = result["results"][0]["link_id"]
        assert link_id is not None
        link = suggestion_svc.links.get_link(link_id)
        assert link is not None
        assert link.source_memory_id == sug.source_memory_id
        assert link.target_memory_id == sug.target_memory_id

    def test_review_accept_updates_suggestion_status(self, suggestion_processor, suggestion_stores):
        sug = self._make_suggestion(suggestion_stores)
        _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )
        updated = suggestion_stores.suggestions.get_suggestion(sug.id)
        assert updated.status == "accepted"

    def test_review_accept_idempotent_on_already_accepted(
        self, suggestion_processor, suggestion_stores
    ):
        """Double-accept returns skipped, not an error."""
        sug = self._make_suggestion(suggestion_stores, status="accepted")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )
        assert result["skipped"] == 1
        assert result["accepted"] == 0
        assert result["results"][0]["message"] == "Already accepted"

    def test_review_accept_unknown_id_skipped(self, suggestion_processor, suggestion_stores):
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=["nonexistent-uuid"], action="accept",
        )
        assert result["skipped"] == 1
        assert result["results"][0]["message"] == "Suggestion not found"

    def test_review_accept_fallback_relation_type_for_invalid(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        """Suggestions with unrecognised suggested_type fall back to 'references'."""
        sug = self._make_suggestion(suggestion_stores, suggested_type="UNKNOWN_TYPE")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )
        assert result["accepted"] == 1
        link = suggestion_svc.links.get_link(result["results"][0]["link_id"])
        assert link.relation_type == "references"

    # ── _handle_review_suggestion reject path ────────────────────────────────

    def test_review_reject_updates_suggestion_status(self, suggestion_processor, suggestion_stores):
        sug = self._make_suggestion(suggestion_stores)
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="reject",
        )
        assert result["rejected"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == []
        updated = suggestion_stores.suggestions.get_suggestion(sug.id)
        assert updated.status == "rejected"

    def test_review_reject_does_not_create_link(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        sug = self._make_suggestion(suggestion_stores)
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="reject",
        )
        assert result["results"][0]["link_id"] is None
        assert suggestion_svc.links.all_links() == []

    def test_review_reject_idempotent_on_already_rejected(
        self, suggestion_processor, suggestion_stores
    ):
        sug = self._make_suggestion(suggestion_stores, status="rejected")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="reject",
        )
        assert result["skipped"] == 1
        assert result["results"][0]["message"] == "Already rejected"

    def test_review_reject_on_accepted_is_skipped(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        """Rejecting an already-accepted suggestion must be skipped, not overwrite status."""
        sug = self._make_suggestion(suggestion_stores, status="accepted")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="reject",
        )
        assert result["skipped"] == 1
        assert result["rejected"] == 0
        assert "accepted" in result["results"][0]["message"].lower()
        # Status must remain accepted — not flipped to rejected
        updated = suggestion_stores.suggestions.get_suggestion(sug.id)
        assert updated.status == "accepted"

    def test_review_reject_unknown_id_skipped(self, suggestion_processor, suggestion_stores):
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=["does-not-exist"], action="reject",
        )
        assert result["skipped"] == 1

    # ── batch behaviour ───────────────────────────────────────────────────────

    def test_review_batch_accept_multiple(self, suggestion_processor, suggestion_stores):
        """Batch accept processes all items in one call."""
        s1 = self._make_suggestion(suggestion_stores, src_id="a1", tgt_id="a2")
        s2 = self._make_suggestion(suggestion_stores, src_id="b1", tgt_id="b2")
        s3 = self._make_suggestion(suggestion_stores, src_id="c1", tgt_id="c2")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[s1.id, s2.id, s3.id], action="accept",
        )
        assert result["accepted"] == 3
        assert result["skipped"] == 0
        assert result["errors"] == []
        assert len(result["results"]) == 3

    def test_review_batch_mixed_accept_reject_independent(
        self, suggestion_processor, suggestion_stores
    ):
        """Batch with mixed valid/invalid IDs — each processed independently."""
        s1 = self._make_suggestion(suggestion_stores, src_id="x1", tgt_id="x2")
        s2 = self._make_suggestion(suggestion_stores, src_id="y1", tgt_id="y2", status="accepted")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[s1.id, s2.id, "nonexistent-id"], action="accept",
        )
        assert result["accepted"] == 1
        assert result["skipped"] == 2  # s2 already accepted + nonexistent
        assert result["errors"] == []

    def test_review_accept_on_rejected_creates_link(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        """Edge case from plan: accept a previously-rejected suggestion creates a link."""
        sug = self._make_suggestion(suggestion_stores, status="rejected")
        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )
        assert result["accepted"] == 1
        assert result["results"][0]["link_id"] is not None

    # ── LKPR-104 Phase 6b: accept_one atomicity ──────────────────────────────

    def test_review_accept_rolls_back_link_if_status_update_fails(
        self, suggestion_svc, suggestion_processor, suggestion_stores
    ):
        """If update_suggestion_status fails after insert_link succeeds, the
        link insert must be rolled back too — accept_one's Database.transaction()
        SAVEPOINT must cover both steps atomically, not just log-and-continue.
        """
        sug = self._make_suggestion(suggestion_stores)

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated status update failure")

        suggestion_stores.suggestions.update_suggestion_status = _boom

        result = _handle_review_suggestion(
            suggestion_processor,
            suggestion_ids=[sug.id], action="accept",
        )

        assert result["accepted"] == 0
        assert result["errors"][0]["id"] == sug.id
        assert "simulated status update failure" in result["errors"][0]["error"]

        # The link must NOT exist — insert_link's write should have been
        # rolled back by the same SAVEPOINT that failed on the status update.
        assert suggestion_svc.links.all_links() == []
        # Suggestion status must remain pending — not left half-accepted.
        stored = suggestion_stores.db.conn.execute(
            "SELECT status FROM link_suggestions WHERE id = ?", (sug.id,)
        ).fetchone()
        assert stored["status"] == "pending"
