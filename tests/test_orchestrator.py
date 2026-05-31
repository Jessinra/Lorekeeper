"""
Orchestrator integration tests.
Uses real SQLite (via the focused stores from build_stores()) and a fake MemoryEngine.
"""
import pytest

from lorekeeper.config import Settings
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.orchestrator import MemoryService
from tests._helpers import build_service, build_stores


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
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_service(store, engine, kw, settings), engine


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
    row_before = service.memories.get_memory_row(mid)

    service.update(memory_feedback=[{"id": mid, "useful": True}], link_feedback=[])
    row_after = service.memories.get_memory_row(mid)

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
    row = service.memories.get_memory_row(mid)
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


def test_submit_reflection_first_call_succeeds(svc):
    """First lore_reflect call for a session should store a reflection and return reflection_id."""
    service, _ = svc
    result = service.submit_reflection(
        session_id="session-abc",
        session_date="2026-05-23",
        topic="test topic",
        task_type="build",
        what_was_done="built stuff",
        decisions="went with approach A",
        lessons_learnt=["lesson 1"],
        good_patterns=["pattern 1"],
        user_profile_updates=[],
        factual_discoveries=[],
        summary="Test session summary",
        memory_ids=[],
    )
    assert result["session_id"] == "session-abc"
    assert "reflection_id" in result
    assert result.get("already_processed") is None


def test_submit_reflection_duplicate_returns_noop(svc):
    """Calling lore_reflect on an already-processed session must return idempotent no-op."""
    service, _ = svc
    first = service.submit_reflection(
        session_id="session-dup",
        session_date="2026-05-23",
        topic="topic",
        task_type="build",
        what_was_done="did things",
        decisions="decided",
        lessons_learnt=[],
        good_patterns=[],
        user_profile_updates=[],
        factual_discoveries=[],
        summary="Summary",
        memory_ids=[],
    )
    # Second call with same session_id
    second = service.submit_reflection(
        session_id="session-dup",
        session_date="2026-05-24",
        topic="different topic",
        task_type="review",
        what_was_done="other work",
        decisions="new decision",
        lessons_learnt=["new lesson"],
        good_patterns=[],
        user_profile_updates=[],
        factual_discoveries=[],
        summary="Different summary",
        memory_ids=[],
    )
    assert second["already_processed"] is True
    assert second["reflection_id"] == first["reflection_id"]
    assert second["session_id"] == "session-dup"


def test_submit_reflection_duplicate_does_not_create_extra_reflection_row(svc):
    """Duplicate lore_reflect must not insert additional reflection rows."""
    service, _ = svc
    session_id = "session-no-dup-row"
    for _ in range(3):
        service.submit_reflection(
            session_id=session_id,
            session_date="2026-05-23",
            topic="topic",
            task_type="build",
            what_was_done="work",
            decisions="decision",
            lessons_learnt=[],
            good_patterns=[],
            user_profile_updates=[],
            factual_discoveries=[],
            summary="Summary",
            memory_ids=[],
        )
    # Only one reflection row should exist for this session
    reflections = service.reflections.all_reflections()
    session_row = service.reflections.get_session(session_id)
    matching = [r for r in reflections if r["id"] == session_row["reflection_id"]]
    assert len(matching) == 1
    assert len(reflections) == 1  # only one reflection total in this test DB


def test_search_excludes_soft_deleted(svc):
    service, engine = svc
    r = service.insert(
        memories=[{"title": "deleted mem", "description": "d", "content": "c"}],
        links=[],
    )
    mid = r["inserted_memories"][0]["id"]
    service.memories.update_memory_fields(mid, soft_deleted=1)

    engine._search_results = [{"lore_id": mid, "score": 0.9}]
    results = service.search("deleted", include_deleted=False)
    assert len(results) == 0

    results = service.search("deleted", include_deleted=True)
    assert len(results) == 1


def test_insert_one_memory_missing_title_raises_clear_error(svc):
    service, _ = svc
    result = service.insert(
        memories=[{"content": "no title here", "score": 8}],
        links=[],
    )
    assert result["inserted_memories"] == []
    assert len(result["errors"]) == 1
    error_msg = result["errors"][0]["error"]
    # Should be a descriptive message, not the bare KeyError repr ("'title'")
    assert error_msg != "'title'"
    assert "missing required field" in error_msg
    assert "title" in error_msg


# ── lore_remember tests ────────────────────────────────────────────────────────


def test_extract_title_short_thought():
    thought = "Checkout flow: three-step process"
    assert MemoryService._extract_title(thought) == thought


def test_extract_title_sentence_boundary():
    thought = (
        "Hybrid search formula: 0.45 semantic + 0.30 keyword + 0.15 score "
        "+ 0.10 usage. This is the core ranking algorithm used across all lore_search calls."
    )
    title = MemoryService._extract_title(thought)
    assert title.endswith("usage.")
    assert len(title) <= 80


def test_extract_title_no_boundary_breaks_at_word():
    # Long single sentence with no punctuation in first 80 chars
    thought = (
        "This is a very long sentence that goes on and on without any punctuation "
        "at all and just keeps running past the eighty character limit"
    )
    title = MemoryService._extract_title(thought)
    assert len(title) <= 80
    # Should end at a word boundary (not mid-word like "charact")
    assert title[-1] != "e"  # "sentence" ends with 'e' — verify it didn't slice mid-word


def test_new_memory_default_score_is_five(svc):
    service, _engine = svc
    result = service.remember("test thought")
    row = service.memories.get_memory_row(result["id"])
    assert row["score"] == 5.0


def test_remember_stores_full_content(svc):
    service, _ = svc
    thought = "Project checkout uses GAS framework and SPEX protocol."
    result = service.remember(thought)
    row = service.memories.get_memory_row(result["id"])
    assert row["content"] == thought


def test_remember_returns_none_linked_to_when_no_neighbor(svc):
    service, engine = svc
    engine._search_results = []  # no results from Chroma
    result = service.remember("lone thought")
    assert result["linked_to"] is None


def test_remember_auto_link_when_neighbor_above_threshold(svc):
    service, engine = svc
    # First, insert a seed memory
    seed = service.insert(
        memories=[{"title": "seed", "description": "s", "content": "seed content about checkout"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Point fake engine to return the seed with high similarity
    engine._search_results = [
        {"lore_id": seed_id, "score": 0.85},
        {"lore_id": "some-other", "score": 0.5},
    ]

    result = service.remember("related thought about checkout")
    assert result["linked_to"] is not None
    assert result["linked_to"]["id"] == seed_id
    assert result["linked_to"]["score"] == 0.85


def test_remember_no_auto_link_below_threshold(svc):
    service, engine = svc
    seed = service.insert(
        memories=[{"title": "seed", "description": "s", "content": "seed"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    engine._search_results = [{"lore_id": seed_id, "score": 0.74}]
    result = service.remember("unrelated thought")
    assert result["linked_to"] is None


def test_remember_detects_duplicate_title(svc):
    service, _ = svc
    thought = "Checkout flow: three steps"
    first = service.remember(thought)
    second = service.remember(thought)
    assert second["id"] == first["id"]
    assert second["linked_to"] is None


def test_remember_auto_link_skips_self_match(svc):
    service, engine = svc
    engine._search_results = []  # Chroma doesn't return self (or returns self only)
    result = service.remember("self-contained thought")
    assert result["linked_to"] is None


# ── Inline links on lore_insert ─────────────────────────────────────────────


def test_insert_with_inline_links(svc):
    """Insert a memory with inline links — both memory and links are created."""
    service, _ = svc

    # First, create a target memory to link to
    target_result = service.insert(
        memories=[{"title": "target mem", "description": "t", "content": "target"}],
        links=[],
    )
    target_id = target_result["inserted_memories"][0]["id"]

    # Insert a new memory with inline link to target
    result = service.insert(
        memories=[{
            "title": "source mem",
            "description": "s",
            "content": "source",
            "links": [{
                "target_memory_id": target_id,
                "relation_type": "related_to",
                "reason": "they are connected",
            }],
        }],
        links=[],
    )

    assert len(result["inserted_memories"]) == 1
    assert result["duplicates"] == []
    assert len(result["errors"]) == 0
    source_id = result["inserted_memories"][0]["id"]

    # Verify link was created
    links = service.links.links_for_memory(source_id)
    assert len(links) == 1
    assert links[0].target_memory_id == target_id
    assert links[0].relation_type == "related_to"
    assert links[0].reason == "they are connected"


def test_insert_inline_link_invalid_target(svc):
    """Invalid target in inline link returns error but memory is still inserted."""
    service, _ = svc

    result = service.insert(
        memories=[{
            "title": "orphan mem",
            "description": "o",
            "content": "orphan",
            "links": [{
                "target_memory_id": "nonexistent-id",
                "relation_type": "related_to",
            }],
        }],
        links=[],
    )

    # Memory should be inserted
    assert len(result["inserted_memories"]) == 1
    assert result["duplicates"] == []

    # Link error should be reported
    assert len(result["errors"]) == 1
    assert "nonexistent-id" in result["errors"][0]["error"]
    assert "not found" in result["errors"][0]["error"]


def test_insert_inline_link_invalid_relation(svc):
    """Invalid relation type in inline link returns error but memory is still inserted."""
    service, _ = svc

    # Create a target first
    target_result = service.insert(
        memories=[{"title": "target for bad relation", "description": "t", "content": "t"}],
        links=[],
    )
    target_id = target_result["inserted_memories"][0]["id"]

    result = service.insert(
        memories=[{
            "title": "mem with bad relation link",
            "description": "b",
            "content": "bad",
            "links": [{
                "target_memory_id": target_id,
                "relation_type": "invalid_relation",
            }],
        }],
        links=[],
    )

    # Memory should be inserted
    assert len(result["inserted_memories"]) == 1
    assert result["duplicates"] == []

    # Link error should be reported
    assert len(result["errors"]) == 1
    assert "invalid_relation" in result["errors"][0]["error"]
    assert "invalid relation_type" in result["errors"][0]["error"]

def test_insert_inline_links_invalid_format_string_not_list(svc):
    """Inline links that is a string (not list) raises an error."""
    service, _ = svc

    result = service.insert(
        memories=[{
            "title": "bad links format",
            "description": "b",
            "content": "bad format",
            "links": "this should be a list",
        }],
        links=[],
    )

    assert len(result["inserted_memories"]) == 0
    assert len(result["errors"]) == 1
    assert "expected a list" in result["errors"][0]["error"]


def test_insert_inline_link_missing_target_memory_id(svc):
    """Inline link without target_memory_id fails fast — memory is not inserted."""
    service, _ = svc

    result = service.insert(
        memories=[{
            "title": "mem with incomplete link",
            "description": "m",
            "content": "missing target_memory_id",
            "links": [{
                "relation_type": "related_to",
            }],
        }],
        links=[],
    )

    # Pre-insert validation catches this before the memory is created
    assert len(result["inserted_memories"]) == 0
    assert len(result["errors"]) == 1
    assert "target_memory_id" in result["errors"][0]["error"]


def test_insert_inline_link_missing_relation_type(svc):
    """Inline link without relation_type fails fast — memory is not inserted."""
    service, _ = svc

    result = service.insert(
        memories=[{
            "title": "mem with incomplete link",
            "description": "m",
            "content": "missing relation_type",
            "links": [{
                "target_memory_id": "some-id",
            }],
        }],
        links=[],
    )

    # Pre-insert validation catches this before the memory is created
    assert len(result["inserted_memories"]) == 0
    assert len(result["errors"]) == 1
    assert "relation_type" in result["errors"][0]["error"]


# ── Auto-link on insert ────────────────────────────────────────────────────


def test_insert_auto_link_creates_link(svc):
    """Insert calls auto-link — a link is created when a similar memory exists."""
    service, engine = svc

    # Seed a memory
    seed = service.insert(
        memories=[{"title": "checkout", "description": "", "content": "checkout flow details"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Point engine to treat any new content as similar to seed
    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]

    # Insert a new memory — should auto-link to seed
    result = service.insert(
        memories=[{
            "title": "payment",
            "description": "",
            "content": "payment processing in checkout",
        }],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 1
    assert links[0].target_memory_id == seed_id
    assert "auto-linked from lore_insert" in links[0].reason


def test_insert_auto_link_respects_disabled(svc):
    """When auto_link_enabled=False, insert should not auto-link."""
    service, engine = svc
    service.settings.auto_link_enabled = False

    seed = service.insert(
        memories=[{"title": "checkout", "description": "", "content": "checkout"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]

    result = service.insert(
        memories=[{"title": "payment", "description": "", "content": "payment"}],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 0


def test_insert_auto_link_respects_threshold(svc):
    """Auto-link should not create links below the configured threshold."""
    service, engine = svc

    seed = service.insert(
        memories=[{"title": "seed", "description": "", "content": "seed content"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Score below default threshold of 0.85
    engine._search_results = [{"lore_id": seed_id, "score": 0.70}]

    result = service.insert(
        memories=[{"title": "new", "description": "", "content": "new content"}],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 0


def test_auto_link_duplicate_guard(svc):
    """Auto-link should skip candidates already linked to avoid duplicate links."""
    service, engine = svc

    seed = service.insert(
        memories=[{"title": "seed", "description": "", "content": "seed content"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # First insert — auto-links A→seed
    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]
    result = service.insert(
        memories=[{"title": "mem A", "description": "", "content": "related content"}],
        links=[],
    )
    mem_a_id = result["inserted_memories"][0]["id"]
    assert len(service.links.links_for_memory(mem_a_id)) == 1

    # Call _auto_link directly with the same lore_id — should skip because
    # mem_a already has a link to seed
    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]
    linked = service._auto_link("related content", mem_a_id, source="insert")
    assert linked is None  # skipped by duplicate guard

    # Still only 1 link from mem_a to seed
    assert len(service.links.links_for_memory(mem_a_id)) == 1


def test_auto_link_uses_settings_k(svc):
    """_auto_link searches with settings.auto_link_k candidates, not hardcoded 2."""
    service, engine = svc
    service.settings.auto_link_k = 10

    seed = service.insert(
        memories=[{"title": "seed", "description": "", "content": "seed"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # If engine is called with limit=10, the first 2 results are below threshold
    # but the 10th is a 0.95 match
    hits = [{"lore_id": f"noise-{i}", "score": 0.5} for i in range(9)]
    hits.append({"lore_id": seed_id, "score": 0.95})
    engine._search_results = hits

    result = service.insert(
        memories=[{"title": "test", "description": "", "content": "test content"}],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 1
    assert links[0].target_memory_id == seed_id


def test_insert_with_inline_links_and_top_level_links(svc):
    """Both inline links (per memory) and top-level links work together."""
    service, _ = svc

    # Create target memories
    r1 = service.insert(
        memories=[
            {"title": "target A", "description": "a", "content": "a"},
            {"title": "target B", "description": "b", "content": "b"},
            {"title": "target C", "description": "c", "content": "c"},
        ],
        links=[],
    )
    id_a = r1["inserted_memories"][0]["id"]
    id_b = r1["inserted_memories"][1]["id"]
    id_c = r1["inserted_memories"][2]["id"]

    # Insert with both inline links and top-level links
    result = service.insert(
        memories=[{
            "title": "source with inline link",
            "description": "s",
            "content": "source",
            "links": [{
                "target_memory_id": id_a,
                "relation_type": "used_in",
                "reason": "inline link",
            }],
        }],
        links=[{
            "source_memory_id": id_b,
            "target_memory_id": id_c,
            "relation_type": "related_to",
            "reason": "top-level link between targets",
        }],
    )

    assert len(result["inserted_memories"]) == 1
    assert len(result["inserted_links"]) >= 1  # at least the inline link
    assert len(result["errors"]) == 0
    source_id = result["inserted_memories"][0]["id"]

    # Verify inline link
    source_links = service.links.links_for_memory(source_id)
    assert len(source_links) >= 1
    assert source_links[0].source_memory_id == source_id
    assert source_links[0].target_memory_id == id_a

    # Verify top-level link
    b_links = service.links.links_for_memory(id_b)
    has_c_link = any(lnk.target_memory_id == id_c for lnk in b_links)
    assert has_c_link


# ── Namespace isolation tests ──────────────────────────────────────────────────

def _make_svc(tmp_path, db_name: str, namespace: str):
    """Helper: create a MemoryService with a given namespace."""
    store = build_stores(tmp_path / db_name)
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings(namespace=namespace)
    return build_service(store, engine, kw, settings), store


def test_insert_tags_with_agent_namespace(tmp_path):
    svc, store = _make_svc(tmp_path, "ns.db", "diana")
    svc.insert(memories=[{"title": "diana memory", "content": "c", "description": "d"}], links=[])
    rows = store.memories.all_memory_rows()
    assert len(rows) == 1
    assert rows[0]["namespace"] == "diana"


def test_insert_tags_with_shared_when_no_namespace(tmp_path):
    svc, store = _make_svc(tmp_path, "ns.db", "shared")
    svc.insert(memories=[{"title": "shared memory", "content": "c", "description": "d"}], links=[])
    rows = store.memories.all_memory_rows()
    assert rows[0]["namespace"] == "shared"


def test_agent_reads_own_and_shared(tmp_path):
    """Diana agent should see diana + shared memories, not bella's."""
    # Seed the DB directly with memories from multiple namespaces
    store = build_stores(tmp_path / "multi.db")
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
    svc = build_service(store, engine, kw, settings)

    memories = svc._all_memories()
    ids = set(memories.keys())
    assert "a" in ids   # own namespace
    assert "b" in ids   # shared
    assert "c" not in ids  # bella's — invisible


def test_no_namespace_sees_all(tmp_path):
    """With namespace='shared' (default), _all_memories returns all rows."""
    store = build_stores(tmp_path / "all.db")
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
    svc = build_service(store, engine, kw, settings)

    memories = svc._all_memories()
    assert len(memories) == 2  # sees all


def test_same_title_different_namespace_not_duplicate(tmp_path):
    """Two agents in different namespaces can use the same title without false duplicate."""
    diana_svc, _ = _make_svc(tmp_path, "dup.db", "diana")
    bella_svc, _ = _make_svc(tmp_path, "dup.db", "bella")

    # Insert same title in different namespaces
    diana_res = diana_svc.insert(
        memories=[{"title": "common title", "content": "diana's", "description": "d"}],
        links=[],
    )
    diana_id = diana_res["inserted_memories"][0]["id"]

    bella_res = bella_svc.insert(
        memories=[{"title": "common title", "content": "bella's", "description": "d"}],
        links=[],
    )
    bella_id = bella_res["inserted_memories"][0]["id"]

    # Both should succeed with different IDs
    assert diana_id != bella_id


def test_same_title_same_namespace_still_detects_duplicate(tmp_path):
    """Same title in same namespace still triggers duplicate detection."""
    svc, _ = _make_svc(tmp_path, "dup2.db", "diana")

    first = svc.insert(
        memories=[{"title": "my memory", "content": "first", "description": "d"}],
        links=[],
    )
    first_id = first["inserted_memories"][0]["id"]

    second = svc.insert(
        memories=[{"title": "my memory", "content": "second", "description": "d"}],
        links=[],
    )
    assert len(second["duplicates"]) == 1
    assert second["duplicates"][0]["existing_memory"]["id"] == first_id


def test_same_title_in_shared_still_detects_duplicate(tmp_path):
    """Memory with namespace='shared' is visible as duplicate to any agent."""
    store = build_stores(tmp_path / "dup3.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    store.memories.upsert_memory_row(id="shared-id", title="overlap", description="d", content="c",
                            created_at="2026-01-01T00:00:00+00:00",
                            updated_at="2026-01-01T00:00:00+00:00",
                            namespace="shared")

    diana_svc = build_service(store, engine, kw, Settings(namespace="diana"))
    result = diana_svc.insert(
        memories=[{"title": "overlap", "content": "new", "description": "d"}],
        links=[],
    )
    assert len(result["duplicates"]) == 1
    assert result["duplicates"][0]["existing_memory"]["id"] == "shared-id"


def test_shared_agent_deduplicates_against_all_namespaces(tmp_path):
    """Regression: shared agent's insert duplicate check spans all namespaces.

    A memory seeded in a non-shared namespace must still be detected as a
    duplicate when the shared agent tries to insert the same title. Without
    this, the shared agent could re-insert titles that already exist in
    profile namespaces and later surface duplicates to every reader.
    """
    store = build_stores(tmp_path / "shared_dedup.db")
    engine = FakeEngine()
    kw = KeywordIndex()

    # Seed a memory in "diana" namespace directly (bypassing the service)
    store.memories.upsert_memory_row(
        id="diana-mem-1",
        title="cross-ns title",
        description="original in diana ns",
        content="content",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="diana",
    )

    # Shared agent should detect it as a duplicate (namespaces=None → global scan)
    shared_svc = build_service(store, engine, kw, Settings(namespace="shared"))
    result = shared_svc.insert(
        memories=[{"title": "cross-ns title", "content": "new", "description": "d"}],
        links=[],
    )
    assert len(result["duplicates"]) == 1, (
        "Shared agent must detect duplicates from all namespaces"
    )
    assert result["duplicates"][0]["existing_memory"]["id"] == "diana-mem-1"
