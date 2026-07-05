"""Processor-level tests for ReflectionProcessor — validation, orchestration, metrics.

Validation moved here from the ``lore_reflect`` MCP tool body.  Each test
constructs a ReflectionProcessor with real domain service instances and
validates that:
- input validation fires before any store/engine access
- metrics are incremented correctly
- dashboard read passthroughs return store data
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.processors.reflection import ReflectionProcessor
from tests._helpers import build_app, build_stores
from tests.test_handlers import FakeEngine


@pytest.fixture
def stores(tmp_path):
    s = build_stores(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def app(stores):
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    return build_app(stores, engine, kw, settings)


@pytest.fixture
def processor(app, stores):
    return ReflectionProcessor(
        reflection_service=app.reflection_service,
        reflections=stores.reflections,
        metrics=stores.metrics,
        db=stores.db,
    )


# ── submit_reflection: validation ──────────────────────────────────────────


def test_submit_reflection_empty_session_id_raises(processor):
    with pytest.raises(ValueError, match="session_id is required"):
        processor.submit_reflection(session_id="", summary="a summary")


def test_submit_reflection_whitespace_session_id_raises(processor):
    with pytest.raises(ValueError, match="session_id is required"):
        processor.submit_reflection(session_id="   ", summary="a summary")


def test_submit_reflection_empty_summary_raises(processor):
    with pytest.raises(ValueError, match="summary is required"):
        processor.submit_reflection(session_id="session-1", summary="")


def test_submit_reflection_whitespace_summary_raises(processor):
    with pytest.raises(ValueError, match="summary is required"):
        processor.submit_reflection(session_id="session-1", summary="   ")


# ── submit_reflection: happy path ──────────────────────────────────────────


def test_submit_reflection_valid_call_succeeds(processor):
    result = processor.submit_reflection(session_id="session-1", summary="a summary")
    assert result["session_id"] == "session-1"
    assert "reflection_id" in result


def test_submit_reflection_duplicate_returns_idempotent_noop(processor):
    first = processor.submit_reflection(session_id="session-dup", summary="first")
    second = processor.submit_reflection(session_id="session-dup", summary="second")
    assert second["already_processed"] is True
    assert second["reflection_id"] == first["reflection_id"]


# ── processed_session_ids ──────────────────────────────────────────────────


def test_processed_session_ids_empty_before_any_reflect(processor):
    assert processor.processed_session_ids() == []


def test_processed_session_ids_includes_submitted_session(processor):
    processor.submit_reflection(session_id="session-abc", summary="summary")
    assert "session-abc" in processor.processed_session_ids()


# ── metric increment ────────────────────────────────────────────────────────


def test_submit_reflection_increments_lore_reflect_metric(processor):
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        processor.submit_reflection(session_id="session-1", summary="summary")
        mock.assert_any_call("lore_reflect")


def test_submit_reflection_validation_failure_does_not_increment_metric(processor):
    """Metric must not fire when validation rejects the call before any work."""
    with patch.object(processor._metrics, "increment_metric_safe") as mock:
        with pytest.raises(ValueError):
            processor.submit_reflection(session_id="", summary="summary")
        mock.assert_not_called()


# ── dashboard read passthroughs ────────────────────────────────────────────


def test_list_reflections_empty_returns_empty_list(processor):
    assert processor.list_reflections() == []


def test_list_reflections_returns_submitted_reflection(processor):
    processor.submit_reflection(session_id="session-1", summary="a summary")
    rows = processor.list_reflections()
    assert len(rows) == 1
    assert rows[0]["summary"] == "a summary"


def test_get_reflection_not_found_returns_none(processor):
    assert processor.get_reflection("nonexistent") is None


def test_get_reflection_found_returns_row(processor):
    result = processor.submit_reflection(session_id="session-1", summary="a summary")
    row = processor.get_reflection(result["reflection_id"])
    assert row is not None
    assert row["summary"] == "a summary"


def test_sessions_for_reflection_returns_matching_sessions(processor):
    result = processor.submit_reflection(session_id="session-1", summary="a summary")
    sessions = processor.sessions_for_reflection(result["reflection_id"])
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-1"


def test_list_sessions_empty_returns_empty_list(processor):
    assert processor.list_sessions() == []


def test_list_sessions_with_content_true_returns_submitted_session(processor):
    processor.submit_reflection(session_id="session-1", summary="a summary", topic="topic")
    rows = processor.list_sessions(with_content=True)
    assert len(rows) == 1


def test_list_sessions_with_content_false_returns_all_sessions(processor):
    processor.submit_reflection(session_id="session-1", summary="a summary")
    rows = processor.list_sessions(with_content=False)
    assert len(rows) == 1


def test_get_session_not_found_returns_none(processor):
    assert processor.get_session("nonexistent") is None


def test_get_session_found_returns_row(processor):
    processor.submit_reflection(session_id="session-1", summary="a summary")
    row = processor.get_session("session-1")
    assert row is not None
    assert row["session_id"] == "session-1"
