"""Processor-level tests for MemoryProcessor — validation, orchestration, metrics.

Validation moved here from the handler layer.  Each test constructs a
MemoryProcessor with real domain service instances and validates that:
- input validation fires before any store/engine access
- metrics are incremented correctly
- edge cases are handled
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.processors.memory import MemoryProcessor
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
    return MemoryProcessor(
        search_service=svc.memory_search_service,
        write_service=svc.memory_write_service,
        import_service=svc.import_service,
        metrics=stores.metrics,
        db=stores.db,
        settings=Settings(),
    )


# ── search: format validation ─────────────────────────────────────────────


def test_search_invalid_format_raises(processor):
    with pytest.raises(ValueError, match="Unknown format"):
        processor.search("query", search_format="xml")


def test_search_valid_format_full_does_not_raise(processor):
    results = processor.search("query", search_format="full")
    assert isinstance(results, list)


def test_search_valid_format_title_does_not_raise(processor):
    results = processor.search("query", search_format="title")
    assert isinstance(results, list)


# ── search: sort_by validation ────────────────────────────────────────────


def test_sort_by_unknown_value_raises(processor):
    with pytest.raises(ValueError, match="Unknown sort_by"):
        processor.search("test", sort_by="magic")


def test_sort_by_valid_values_do_not_raise(processor):
    for valid in ("relevance", "recent", "frequent"):
        results = processor.search("test", sort_by=valid)
        assert isinstance(results, list)


# ── search: source_type validation ─────────────────────────────────────────


def test_source_type_unknown_value_raises(processor):
    with pytest.raises(ValueError, match="Unknown source_type"):
        processor.search("test", source_type="nonexistent")


# ── search: ids cap ────────────────────────────────────────────────────────


def test_search_by_ids_exceeds_cap_raises(processor):
    oversize = [str(i) for i in range(51)]
    with pytest.raises(ValueError, match="ids exceeds cap of 50 IDs"):
        processor.search("query", ids=oversize)


# ── search: empty query guard ──────────────────────────────────────────────


def test_search_empty_query_without_ids_raises(processor):
    with pytest.raises(ValueError, match="query is required"):
        processor.search("")


def test_search_blank_query_without_ids_raises(processor):
    with pytest.raises(ValueError, match="query is required"):
        processor.search("   ")


def test_search_empty_query_with_ids_succeeds(processor):
    results = processor.search("", ids=[])
    assert results == []


# ── search: refine_from cap ───────────────────────────────────────────────


def test_search_refine_from_exceeds_cap_raises(processor):
    oversize = [str(i) for i in range(201)]
    with pytest.raises(ValueError, match="refine_from exceeds cap of 200 IDs"):
        processor.search("test", refine_from=oversize)


def test_search_refine_from_empty_succeeds(processor):
    results = processor.search("test", refine_from=[])
    assert isinstance(results, list)


# ── search: created_after / updated_after validation ──────────────────────


def test_created_after_invalid_iso_string_raises(processor):
    with pytest.raises(ValueError, match="Invalid ISO timestamp for 'created_after'"):
        processor.search("test", created_after="not-a-date")


def test_updated_after_invalid_iso_string_raises(processor):
    with pytest.raises(ValueError, match="Invalid ISO timestamp for 'updated_after'"):
        processor.search("test", updated_after="2026/06/01")


def test_created_after_non_utc_offset_raises(processor):
    with pytest.raises(ValueError, match="Non-UTC timezone offset"):
        processor.search("test", created_after="2026-06-01T00:00:00+05:30")


# ── remember: source_type validation ──────────────────────────────────────


def test_remember_invalid_source_type_raises(processor):
    with pytest.raises(ValueError, match="Unknown source_type"):
        processor.remember("my thought", source_type="magic")


# ── forget: validation ────────────────────────────────────────────────────


def test_forget_empty_ids_raises(processor):
    with pytest.raises(ValueError, match="memory_ids must not be empty"):
        processor.forget([])


def test_forget_invalid_reason_raises(processor):
    with pytest.raises(ValueError, match="Unknown reason"):
        processor.forget(["some-id"], reason="invalid")


# ── insert: validation ────────────────────────────────────────────────────


def test_insert_missing_title_raises(processor):
    with pytest.raises(ValueError, match="memory at index 0"):
        processor.insert(memories=[{"content": "no title here"}])


def test_insert_invalid_source_type_raises(processor):
    with pytest.raises(ValueError, match="invalid source_type"):
        processor.insert(memories=[{"title": "test", "source_type": "magic"}])


# ── metric increment tests ────────────────────────────────────────────────


def test_search_increments_lore_search_metric(processor):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.search("test")
        mock.assert_any_call("lore_search")


def test_insert_increments_lore_insert_metric(processor):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.insert(memories=[], links=[])
        mock.assert_any_call("lore_insert")


def test_remember_increments_lore_remember_metric(processor, svc):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.remember("a thought")
        mock.assert_any_call("lore_remember")


def test_update_increments_lore_update_metric(processor):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.update(memory_feedback=[], link_feedback=[])
        mock.assert_any_call("lore_update")


def test_forget_increments_lore_forget_metric(processor):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.forget(["nonexistent-id"])
        mock.assert_any_call("lore_forget")
