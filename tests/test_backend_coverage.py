"""
LKPR-78: Critical and high-priority test coverage gaps.

MCP backend (critical):
  - lore_update link_feedback path — completely untested, silent failure risk
  - lore_update memory_feedback with non-existent ID — errors[] not exception
  - lore_processed_sessions + lore_reflect integration round-trip
  - lore_forget mixed found+not_found in a single call
  - lore_insert force=True bypasses dedup

Dashboard API (high priority):
  - GET /api/reflections/{id} success path (was 404-only)
  - GET /api/sessions/{id} with linked reflection
  - GET /api/sessions/{id} without linked reflection (reflection=None branch)
  - POST /api/links target-not-found 404 (source-only was tested)
  - GET /api/links?include_deleted=true filter branch
  - PATCH /api/config + GET read-back verifying persistence
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from tests._helpers import App, build_app, build_stores

# ── Shared fake engine ────────────────────────────────────────────────────────


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


# ── Shared service factory ────────────────────────────────────────────────────


def _make_svc(tmp_path) -> tuple[Any, FakeEngine, Any]:
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    svc = build_app(store, engine, kw, settings)
    return svc, engine, store


@pytest.fixture
def svc(tmp_path):
    service, _, store = _make_svc(tmp_path)
    yield service
    store.close()


# ── Dashboard client fixture ──────────────────────────────────────────────────


@pytest.fixture
def seeded_client(tmp_path):
    svc_obj, engine, store = _make_svc(tmp_path)
    svc_obj.write_service.insert(
        memories=[{"title": "test memory", "description": "desc", "content": "content"}],
        links=[],
    )
    mem_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    engine._store[mem_id] = "test memory desc content"

    import lorekeeper.server as srv
    from lorekeeper.processors.admin import AdminProcessor
    from lorekeeper.processors.link import LinkProcessor
    from lorekeeper.processors.memory import MemoryProcessor
    from lorekeeper.processors.reflection import ReflectionProcessor

    srv._svc = svc_obj
    srv._memory_processor = MemoryProcessor(
        search_service=svc_obj.memory_search_service,
        write_service=svc_obj.memory_write_service,
        import_service=svc_obj.import_service,
        metrics=store.metrics,
        db=store.db,
        settings=Settings(),
    )
    srv._reflection_processor = ReflectionProcessor(
        reflection_service=svc_obj.reflection_service,
        reflections=store.reflections,
        metrics=store.metrics,
        db=store.db,
    )
    srv._link_processor = LinkProcessor(
        link_service=svc_obj.link_service,
        memories=store.memories,
        links=store.links,
        metrics=store.metrics,
        db=store.db,
    )
    srv._admin_processor = AdminProcessor(
        config=store.config,
        metrics=store.metrics,
        suggestions=store.suggestions,
        settings=svc_obj.settings,
        db=store.db,
    )

    from lorekeeper.dashboard import app as dash_app

    with patch("lorekeeper.dashboard.app.init_service", return_value=svc_obj):
        with TestClient(dash_app.app) as client:
            yield client, svc_obj, engine
        store.close()


# =============================================================================
# MCP CRITICAL — lore_update link_feedback
# =============================================================================


class TestUpdateLinkFeedback:
    """link_feedback path in lore_update — zero coverage before this ticket."""

    def _make_link(self, svc: App) -> tuple[str, str, str]:
        """Insert two memories and one link; return (src_id, tgt_id, link_id)."""
        result = svc.write_service.insert(
            memories=[
                {"title": "source mem", "content": "src"},
                {"title": "target mem", "content": "tgt"},
            ],
            links=[],
        )
        ids = [m["id"] for m in result["inserted_memories"]]
        src_id, tgt_id = ids[0], ids[1]
        link = svc.links.insert_link(src_id, tgt_id, "references", "test")
        svc.db.conn.commit()
        return src_id, tgt_id, link.id

    def test_link_feedback_useful_true_bumps_score(self, svc):
        """useful=True on a link increases its score and increments usage_count."""
        _, _, link_id = self._make_link(svc)
        before = svc.links.get_link(link_id)

        result = svc.memory_processor.update(
            memory_feedback=[],
            link_feedback=[{"id": link_id, "useful": True, "confidence": 8}],
        )

        assert result["updated_links"] == 1
        assert result["errors"] == []
        after = svc.links.get_link(link_id)
        assert after.score > before.score
        assert after.usage_count == before.usage_count + 1

    def test_link_feedback_useful_false_decrements_score(self, svc):
        """useful=False on a link decreases its score."""
        _, _, link_id = self._make_link(svc)
        before = svc.links.get_link(link_id)

        result = svc.memory_processor.update(
            memory_feedback=[],
            link_feedback=[{"id": link_id, "useful": False, "confidence": 5}],
        )

        assert result["updated_links"] == 1
        assert result["errors"] == []
        after = svc.links.get_link(link_id)
        assert after.score < before.score

    def test_link_feedback_unknown_id_goes_to_errors(self, svc):
        """Non-existent link ID in link_feedback lands in errors — no exception raised."""
        result = svc.memory_processor.update(
            memory_feedback=[],
            link_feedback=[{"id": "nonexistent-link-id", "useful": True, "confidence": 7}],
        )

        assert result["updated_links"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["id"] == "nonexistent-link-id"
        assert "not found" in result["errors"][0]["error"]


# =============================================================================
# MCP CRITICAL — lore_update memory_feedback error path
# =============================================================================


class TestUpdateMemoryFeedbackErrors:
    def test_nonexistent_memory_id_goes_to_errors_not_exception(self, svc):
        """Non-existent memory ID produces an errors entry — must not raise."""
        result = svc.memory_processor.update(
            memory_feedback=[{"id": "no-such-id", "useful": True, "confidence": 5}],
            link_feedback=[],
        )

        assert result["updated_memories"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["id"] == "no-such-id"
        assert "not found" in result["errors"][0]["error"]


# =============================================================================
# MCP CRITICAL — lore_processed_sessions + lore_reflect integration
# =============================================================================


class TestProcessedSessions:
    def test_empty_when_no_reflections(self, svc):
        """get_processed_session_ids returns empty list before any reflect call."""
        result = svc.reflection_service.get_processed_session_ids()
        assert result == []

    def test_session_id_appears_after_reflect(self, svc):
        """Calling submit_reflection registers session_id as processed."""
        svc.reflection_service.submit_reflection(
            session_id="test-session-abc",
            session_date="2026-06-10",
            summary="test summary",
            topic=None, task_type=None, what_was_done=None, decisions=None,
            lessons_learnt=[], good_patterns=[], user_profile_updates=[],
            factual_discoveries=[], memory_ids=[], auto_insert=False,
        )

        processed = svc.reflection_service.get_processed_session_ids()
        assert "test-session-abc" in processed

    def test_multiple_sessions_all_appear(self, svc):
        """Two reflect calls → both session IDs in processed list."""
        for sid in ("session-1", "session-2"):
            svc.reflection_service.submit_reflection(
                session_id=sid, session_date="2026-06-10",
                summary=f"summary for {sid}",
                topic=None, task_type=None, what_was_done=None, decisions=None,
                lessons_learnt=[], good_patterns=[], user_profile_updates=[],
                factual_discoveries=[], memory_ids=[], auto_insert=False,
            )

        processed = svc.reflection_service.get_processed_session_ids()
        assert "session-1" in processed
        assert "session-2" in processed

    def test_duplicate_reflect_does_not_duplicate_in_processed_list(self, svc):
        """Same session_id reflected twice — appears only once in processed list."""
        for _ in range(2):
            svc.reflection_service.submit_reflection(
                session_id="idempotent-session",
                session_date="2026-06-10",
                summary="same session, called twice",
                topic=None, task_type=None, what_was_done=None, decisions=None,
                lessons_learnt=[], good_patterns=[], user_profile_updates=[],
                factual_discoveries=[], memory_ids=[], auto_insert=False,
            )

        processed = svc.reflection_service.get_processed_session_ids()
        assert processed.count("idempotent-session") == 1


# =============================================================================
# MCP CRITICAL — lore_forget mixed found + not_found
# =============================================================================


class TestForgetMixed:
    def test_mixed_found_and_not_found_in_single_call(self, svc):
        """One existing ID and one unknown ID in the same forget call.
        forgotten and not_found are both populated — not one or the other.
        """
        result = svc.write_service.insert(
            memories=[{"title": "forgettable", "content": "forget me"}],
            links=[],
        )
        real_id = result["inserted_memories"][0]["id"]
        fake_id = "does-not-exist-id"

        forget_result = svc.memory_processor.forget([real_id, fake_id], reason="outdated")

        assert real_id in forget_result["forgotten"]
        assert fake_id in forget_result["not_found"]
        assert forget_result["errors"] == []

        # Confirm the real memory is actually soft-deleted
        row = svc.memories.get_memory_row(real_id)
        assert row is not None  # get_memory_row returns row regardless of soft_deleted
        assert row["soft_deleted"] == 1


# =============================================================================
# MCP CRITICAL — lore_insert force=True bypasses dedup
# =============================================================================


class TestInsertForce:
    def test_force_true_bypasses_semantic_dedup(self, tmp_path):
        """force=True skips the Python-level semantic/fuzzy dedup check.

        When two memories have different titles but semantically similar content,
        force=True inserts both — the semantic dedup guard is bypassed.
        Without force, the second insert would be rejected as a duplicate.
        """
        # Use a very low duplicate_threshold so a pure-semantic hit fires.
        low_threshold_settings = Settings(duplicate_threshold=0.5)
        stores = build_stores(tmp_path / "force_test.db")
        engine = FakeEngine()
        kw = KeywordIndex()
        svc = build_app(stores, engine, kw, low_threshold_settings)

        r1 = svc.write_service.insert(
            memories=[{"title": "mem alpha", "content": "dogs are loyal animals"}],
            links=[],
        )
        first_id = r1["inserted_memories"][0]["id"]
        # Simulate a high semantic score for the first memory so the dedup
        # guard fires at our lowered threshold.
        engine._search_results = [{"lore_id": first_id, "score": 0.99}]

        # Without force: rejected as semantic duplicate (score 0.6*0.99 = 0.594 ≥ 0.5).
        r_no_force = svc.write_service.insert(
            memories=[{"title": "mem beta", "content": "dogs are faithful companions"}],
            links=[],
        )
        assert len(r_no_force["inserted_memories"]) == 0
        assert len(r_no_force["duplicates"]) == 1

        # With force: semantic dedup is skipped — new row must be inserted.
        r_force = svc.write_service.insert(
            memories=[{"title": "mem beta", "content": "dogs are faithful companions"}],
            links=[],
            force=True,
        )
        assert len(r_force["inserted_memories"]) == 1
        assert r_force["duplicates"] == []
        assert len(svc.memories.all_memory_rows()) == 2

    def test_force_true_same_title_same_namespace_hits_db_constraint(self, svc):
        """force=True bypasses Python dedup but the DB enforces UNIQUE(namespace, title).

        Inserting the same title twice with force=True still fails — the error
        appears in errors[] rather than raising an exception. This is the
        current behaviour; a separate ticket should decide whether force=True
        should also bypass the DB constraint (e.g. via a UUID suffix strategy).
        """
        svc.write_service.insert(
            memories=[{"title": "constrained title", "content": "first"}],
            links=[],
        )

        result = svc.write_service.insert(
            memories=[{"title": "constrained title", "content": "second"}],
            links=[],
            force=True,
        )

        # Still only one row in DB — DB constraint prevents the duplicate.
        assert len(svc.memories.all_memory_rows()) == 1
        # Error is surfaced in errors[], not raised as an exception.
        assert len(result["errors"]) == 1
        err_msg = result["errors"][0]["error"].lower()
        assert "unique" in err_msg

    def test_force_false_deduplicates_by_title(self, svc):
        """Baseline: force=False (default) deduplicates on exact title match."""
        svc.write_service.insert(
            memories=[{"title": "same title", "content": "first"}],
            links=[],
        )

        result = svc.write_service.insert(
            memories=[{"title": "same title", "content": "second"}],
            links=[],
        )

        assert len(result["inserted_memories"]) == 0
        assert len(result["duplicates"]) == 1
        assert len(svc.memories.all_memory_rows()) == 1


# =============================================================================
# DASHBOARD HIGH — GET /api/reflections/{id} success path
# =============================================================================


class TestReflectionDetailRoute:
    def test_get_reflection_found(self, seeded_client):
        """GET /api/reflections/{id} — success path was 404-only before this ticket."""
        client, svc_obj, _ = seeded_client
        svc_obj.reflection_service.submit_reflection(
            session_id="detail-session-1",
            session_date="2026-06-10",
            summary="detail test summary",
            topic="testing", task_type="test",
            what_was_done="wrote tests",
            decisions="none",
            lessons_learnt=["lesson one"],
            good_patterns=[],
            user_profile_updates=[],
            factual_discoveries=[],
            memory_ids=[],
        )
        # Get the reflection id from the DB
        reflections = svc_obj.reflections.all_reflections()
        assert len(reflections) == 1
        ref_id = reflections[0]["id"]

        resp = client.get(f"/api/reflections/{ref_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "reflection" in body
        assert "sessions" in body
        assert body["reflection"]["summary"] == "detail test summary"
        assert isinstance(body["sessions"], list)


# =============================================================================
# DASHBOARD HIGH — GET /api/sessions/{id} — both branches
# =============================================================================


class TestSessionDetailRoute:
    def _submit_reflection(self, svc_obj, session_id: str) -> str:
        """Helper: submit a reflection and return its reflection_id."""
        svc_obj.reflection_service.submit_reflection(
            session_id=session_id,
            session_date="2026-06-10",
            summary="session detail test",
            topic=None, task_type=None, what_was_done=None, decisions=None,
            lessons_learnt=[], good_patterns=[], user_profile_updates=[],
            factual_discoveries=[], memory_ids=[],
        )
        return svc_obj.reflections.all_reflections()[0]["id"]

    def test_get_session_with_linked_reflection(self, seeded_client):
        """Session that has a reflection_id — reflection key is populated."""
        client, svc_obj, _ = seeded_client
        sid = "session-with-ref"
        self._submit_reflection(svc_obj, sid)

        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        assert "reflection" in body
        # Linked reflection must have these keys
        ref = body["reflection"]
        assert ref is not None
        assert "id" in ref
        assert "summary" in ref
        assert "created_at" in ref

    def test_get_session_without_reflection(self, seeded_client):
        """Session with no linked reflection — reflection key is None."""
        client, svc_obj, _ = seeded_client
        # Upsert a bare session (no reflection_id)
        svc_obj.reflections.upsert_session(
            session_id="orphan-session",
            reviewed_at="2026-06-10T00:00:00",
            reflection_id=None,
        )
        svc_obj.db.conn.commit()

        resp = client.get("/api/sessions/orphan-session")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reflection"] is None


# =============================================================================
# DASHBOARD HIGH — POST /api/links target-not-found
# =============================================================================


class TestCreateLinkTargetNotFound:
    def test_create_link_target_not_found_returns_404(self, seeded_client):
        """Source exists but target does not — must return 404 (separate code path)."""
        client, svc_obj, _ = seeded_client
        src_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]

        resp = client.post(
            "/api/links",
            json={
                "source_memory_id": src_id,
                "target_memory_id": "nonexistent-target",
                "relation_type": "references",
                "reason": "testing",
            },
        )
        assert resp.status_code == 404
        assert "target" in resp.json()["detail"].lower()


# =============================================================================
# DASHBOARD HIGH — GET /api/links?include_deleted=true filter branch
# =============================================================================


class TestLinksIncludeDeleted:
    def _make_link_to_soft_deleted(self, svc_obj) -> tuple[str, str]:
        """Create two memories, link them, soft-delete the target. Return (src_id, tgt_id)."""
        # Capture IDs explicitly — don't rely on all_memory_rows() row order (no ORDER BY)
        result = svc_obj.write_service.insert(
            memories=[{"title": "target to delete", "content": "tgt"}],
            links=[],
        )
        tgt_id = result["inserted_memories"][0]["id"]
        src_rows = svc_obj.memories.all_memory_rows(include_deleted=False)
        src_id = next(r["id"] for r in src_rows if r["title"] == "test memory")
        svc_obj.links.insert_link(src_id, tgt_id, "references", "test")
        svc_obj.db.conn.commit()
        # Soft-delete the target
        svc_obj.write_service.forget([tgt_id], reason="outdated")
        return src_id, tgt_id

    def test_link_to_soft_deleted_hidden_by_default(self, seeded_client):
        """Links where either endpoint is soft-deleted are excluded from default list."""
        client, svc_obj, _ = seeded_client
        self._make_link_to_soft_deleted(svc_obj)

        resp = client.get("/api/links")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_link_to_soft_deleted_visible_with_include_deleted(self, seeded_client):
        """Same link IS returned when include_deleted=true is passed."""
        client, svc_obj, _ = seeded_client
        self._make_link_to_soft_deleted(svc_obj)

        resp = client.get("/api/links?include_deleted=true")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


# =============================================================================
# DASHBOARD HIGH — PATCH /api/config + GET read-back
# =============================================================================


class TestConfigPersistence:
    def test_patch_config_value_persists_in_get(self, seeded_client):
        """PATCH /api/config must persist — GET after PATCH must return new value."""
        client, _, _ = seeded_client

        patch_resp = client.patch("/api/config", json={"w_semantic": 0.75})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["ok"] is True

        get_resp = client.get("/api/config")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["w_semantic"] == pytest.approx(0.75)
        assert "w_semantic" in data["_overridden_keys"]
