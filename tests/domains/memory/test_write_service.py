"""MemoryWriteService integration tests.

Relocated from tests/test_orchestrator.py (Step 6 of LKPR-105).
Uses real SQLite (via build_stores) and a FakeEngine.
"""
import pytest

from lorekeeper.domains.memory.service import extract_title
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


def test_insert_and_search(svc):
    service, engine = svc
    result = service.write_service.insert(
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
    result = service.write_service.insert(
        memories=[{"title": "test memory", "description": "d", "content": "c"}],
        links=[],
    )
    mid = result["inserted_memories"][0]["id"]
    row_before = service.memories.get_memory_row(mid)

    service.memory_processor.update(memory_feedback=[{"id": mid, "useful": True}], link_feedback=[])
    row_after = service.memories.get_memory_row(mid)

    assert row_after["score"] > row_before["score"]


def test_soft_delete_on_low_confidence_not_useful(svc):
    service, _ = svc
    result = service.write_service.insert(
        memories=[{"title": "bad memory", "description": "d", "content": "c"}],
        links=[],
    )
    mid = result["inserted_memories"][0]["id"]

    update_result = service.memory_processor.update(
        memory_feedback=[{"id": mid, "useful": False, "confidence": 1}],
        link_feedback=[],
    )
    assert update_result["soft_deleted_memories"] == 1
    row = service.memories.get_memory_row(mid)
    assert row["soft_deleted"] == 1


def test_insert_one_memory_missing_title_raises_clear_error(svc):
    service, _ = svc
    result = service.write_service.insert(
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
    assert extract_title(thought) == thought


def test_extract_title_sentence_boundary():
    thought = (
        "Hybrid search formula: 0.45 semantic + 0.30 keyword + 0.15 score "
        "+ 0.10 usage. This is the core ranking algorithm used across all lore_search calls."
    )
    title = extract_title(thought)
    assert title.endswith("usage.")
    assert len(title) <= 80


def test_extract_title_no_boundary_breaks_at_word():
    # Long single sentence with no punctuation in first 80 chars
    thought = (
        "This is a very long sentence that goes on and on without any punctuation "
        "at all and just keeps running past the eighty character limit"
    )
    title = extract_title(thought)
    assert len(title) <= 80
    # Should end at a word boundary (not mid-word like "charact")
    assert title[-1] != "e"  # "sentence" ends with 'e' — verify it didn't slice mid-word


def test_new_memory_default_score_is_five(svc):
    service, _engine = svc
    result = service.memory_processor.remember("test thought")
    row = service.memories.get_memory_row(result["id"])
    assert row["score"] == 5.0


def test_remember_stores_full_content(svc):
    service, _ = svc
    thought = "Project checkout uses GAS framework and SPEX protocol."
    result = service.memory_processor.remember(thought)
    row = service.memories.get_memory_row(result["id"])
    assert row["content"] == thought


def test_remember_returns_none_linked_to_when_no_neighbor(svc):
    service, engine = svc
    engine._search_results = []  # no results from Chroma
    result = service.memory_processor.remember("lone thought")
    assert result["linked_to"] is None


def test_remember_auto_link_when_neighbor_above_threshold(svc):
    service, engine = svc
    # First, insert a seed memory
    seed = service.write_service.insert(
        memories=[{"title": "seed", "description": "s", "content": "seed content about checkout"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Point fake engine to return the seed with high similarity
    engine._search_results = [
        {"lore_id": seed_id, "score": 0.85},
        {"lore_id": "some-other", "score": 0.5},
    ]

    result = service.memory_processor.remember("related thought about checkout")
    assert result["linked_to"] is not None
    assert result["linked_to"]["id"] == seed_id
    assert result["linked_to"]["score"] == 0.85


def test_remember_no_auto_link_below_threshold(svc):
    service, engine = svc
    seed = service.write_service.insert(
        memories=[{"title": "seed", "description": "s", "content": "seed"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    engine._search_results = [{"lore_id": seed_id, "score": 0.74}]
    result = service.memory_processor.remember("unrelated thought")
    assert result["linked_to"] is None


def test_remember_detects_duplicate_title(svc):
    service, _ = svc
    thought = "Checkout flow: three steps"
    first = service.memory_processor.remember(thought)
    second = service.memory_processor.remember(thought)
    assert second["id"] == first["id"]
    assert second["linked_to"] is None


def test_remember_auto_link_skips_self_match(svc):
    service, engine = svc
    engine._search_results = []  # Chroma doesn't return self (or returns self only)
    result = service.memory_processor.remember("self-contained thought")
    assert result["linked_to"] is None


# ── Inline links on lore_insert ─────────────────────────────────────────────


def test_insert_with_inline_links(svc):
    """Insert a memory with inline links — both memory and links are created."""
    service, _ = svc

    # First, create a target memory to link to
    target_result = service.write_service.insert(
        memories=[{"title": "target mem", "description": "t", "content": "target"}],
        links=[],
    )
    target_id = target_result["inserted_memories"][0]["id"]

    # Insert a new memory with inline link to target
    result = service.write_service.insert(
        memories=[{
            "title": "source mem",
            "description": "s",
            "content": "source",
            "links": [{
                "target_memory_id": target_id,
                "relation_type": "references",
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
    assert links[0].relation_type == "references"
    assert links[0].reason == "they are connected"


def test_insert_inline_link_invalid_target(svc):
    """Invalid target in inline link returns error but memory is still inserted."""
    service, _ = svc

    result = service.write_service.insert(
        memories=[{
            "title": "orphan mem",
            "description": "o",
            "content": "orphan",
            "links": [{
                "target_memory_id": "nonexistent-id",
                "relation_type": "references",
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
    target_result = service.write_service.insert(
        memories=[{"title": "target for bad relation", "description": "t", "content": "t"}],
        links=[],
    )
    target_id = target_result["inserted_memories"][0]["id"]

    result = service.write_service.insert(
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

    result = service.write_service.insert(
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

    result = service.write_service.insert(
        memories=[{
            "title": "mem with incomplete link",
            "description": "m",
            "content": "missing target_memory_id",
            "links": [{
                "relation_type": "references",
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

    result = service.write_service.insert(
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
    seed = service.write_service.insert(
        memories=[{"title": "checkout", "description": "", "content": "checkout flow details"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Point engine to treat any new content as similar to seed
    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]

    # Insert a new memory — should auto-link to seed
    result = service.write_service.insert(
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

    seed = service.write_service.insert(
        memories=[{"title": "checkout", "description": "", "content": "checkout"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    engine._search_results = [{"lore_id": seed_id, "score": 0.90}]

    result = service.write_service.insert(
        memories=[{"title": "payment", "description": "", "content": "payment"}],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 0


def test_insert_auto_link_respects_threshold(svc):
    """Auto-link should not create links below the configured threshold."""
    service, engine = svc

    seed = service.write_service.insert(
        memories=[{"title": "seed", "description": "", "content": "seed content"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # Score below default threshold of 0.85
    engine._search_results = [{"lore_id": seed_id, "score": 0.70}]

    result = service.write_service.insert(
        memories=[{"title": "new", "description": "", "content": "new content"}],
        links=[],
    )
    new_id = result["inserted_memories"][0]["id"]

    links = service.links.links_for_memory(new_id)
    assert len(links) == 0


def test_auto_link_uses_settings_k(svc):
    """_auto_link searches with settings.auto_link_k candidates, not hardcoded 2."""
    service, engine = svc
    service.settings.auto_link_k = 10

    seed = service.write_service.insert(
        memories=[{"title": "seed", "description": "", "content": "seed"}],
        links=[],
    )
    seed_id = seed["inserted_memories"][0]["id"]

    # If engine is called with limit=10, the first 2 results are below threshold
    # but the 10th is a 0.95 match
    hits = [{"lore_id": f"noise-{i}", "score": 0.5} for i in range(9)]
    hits.append({"lore_id": seed_id, "score": 0.95})
    engine._search_results = hits

    result = service.write_service.insert(
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
    r1 = service.write_service.insert(
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
    result = service.write_service.insert(
        memories=[{
            "title": "source with inline link",
            "description": "s",
            "content": "source",
            "links": [{
                "target_memory_id": id_a,
                "relation_type": "part_of",
                "reason": "inline link",
            }],
        }],
        links=[{
            "source_memory_id": id_b,
            "target_memory_id": id_c,
            "relation_type": "references",
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
