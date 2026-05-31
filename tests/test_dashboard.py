"""Dashboard integration tests using FastAPI TestClient.

Tests all API routes with an isolated in-memory SQLite DB and fake engine.
Uses tmp_path to avoid touching any real ~/.lorekeeper/ data.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from lorekeeper.config import Settings
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.orchestrator import MemoryService

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

    def find_mem0_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None


# ── Factory ───────────────────────────────────────────────────────────────────


def _make_svc(tmp_path: str) -> tuple[MemoryService, FakeEngine]:
    store = LinkStore(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    svc = MemoryService(engine, store, kw, settings)
    return svc, engine


def _client_for(svc: MemoryService) -> TestClient:
    """Create a TestClient patched at the dashboard level (where init_service is imported)."""
    from lorekeeper.dashboard import app as dash_app

    # Patch the dashboard's local references to init_service and get_service
    with (
        patch("lorekeeper.dashboard.app.init_service", return_value=svc),
        patch("lorekeeper.dashboard.app.get_service", return_value=svc),
    ):
        # The lifespan will call the patched init_service (no-op) and then get_service works
        yield TestClient(dash_app.app)


@pytest.fixture
def fresh_client(tmp_path):
    """Each test gets its own clean service + client with no seed data."""
    svc_obj, _engine = _make_svc(tmp_path)
    import lorekeeper.server as srv

    srv._svc = svc_obj

    from lorekeeper.dashboard import app as dash_app

    with (
        patch("lorekeeper.dashboard.app.init_service", return_value=svc_obj),
        patch("lorekeeper.dashboard.app.get_service", return_value=svc_obj),
    ):
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
    mem_id = svc_obj._store.all_memory_rows(include_deleted=True)[0]["id"]
    engine._store[mem_id] = "test memory desc content"

    import lorekeeper.server as srv

    srv._svc = svc_obj

    from lorekeeper.dashboard import app as dash_app

    with (
        patch("lorekeeper.dashboard.app.init_service", return_value=svc_obj),
        patch("lorekeeper.dashboard.app.get_service", return_value=svc_obj),
    ):
        with TestClient(dash_app.app) as client:
            yield client, svc_obj, engine


def c(fixture_val):
    """Extract just the TestClient from a fixture tuple."""
    return fixture_val[0]


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
    mem_id = svc_obj._store.all_memory_rows(include_deleted=True)[0]["id"]
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
    mem_id = svc_obj._store.all_memory_rows(include_deleted=True)[0]["id"]
    resp = client.patch(f"/api/memories/{mem_id}", json={"title": "updated title"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    row = svc_obj._store.get_memory_row(mem_id)
    assert row["title"] == "updated title"


def test_update_memory_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/memories/nonexistent", json={"title": "new"})
    assert resp.status_code == 404


# ── DELETE /api/memories/{id} ─────────────────────────────────────────────────


def test_delete_memory(seeded_client):
    client, svc_obj, _engine = seeded_client
    mem_id = svc_obj._store.all_memory_rows(include_deleted=True)[0]["id"]
    resp = client.delete(f"/api/memories/{mem_id}")
    assert resp.status_code == 200
    assert svc_obj._store.get_memory_row(mem_id) is None


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
    src_id = svc_obj._store.all_memory_rows(include_deleted=True)[0]["id"]
    # Insert a second memory to link to
    svc_obj.insert(
        memories=[{"title": "target mem", "description": "desc", "content": "c"}],
        links=[],
    )
    tgt_id = svc_obj._store.all_memory_rows(include_deleted=True)[1]["id"]
    svc_obj._store.insert_link(
        source_memory_id=src_id,
        target_memory_id=tgt_id,
        relation_type="related_to",
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
    memories = svc_obj._store.all_memory_rows(include_deleted=True)
    src_id = memories[0]["id"]
    # Insert a target memory
    svc_obj.insert(
        memories=[{"title": "target", "description": "d", "content": "c"}],
        links=[],
    )
    tgt_id = svc_obj._store.all_memory_rows(include_deleted=True)[1]["id"]
    resp = client.post(
        "/api/links",
        json={
            "source_memory_id": src_id,
            "target_memory_id": tgt_id,
            "relation_type": "related_to",
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
            "relation_type": "related_to",
            "reason": "x",
        },
    )
    assert resp.status_code == 404


# ── DELETE /api/links/{id} ────────────────────────────────────────────────────


def test_delete_link_not_found(fresh_client):
    client, _svc, _engine = fresh_client
    resp = client.delete("/api/links/nonexistent")
    assert resp.status_code == 404


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
    """Sending string for a float field should return 422."""
    client, _svc, _engine = fresh_client
    resp = client.patch("/api/config", json={"w_semantic": "banana"})
    assert resp.status_code == 422


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
