"""ReflectionService integration tests.

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


# ── Submit reflection ──────────────────────────────────────────────────────


def test_submit_reflection_first_call_succeeds(svc):
    """First lore_reflect call for a session should store a reflection and return reflection_id."""
    service, _ = svc
    result = service.reflection_service.submit_reflection(
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
    first = service.reflection_service.submit_reflection(
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
    second = service.reflection_service.submit_reflection(
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
        service.reflection_service.submit_reflection(
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


# ── Auto-insert on lore_reflect ────────────────────────────────────────────


def _reflect(service, session_id="s-lkpr30", discoveries=None, lessons=None, auto_insert=True):
    """Helper to call submit_reflection with LKPR-30 params."""
    return service.reflection_service.submit_reflection(
        session_id=session_id,
        session_date="2026-06-02",
        topic="test",
        task_type="build",
        what_was_done="stuff",
        decisions="none",
        lessons_learnt=lessons or [],
        good_patterns=[],
        user_profile_updates=[],
        factual_discoveries=discoveries or [],
        summary="summary",
        memory_ids=[],
        auto_insert=auto_insert,
    )


def test_reflect_auto_insert_creates_memories_from_discoveries(svc):
    """factual_discoveries items must be inserted as memories when auto_insert=True."""
    service, _ = svc
    result = _reflect(
        service, discoveries=["BM25 rebuild costs 10ms", "LanceDB is concurrent-safe"]
    )
    assert "memories_created" in result
    assert len(result["memories_created"]) == 2


def test_reflect_auto_insert_creates_memories_from_lessons(svc):
    """lessons_learnt items must be inserted as memories when auto_insert=True."""
    service, _ = svc
    result = _reflect(service, session_id="s-lessons", lessons=["Always write tests first"])
    assert len(result["memories_created"]) == 1


def test_reflect_auto_insert_both_types(svc):
    """Both factual_discoveries and lessons_learnt should produce memories."""
    service, _ = svc
    result = _reflect(
        service,
        session_id="s-both",
        discoveries=["Fact A"],
        lessons=["Lesson B"],
    )
    assert len(result["memories_created"]) == 2
    relations = {m["relation"] for m in result["memories_created"]}
    assert "discovered_in" in relations
    assert "learned_in" in relations


def test_reflect_auto_insert_scores_correctly(svc):
    """Discoveries score 7.0, lessons score 8.0."""
    service, _ = svc
    result = _reflect(
        service,
        session_id="s-scores",
        discoveries=["discovery item"],
        lessons=["lesson item"],
    )
    ids_by_relation = {m["relation"]: m["id"] for m in result["memories_created"]}
    discovery_row = service.memories.get_memory_row(ids_by_relation["discovered_in"])
    lesson_row = service.memories.get_memory_row(ids_by_relation["learned_in"])
    assert discovery_row["score"] == pytest.approx(7.0)
    assert lesson_row["score"] == pytest.approx(8.0)


def test_reflect_auto_insert_false_skips_creation(svc):
    """auto_insert=False must skip memory creation entirely."""
    service, _ = svc
    result = _reflect(
        service,
        session_id="s-no-insert",
        discoveries=["something"],
        lessons=["something else"],
        auto_insert=False,
    )
    assert result["memories_created"] == []


def test_reflect_auto_insert_empty_lists_returns_empty(svc):
    """No discoveries and no lessons → memories_created is empty list."""
    service, _ = svc
    result = _reflect(service, session_id="s-empty")
    assert result["memories_created"] == []


def test_reflect_auto_insert_return_has_id_title_relation(svc):
    """Each entry in memories_created must have id, title, relation, status keys."""
    service, _ = svc
    result = _reflect(service, session_id="s-shape", discoveries=["Python GIL released on I/O"])
    assert len(result["memories_created"]) == 1
    entry = result["memories_created"][0]
    assert "id" in entry
    assert "title" in entry
    assert entry["relation"] == "discovered_in"
    assert entry["status"] == "inserted"


def test_reflect_auto_insert_dedup_blocked_returns_existing_id(svc):
    """Duplicate discovery returns existing memory id with status='duplicate'."""
    service, _ = svc
    # First reflection creates the memory
    r1 = _reflect(service, session_id="s-dup-1", discoveries=["Unique fact about dedup"])
    first_id = r1["memories_created"][0]["id"]
    assert r1["memories_created"][0]["status"] == "inserted"

    # Second reflection with same text — dedup should block re-insert
    r2 = _reflect(service, session_id="s-dup-2", discoveries=["Unique fact about dedup"])
    second_id = r2["memories_created"][0]["id"]
    assert r2["memories_created"][0]["status"] == "duplicate"

    assert first_id == second_id, "Duplicate discovery should return existing memory id"


def test_reflect_auto_insert_memory_ids_populated(svc):
    """reflection_id return should include memories_created, not just IDs field."""
    service, _ = svc
    result = _reflect(
        service,
        session_id="s-mem-ids",
        discoveries=["A fact"],
        lessons=["A lesson"],
    )
    # All returned memory ids must exist in the memories store
    for entry in result["memories_created"]:
        row = service.memories.get_memory_row(entry["id"])
        assert row is not None, f"Memory {entry['id']} was not found in store"


def test_reflect_auto_insert_partial_failure_continues(svc):
    """If one item raises during auto-insert, others still succeed (best-effort)."""
    service, _ = svc

    import lorekeeper.domains.reflection.service as ref_service

    original_extract = ref_service.extract_title

    call_count = 0

    def patched_extract(text):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated extract failure")
        return original_extract(text)

    ref_service.extract_title = patched_extract
    try:
        result = _reflect(
            service,
            session_id="s-partial",
            discoveries=["this one fails", "this one succeeds"],
        )
        # One failed, one succeeded → only one entry in memories_created
        assert len(result["memories_created"]) == 1
        assert result["memories_created"][0]["relation"] == "discovered_in"
    finally:
        ref_service.extract_title = original_extract
