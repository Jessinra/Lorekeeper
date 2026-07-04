"""Dashboard integration tests using FastAPI TestClient.

Tests all API routes with an isolated in-memory SQLite DB and fake engine.
Uses tmp_path to avoid touching any real ~/.lorekeeper/ data.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.services.orchestrator import MemoryService
from tests._helpers import build_service, build_stores

# ── Fake Engine ───────────────────────────────────────────────────────────────


class FakeEngine:
    """Minimal stub — stores text by lore_id, returns configurable search results."""

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


# ── Factory ───────────────────────────────────────────────────────────────────


def _make_svc(tmp_path: str) -> tuple[MemoryService, FakeEngine]:
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    svc = build_service(store, engine, kw, settings)
    return svc, engine


@pytest.fixture
def fresh_client(tmp_path):
    """Each test gets its own clean service + client with no seed data."""
    svc_obj, _engine = _make_svc(tmp_path)
    import lorekeeper.server as srv

    srv._svc = svc_obj

    from lorekeeper.dashboard import app as dash_app

    with patch("lorekeeper.dashboard.app.init_service", return_value=svc_obj):
        with TestClient(dash_app.app) as client:
            yield client, svc_obj, _engine


@pytest.fixture
def seeded_client(tmp_path):
    """Service with one pre-seeded memory for retrieval tests."""
    svc_obj, engine = _make_svc(tmp_path)
    svc_obj.insert(
        memories=[{"title": "test memory", "description": "desc", "content": "content"}],
        links=[],
    )
    mem_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    engine._store[mem_id] = "test memory desc content"

    import lorekeeper.server as srv

    srv._svc = svc_obj

    from lorekeeper.dashboard import app as dash_app

    with patch("lorekeeper.dashboard.app.init_service", return_value=svc_obj):
        with TestClient(dash_app.app) as client:
            yield client, svc_obj, engine


# ── GET /api/memories ─────────────────────────────────────────────────────────


def test_list_memories_empty(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/memories")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_memories_with_data(seeded_client):
    client, _svc, _engine = seeded_client
    resp = client.get("/api/memories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "test memory"
    assert "link_count" in data[0]


def test_list_memories_include_deleted(seeded_client):
    client, _svc, _engine = seeded_client
    resp = client.get("/api/memories?include_deleted=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


# ── GET /api/memories/{id} ────────────────────────────────────────────────────


def test_get_memory_found(seeded_client):
    client, svc_obj, _engine = seeded_client
    mem_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    resp = client.get(f"/api/memories/{mem_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["memory"]["id"] == mem_id
    assert "links" in body


def test_get_memory_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/memories/nonexistent-id")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── PATCH /api/memories/{id} ──────────────────────────────────────────────────


def test_update_memory(seeded_client):
    client, svc_obj, _engine = seeded_client
    mem_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    resp = client.patch(f"/api/memories/{mem_id}", json={"title": "updated title"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    row = svc_obj.memories.get_memory_row(mem_id)
    assert row["title"] == "updated title"


def test_update_memory_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/memories/nonexistent", json={"title": "new"})
    assert resp.status_code == 404


# ── DELETE /api/memories/{id} ─────────────────────────────────────────────────


def test_delete_memory(seeded_client):
    client, svc_obj, _engine = seeded_client
    mem_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    resp = client.delete(f"/api/memories/{mem_id}")
    assert resp.status_code == 200
    assert svc_obj.memories.get_memory_row(mem_id) is None


def test_delete_memory_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.delete("/api/memories/nonexistent")
    assert resp.status_code == 404


# ── GET /api/links ────────────────────────────────────────────────────────────


def test_list_links_empty(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/links")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_links_with_data(seeded_client):
    client, svc_obj, _engine = seeded_client
    src_id = svc_obj.memories.all_memory_rows(include_deleted=True)[0]["id"]
    # Insert a second memory to link to
    svc_obj.insert(
        memories=[{"title": "target mem", "description": "desc", "content": "c"}],
        links=[],
    )
    tgt_id = svc_obj.memories.all_memory_rows(include_deleted=True)[1]["id"]
    svc_obj.links.insert_link(
        source_memory_id=src_id,
        target_memory_id=tgt_id,
        relation_type="references",
        reason="test link",
    )
    resp = client.get("/api/links")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "source_title" in data[0]
    assert "target_title" in data[0]


# ── POST /api/links ───────────────────────────────────────────────────────────


def test_create_link(seeded_client):
    client, svc_obj, _engine = seeded_client
    memories = svc_obj.memories.all_memory_rows(include_deleted=True)
    src_id = memories[0]["id"]
    # Insert a target memory
    svc_obj.insert(
        memories=[{"title": "target", "description": "d", "content": "c"}],
        links=[],
    )
    tgt_id = svc_obj.memories.all_memory_rows(include_deleted=True)[1]["id"]
    resp = client.post(
        "/api/links",
        json={
            "source_memory_id": src_id,
            "target_memory_id": tgt_id,
            "relation_type": "references",
            "reason": "because",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["source_memory_id"] == src_id
    assert data["target_memory_id"] == tgt_id


def test_create_link_source_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.post(
        "/api/links",
        json={
            "source_memory_id": "no-such",
            "target_memory_id": "also-no-such",
            "relation_type": "references",
            "reason": "x",
        },
    )
    assert resp.status_code == 404


# ── DELETE /api/links/{id} ────────────────────────────────────────────────────


def test_delete_link_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.delete("/api/links/nonexistent")
    assert resp.status_code == 404


def test_delete_link_success(seeded_client):
    """Delete an existing link — should return 200 and remove the link."""
    client, svc_obj, _engine = seeded_client
    # Create two memories and a link between them
    svc_obj.insert(
        memories=[{"title": "link target", "description": "d", "content": "c"}],
        links=[],
    )
    rows = svc_obj.memories.all_memory_rows(include_deleted=True)
    src_id, tgt_id = rows[0]["id"], rows[1]["id"]
    link = svc_obj.links.insert_link(
        source_memory_id=src_id,
        target_memory_id=tgt_id,
        relation_type="references",
        reason="test",
    )
    resp = client.delete(f"/api/links/{link.id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert svc_obj.links.get_link(link.id) is None


# ── POST /api/search ──────────────────────────────────────────────────────────


def test_search(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.post("/api/search", json={"query": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── GET /api/config ───────────────────────────────────────────────────────────


def test_get_config(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "data_dir" in data
    assert "w_semantic" in data
    assert "_overridden_keys" in data


# ── PATCH /api/config ─────────────────────────────────────────────────────────


def test_patch_config(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/config", json={"w_semantic": 0.8})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_patch_config_validation_wrong_type(fresh_client):
    """Sending string for a float field should return 422 with descriptive message."""
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/config", json={"w_semantic": "banana"})
    assert resp.status_code == 422
    detail = resp.json()
    # Pydantic's FastAPI integration may catch this at deserialization
    # (returns a list of errors) or our custom validator (returns a single detail string)
    assert isinstance(detail, dict) and len(detail) > 0


def test_patch_config_readonly_key(fresh_client):
    """data_dir and embedding_model are read-only and should be silently skipped."""
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/config", json={"data_dir": "/tmp"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ── GET /api/export ───────────────────────────────────────────────────────────


def test_export(seeded_client):
    client, _svc, _engine = seeded_client
    resp = client.get("/api/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/json"
    data = resp.json()
    assert "version" in data
    assert "memories" in data
    assert "links" in data


# ── POST /api/import/preview ──────────────────────────────────────────────────


def test_import_preview(fresh_client):
    client, _svc, _engine = fresh_client
    payload = json.dumps({"memories": [], "links": []})
    resp = client.post(
        "/api/import/preview",
        files={"file": ("dump.json", payload, "application/json")},
    )
    assert resp.status_code == 200


def test_import_preview_invalid_json(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.post(
        "/api/import/preview",
        files={"file": ("dump.json", b"not json", "application/json")},
    )
    assert resp.status_code == 422


# ── POST /api/import/confirm ──────────────────────────────────────────────────


def test_import_confirm(fresh_client):
    client, _svc, _engine = fresh_client
    payload = json.dumps({"memories": [], "links": []})
    resp = client.post(
        "/api/import/confirm",
        files={"file": ("dump.json", payload, "application/json")},
    )
    assert resp.status_code == 200


# ── GET /api/sessions ─────────────────────────────────────────────────────────


def test_list_sessions(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_sessions_without_content(fresh_client):
    """with_content=false should also work."""
    client, _svc, _engine = fresh_client
    resp = client.get("/api/sessions?with_content=false")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_session_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/sessions/nonexistent")
    assert resp.status_code == 404


# ── GET /api/reflections ──────────────────────────────────────────────────────


def test_list_reflections(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/reflections")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_reflections_with_data(seeded_client):
    """Reflections with real data should serialize correctly
    (exercises the serialize_reflection dict() conversion path)."""
    client, svc_obj, _engine = seeded_client
    svc_obj.submit_reflection(
        session_id="test-session-1",
        session_date="2026-05-31",
        topic="testing",
        task_type="test",
        what_was_done="ran tests",
        decisions="none",
        lessons_learnt=["lesson one"],
        good_patterns=["pattern one"],
        user_profile_updates=[],
        factual_discoveries=[],
        summary="test summary",
        memory_ids=[],
    )
    resp = client.get("/api/reflections")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["summary"] == "test summary"
    assert "lessons_learnt" in data[0]


def test_get_reflection_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/reflections/nonexistent")
    assert resp.status_code == 404


# ── GET /api/metrics ──────────────────────────────────────────────────────────


def test_get_metrics(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "hours" in data
    assert "buckets" in data
    assert "tools" in data
    assert "data" in data


# ── Suggestion route tests (LKPR-101) ────────────────────────────────────────


def _insert_memory(store, mem_id: str, title: str = "Memory") -> None:
    from datetime import UTC, datetime

    store.db.conn.execute(
        "INSERT OR IGNORE INTO memories"
        " (id, title, content, description, source_type, score,"
        "  soft_deleted, usage_count, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            mem_id,
            title,
            "",
            "",
            "observed",
            5.0,
            0,
            0,
            datetime.now(UTC).isoformat(),
            datetime.now(UTC).isoformat(),
        ),
    )
    store.db.conn.commit()


@pytest.fixture
def suggestion_client(tmp_path):
    """Service with 3 memories and 4 seeded suggestions."""
    store = build_stores(tmp_path / "test_sug.db")
    engine = FakeEngine()

    # Seed memories (FK constraint for suggestions)
    mems = {
        "mem-a": "Auth middleware design",
        "mem-b": "API authentication flow",
        "mem-c": "Database schema v3",
        "mem-d": "SQLite migration plan",
    }
    for mid, title in mems.items():
        _insert_memory(store, mid, title)
        engine._store[mid] = title

    # Seed suggestions
    suggestions_data = [
        ("mem-a", "mem-b", "Auth middleware design", "API authentication flow", 0.92),
        ("mem-c", "mem-d", "Database schema v3", "SQLite migration plan", 0.78),
        ("mem-a", "mem-d", "Auth middleware design", "SQLite migration plan", 0.65),
        ("mem-c", "mem-b", "Database schema v3", "API authentication flow", 0.47),
    ]
    sug_ids = []
    for src, tgt, src_title, tgt_title, score in suggestions_data:
        sug = store.suggestions.insert_suggestion(
            source_memory_id=src,
            target_memory_id=tgt,
            source_title=src_title,
            target_title=tgt_title,
            weighted_score=score,
        )
        sug_ids.append(sug.id)

    kw = KeywordIndex()
    settings = Settings()
    svc = build_service(store, engine, kw, settings)

    import lorekeeper.server as srv

    srv._svc = svc
    srv._suggestions_store = store.suggestions
    from lorekeeper.processors.suggestion import SuggestionProcessor

    srv._suggestion_processor = SuggestionProcessor(
        suggestion_service=svc.suggestion_service,
        suggestions=store.suggestions,
        metrics=store.metrics,
        db=store.db,
    )

    from lorekeeper.dashboard import app as dash_app

    with patch("lorekeeper.dashboard.app.init_service", return_value=svc):
        with TestClient(dash_app.app) as client:
            yield client, svc, store, sug_ids


def test_suggestions_list(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert body["items"][0]["weighted_score"] >= body["items"][1]["weighted_score"]


def test_suggestions_pagination(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2


def test_suggestions_filter_by_memory(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions?memory_id=mem-a")
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert item["source_memory_id"] == "mem-a" or item["target_memory_id"] == "mem-a"


def test_suggestions_count(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions/count")
    assert resp.status_code == 200
    assert resp.json()["count"] == 4

    resp = client.get("/api/suggestions/count?memory_id=mem-a")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2  # mem-a has 2 suggestions


def test_suggestions_batch_accept(suggestion_client):
    client, _svc, _store, sug_ids = suggestion_client
    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": [sug_ids[0], sug_ids[1]], "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 2
    assert body["rejected"] == 0

    # Verify suggestions are now accepted
    for sid in sug_ids[:2]:
        sug = _store.suggestions.get_suggestion(sid)
        assert sug is not None
        assert sug.status == "accepted"

    # Verify memory links were actually created
    links = _svc.links._conn.execute(
        "SELECT source_memory_id, target_memory_id FROM memory_links "
        "WHERE reason = 'Accepted from link suggestion sweep'"
    ).fetchall()
    assert len(links) == 2


def test_suggestions_batch_reject(suggestion_client):
    client, _svc, _store, sug_ids = suggestion_client
    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": [sug_ids[2], sug_ids[3]], "action": "reject"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rejected"] == 2

    for sid in sug_ids[2:4]:
        sug = _store.suggestions.get_suggestion(sid)
        assert sug is not None
        assert sug.status == "rejected"


def test_suggestions_batch_not_found(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": ["nonexistent-id"], "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 0
    assert body["errors"] == []
    assert len(body["results"]) == 1
    assert body["results"][0]["status"] == "skipped"


def test_suggestions_batch_accept_rolls_back_link_if_status_update_fails(suggestion_client):
    """LKPR-104 Phase 6b: accept_one's Database.transaction() SAVEPOINT must
    cover insert_link + update_suggestion_status atomically. If the status
    update fails, the link insert must be rolled back too — not left as an
    orphaned link with no corresponding accepted suggestion.
    """
    client, _svc, _store, sug_ids = suggestion_client

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated status update failure")

    _store.suggestions.update_suggestion_status = _boom

    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": [sug_ids[0]], "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 0
    assert len(body["errors"]) == 1

    links = _svc.links.all_links()
    sweep_links = [lnk for lnk in links if lnk.reason == "Accepted from link suggestion sweep"]
    assert sweep_links == []

    sug = _store.suggestions.get_suggestion(sug_ids[0])
    assert sug.status == "pending"


def test_suggestions_batch_invalid_action(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": [], "action": "invalid"},
    )
    assert resp.status_code == 422


def test_sweep_trigger(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.post("/api/sweep/trigger")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Verify config override was set
    overrides = _store.config.get_overrides()
    assert "sweep_next_run_at" in overrides


def test_sweep_status(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/sweep/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "last_run_at" in body
    assert "next_run_at" in body
    # With no sweep_last_run_at override set, should fall back to newest
    # suggestion created_at (not None, since suggestions were inserted in fixture)
    assert body["last_run_at"] is not None


def test_suggestions_invalid_limit(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions?limit=999")
    assert resp.status_code == 422


def test_suggestions_negative_offset(suggestion_client):
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions?offset=-1")
    assert resp.status_code == 422


def test_suggestions_batch_accept_invalid_relation_type(suggestion_client):
    """Accept normalises an invalid suggested_type to 'references'."""
    client, _svc, store, sug_ids = suggestion_client
    # Patch the suggestion's suggested_type to an invalid value
    store.suggestions._conn.execute(
        "UPDATE link_suggestions SET suggested_type = 'bogus_type' WHERE id = ?",
        (sug_ids[0],),
    )
    resp = client.post(
        "/api/suggestions/batch",
        json={"suggestion_ids": [sug_ids[0]], "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 1
    # Link should have been created with fallback 'references' type
    links = _svc.links._conn.execute(
        "SELECT relation_type FROM memory_links "
        "WHERE reason = 'Accepted from link suggestion sweep'"
    ).fetchall()
    assert len(links) == 1
    assert links[0]["relation_type"] == "references"


def test_suggestions_list_db_sorted(suggestion_client):
    """Sorting is applied DB-side: score-asc returns lowest score first."""
    client, _svc, _store, _sug_ids = suggestion_client
    resp = client.get("/api/suggestions?sort_by=weighted_score&sort_dir=asc")
    assert resp.status_code == 200
    items = resp.json()["items"]
    scores = [i["weighted_score"] for i in items]
    assert scores == sorted(scores), "Items should be ascending by weighted_score"
