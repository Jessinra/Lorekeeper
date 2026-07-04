"""Processor-level tests for LinkProcessor — validation, orchestration, metrics, commits.

Consolidates the link list/create/delete logic that used to be inline in
``dashboard/routes/links.py``.  Each test constructs a LinkProcessor with
real domain service instances and validates that:
- source/target existence is validated before writing (LookupError, not 404 —
  the route layer maps that)
- relation_type validation fires
- commit() happens on writes, not in the route
"""

from __future__ import annotations

import pytest

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.processors.link import LinkProcessor
from tests._helpers import build_service, build_stores
from tests.test_handlers import FakeEngine


@pytest.fixture
def stores(tmp_path):
    return build_stores(tmp_path / "test.db")


@pytest.fixture
def svc(stores):
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_service(stores, engine, kw, settings)


@pytest.fixture
def processor(svc, stores):
    return LinkProcessor(
        link_service=svc.link_service,
        memories=stores.memories,
        links=stores.links,
        metrics=stores.metrics,
        db=stores.db,
    )


def _insert_two_memories(svc) -> tuple[str, str]:
    r = svc.insert(
        memories=[
            {"title": "mem A", "content": "a"},
            {"title": "mem B", "content": "b"},
        ],
        links=[],
    )
    ids = [m["id"] for m in r["inserted_memories"]]
    return ids[0], ids[1]


# ── list_links ──────────────────────────────────────────────────────────────


def test_list_links_empty_returns_empty_list(processor):
    assert processor.list_links() == []


def test_list_links_returns_created_link_with_titles(processor, svc):
    src_id, tgt_id = _insert_two_memories(svc)
    processor.create_link(src_id, tgt_id, "references", "test link")
    links = processor.list_links()
    assert len(links) == 1
    assert links[0]["source_title"] == "mem A"
    assert links[0]["target_title"] == "mem B"


def test_list_links_excludes_deleted_by_default(processor, svc, stores):
    src_id, tgt_id = _insert_two_memories(svc)
    processor.create_link(src_id, tgt_id, "references", "test link")
    stores.memories.update_memory_fields(src_id, soft_deleted=1)
    stores.db.commit()
    assert processor.list_links(include_deleted=False) == []


def test_list_links_includes_deleted_when_requested(processor, svc, stores):
    src_id, tgt_id = _insert_two_memories(svc)
    processor.create_link(src_id, tgt_id, "references", "test link")
    stores.memories.update_memory_fields(src_id, soft_deleted=1)
    stores.db.commit()
    assert len(processor.list_links(include_deleted=True)) == 1


# ── create_link: validation ─────────────────────────────────────────────────


def test_create_link_source_not_found_raises_lookup_error(processor, svc):
    _src_id, tgt_id = _insert_two_memories(svc)
    with pytest.raises(LookupError, match="Source memory not found"):
        processor.create_link("nonexistent", tgt_id, "references", "reason")


def test_create_link_target_not_found_raises_lookup_error(processor, svc):
    src_id, _tgt_id = _insert_two_memories(svc)
    with pytest.raises(LookupError, match="Target memory not found"):
        processor.create_link(src_id, "nonexistent", "references", "reason")


def test_create_link_invalid_relation_type_raises_value_error(processor, svc):
    src_id, tgt_id = _insert_two_memories(svc)
    with pytest.raises(ValueError, match="invalid relation_type"):
        processor.create_link(src_id, tgt_id, "bogus_relation", "reason")


# ── create_link: happy path + commit boundary ───────────────────────────────


def test_create_link_valid_call_returns_link(processor, svc):
    src_id, tgt_id = _insert_two_memories(svc)
    link = processor.create_link(src_id, tgt_id, "references", "reason")
    assert link.source_memory_id == src_id
    assert link.target_memory_id == tgt_id


def test_create_link_persists_after_commit(processor, svc, stores):
    """create_link must commit — a fresh read must see the row."""
    src_id, tgt_id = _insert_two_memories(svc)
    link = processor.create_link(src_id, tgt_id, "references", "reason")
    reread = stores.links.get_link(link.id)
    assert reread is not None


# ── delete_link ──────────────────────────────────────────────────────────────


def test_delete_link_not_found_raises_lookup_error(processor):
    with pytest.raises(LookupError, match="Link not found"):
        processor.delete_link("nonexistent")


def test_delete_link_removes_link(processor, svc, stores):
    src_id, tgt_id = _insert_two_memories(svc)
    link = processor.create_link(src_id, tgt_id, "references", "reason")
    processor.delete_link(link.id)
    assert stores.links.get_link(link.id) is None
