"""Regression tests for fixes from PR #111 review (Copilot)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests._helpers import build_stores

# ── MetricsStore.get_metrics — bucket normalization + correct filtering ──────


def test_get_metrics_handles_legacy_iso_buckets(tmp_path):
    """Legacy rows in ISO format (e.g. '2026-05-21T08:08:00') must be
    bucketed to the same hour as canonical '2026-05-21 08:00' rows.
    Verifies counts are summed across both formats (no double-counting,
    no silent drops).
    """
    s = build_stores(tmp_path / "metrics_legacy.db")
    conn = s.db.conn
    now = datetime.now(UTC)
    canonical = now.strftime("%Y-%m-%d %H:00")
    # Same hour, ISO format with extra precision
    iso_legacy = now.strftime("%Y-%m-%dT%H:08:00")

    conn.execute(
        "INSERT INTO api_metrics (minute_bucket, tool_name, count) VALUES (?, ?, ?)",
        (canonical, "lore_search", 3),
    )
    conn.execute(
        "INSERT INTO api_metrics (minute_bucket, tool_name, count) VALUES (?, ?, ?)",
        (iso_legacy, "lore_search", 5),
    )
    conn.commit()

    rows = s.metrics.get_metrics(hours=24)
    # Both should aggregate into ONE bucket
    matching = [r for r in rows if r["tool_name"] == "lore_search"]
    assert len(matching) == 1, f"expected 1 row, got {matching}"
    assert matching[0]["minute_bucket"] == canonical
    assert matching[0]["count"] == 8  # 3 + 5
    s.db.close()


def test_get_metrics_filters_by_normalized_bucket(tmp_path):
    """Rows older than the cutoff must be excluded, including ISO-format
    rows whose raw string would lexicographically pass the canonical cutoff.
    """
    s = build_stores(tmp_path / "metrics_filter.db")
    conn = s.db.conn
    now = datetime.now(UTC)
    # 48 hours ago in ISO format — would lexicographically be >= cutoff if not normalized
    old_iso = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:30:00")
    recent_canonical = now.strftime("%Y-%m-%d %H:00")

    conn.execute(
        "INSERT INTO api_metrics (minute_bucket, tool_name, count) VALUES (?, ?, ?)",
        (old_iso, "lore_search", 1),
    )
    conn.execute(
        "INSERT INTO api_metrics (minute_bucket, tool_name, count) VALUES (?, ?, ?)",
        (recent_canonical, "lore_search", 2),
    )
    conn.commit()

    rows = s.metrics.get_metrics(hours=24)
    # The 48-hour-old ISO row must be excluded
    assert len(rows) == 1
    assert rows[0]["minute_bucket"] == recent_canonical
    assert rows[0]["count"] == 2
    s.db.close()


# ── MemoryStore.update_memory_fields — updated_at not user-settable ──────────


def test_update_memory_fields_ignores_caller_updated_at(tmp_path):
    """Passing `updated_at` in kwargs must NOT override the store's own
    timestamp (which is always set to _now()). This documents that the
    store owns the timestamp.
    """
    s = build_stores(tmp_path / "upd.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="m", title="t", description="d", content="c",
        created_at=ts, updated_at=ts,
    )
    fake_past = "1999-01-01T00:00:00+00:00"
    s.memories.update_memory_fields("m", score=5.0, updated_at=fake_past)

    row = s.memories.get_memory_row("m")
    assert row is not None
    assert row["score"] == 5.0
    # The caller's updated_at must be ignored — _now() wins
    assert row["updated_at"] != fake_past
    # And it must be a recent timestamp (within 60 seconds)
    parsed = datetime.fromisoformat(row["updated_at"])
    assert (datetime.now(UTC) - parsed).total_seconds() < 60
    s.db.close()


# ── LinkStore.insert_link — non-duplicate IntegrityError re-raises ───────────


def test_insert_link_reraises_non_duplicate_integrity_error(tmp_path):
    """If an IntegrityError fires for a reason OTHER than the (source, target,
    relation_type) unique constraint (e.g. PRIMARY KEY collision on `id`),
    the error must propagate — not silently return an unrelated MemoryLink.
    """
    s = build_stores(tmp_path / "link_collide.db")
    ts = "2026-01-01T00:00:00+00:00"
    for i in ("a", "b", "c", "d"):
        s.memories.upsert_memory_row(
            id=i, title=f"m-{i}", description="d", content="c",
            created_at=ts, updated_at=ts,
        )

    # First link with explicit id
    fixed_id = str(uuid.uuid4())
    s.links.insert_link("a", "b", "references", "r", id=fixed_id)

    # Now insert a DIFFERENT logical link (different source/target) but with
    # the same `id` — this triggers a PRIMARY KEY IntegrityError, NOT the
    # unique-pair duplicate path. The fix must re-raise this.
    with pytest.raises(sqlite3.IntegrityError):
        s.links.insert_link("c", "d", "references", "r2", id=fixed_id)

    s.db.close()


def test_insert_link_duplicate_pair_returns_existing(tmp_path):
    """The intentional swallow case: re-inserting the exact same
    (source, target, relation_type) returns the existing link unchanged.
    """
    s = build_stores(tmp_path / "link_dup.db")
    ts = "2026-01-01T00:00:00+00:00"
    for i in ("a", "b"):
        s.memories.upsert_memory_row(
            id=i, title=f"m-{i}", description="d", content="c",
            created_at=ts, updated_at=ts,
        )

    first = s.links.insert_link("a", "b", "references", "first")
    second = s.links.insert_link("a", "b", "references", "second attempt")
    # Should return the EXISTING link (same id), not insert a new one
    assert second.id == first.id
    assert second.reason == "first"  # original reason preserved
    s.db.close()


# ── orchestrator._increment_metric — logs but does not raise ─────────────────

def test_increment_metric_logs_on_sqlite_failure_and_does_not_raise(tmp_path):
    """If the metrics store raises sqlite3.Error, the orchestrator must
    catch it, log a warning with exc_info, and not propagate the failure.

    Uses a mocked metrics store + spied logger to deterministically verify
    both behaviors (catch + log). Avoids depending on structlog→caplog
    routing, which is configuration-dependent.
    """
    from unittest.mock import MagicMock, patch

    from lorekeeper.config import Settings
    from lorekeeper.services.keyword_index import KeywordIndex
    from tests._helpers import build_service

    class _NoopEngine:
        def probe_score_scale(self): pass
        def add(self, *a, **kw): return ""
        def search(self, *a, **kw): return []
        def get_all(self): return []
        def normalize_score(self, x): return x
        def find_vector_id(self, x): return None

    s = build_stores(tmp_path / "metric_boom.db")
    svc = build_service(s, _NoopEngine(), KeywordIndex(), Settings())

    # Replace metrics.increment_metric with a function that raises sqlite3.Error.
    boom = MagicMock(side_effect=sqlite3.OperationalError("simulated DB locked"))
    svc.metrics.increment_metric = boom  # type: ignore[method-assign]

    # Spy on the module-level structlog logger used by orchestrator.
    with patch("lorekeeper.services.orchestrator.log") as mock_log:
        # Must NOT raise
        svc._increment_metric("test_tool")

    # The metrics store was called once
    boom.assert_called_once_with("test_tool")

    # A warning was logged with the expected event name + exc_info
    mock_log.warning.assert_called_once()
    call_args = mock_log.warning.call_args
    assert call_args.args[0] == "metric_increment_failed"
    assert call_args.kwargs.get("tool_name") == "test_tool"
    assert call_args.kwargs.get("exc_info") is True

    s.db.close()
