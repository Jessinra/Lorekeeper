"""ImportService (backup/dump restore) tests.

Covers the rare admin restore path extracted in LKPR-104 Phase 5:
dry-run preview, real insert, dedup-by-id skip, FK validation,
legacy relation-type normalization, and per-item error capture.
Uses real SQLite (build_stores) + FakeEngine.
"""
from __future__ import annotations

import pytest

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from tests._helpers import FakeEngine, build_app, build_stores


@pytest.fixture
def app(tmp_path):
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_app(store, engine, kw, settings), engine


def _mem(mid: str, **over):
    base = {
        "id": mid,
        "title": f"title-{mid}",
        "description": f"desc-{mid}",
        "content": f"content-{mid}",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(over)
    return base


def _link(lid: str, src: str, tgt: str, **over):
    base = {
        "id": lid,
        "source_memory_id": src,
        "target_memory_id": tgt,
        "relation_type": "references",
        "reason": "test",
    }
    base.update(over)
    return base


# ── dry-run preview ──────────────────────────────────────────────────────


def test_dry_run_previews_without_writing(app):
    service, _ = app
    result = service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")],
        links=[_link("l1", "m1", "m2")],
        dry_run=True,
    )
    assert result["memories_inserted"] == 2
    assert result["links_inserted"] == 1
    assert len(result["preview_memories"]) == 2
    assert len(result["preview_links"]) == 1
    assert result["preview_memories"][0]["id"] == "m1"
    assert result["preview_links"][0]["source_memory_id"] == "m1"
    # Nothing actually persisted.
    assert service.memories.all_memory_rows(include_deleted=True) == []


# ── real insert ────────────────────────────────────────────────────────────


def test_real_insert_persists_memories_and_links(app):
    service, engine = app
    result = service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")],
        links=[_link("l1", "m1", "m2")],
        dry_run=False,
    )
    assert result["memories_inserted"] == 2
    assert result["links_inserted"] == 1
    assert result["errors"] == []
    rows = {r["id"] for r in service.memories.all_memory_rows(include_deleted=True)}
    assert rows == {"m1", "m2"}
    assert engine._store.keys() >= {"m1", "m2"}
    assert {lnk.id for lnk in service.links.all_links()} == {"l1"}


# ── dedup by id ──────────────────────────────────────────────────────────────


def test_existing_memory_is_skipped(app):
    service, _ = app
    service.import_service.import_dump(memories=[_mem("m1")], links=[], dry_run=False)
    result = service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")], links=[], dry_run=False
    )
    assert result["memories_skipped"] == 1
    assert result["memories_inserted"] == 1


def test_existing_link_is_skipped(app):
    service, _ = app
    service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")],
        links=[_link("l1", "m1", "m2")],
        dry_run=False,
    )
    result = service.import_service.import_dump(
        memories=[], links=[_link("l1", "m1", "m2")], dry_run=False
    )
    assert result["links_skipped"] == 1
    assert result["links_inserted"] == 0


# ── validation / error paths ───────────────────────────────────────────────


def test_memory_missing_id_records_error(app):
    service, _ = app
    result = service.import_service.import_dump(
        memories=[_mem("", id="")], links=[], dry_run=False
    )
    assert result["memories_inserted"] == 0
    assert any("memory missing id" in e for e in result["errors"])


def test_link_missing_id_records_error(app):
    service, _ = app
    result = service.import_service.import_dump(
        memories=[], links=[_link("", "m1", "m2", id="")], dry_run=False
    )
    assert result["links_inserted"] == 0
    assert any("link missing id" in e for e in result["errors"])


def test_link_with_unknown_endpoints_counts_as_error(app):
    service, _ = app
    result = service.import_service.import_dump(
        memories=[], links=[_link("l1", "ghost-src", "ghost-tgt")], dry_run=False
    )
    assert result["links_error"] == 1
    assert result["links_inserted"] == 0


# ── legacy relation-type normalization ──────────────────────────────────────


def test_legacy_relation_type_is_normalized(app):
    service, _ = app
    # "used_by" → "depends_on" per types.yaml migration_map.
    service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")],
        links=[_link("l1", "m1", "m2", relation_type="used_by")],
        dry_run=False,
    )
    stored = {lnk.id: lnk for lnk in service.links.all_links()}
    assert stored["l1"].relation_type == "depends_on"


def test_legacy_relation_type_normalized_in_dry_run_preview(app):
    service, _ = app
    result = service.import_service.import_dump(
        memories=[_mem("m1"), _mem("m2")],
        links=[_link("l1", "m1", "m2", relation_type="related_to")],
        dry_run=True,
    )
    assert result["preview_links"][0]["relation_type"] == "references"


# ── per-item exception capture ───────────────────────────────────────────────


def test_memory_insert_exception_is_captured(app):
    service, engine = app

    def _boom(text, lore_id, extra_metadata=None):
        raise RuntimeError("engine down")

    engine.add = _boom  # type: ignore[method-assign]
    result = service.import_service.import_dump(
        memories=[_mem("m1")], links=[], dry_run=False
    )
    assert result["memories_inserted"] == 0
    assert any("m1" in e and "engine down" in e for e in result["errors"])
