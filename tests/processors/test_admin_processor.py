"""Processor-level tests for AdminProcessor — metrics, config, sweep control.

Consolidates the operational logic previously inline in
``dashboard/routes/{metrics,config,suggestions}.py``. Each test constructs an
AdminProcessor with real store instances and validates that:
- config set/get round-trips through the store + Settings object
- type validation matches the current attribute's type
- read-only keys are silently skipped
- trigger_sweep writes the override and commits
- sweep_status falls back to the newest suggestion's created_at
"""

from __future__ import annotations

import pytest

from lorekeeper.infra.settings import Settings
from lorekeeper.processors.admin import AdminProcessor
from tests._helpers import build_stores


@pytest.fixture
def stores(tmp_path):
    s = build_stores(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def processor(stores, settings):
    return AdminProcessor(
        config=stores.config,
        metrics=stores.metrics,
        suggestions=stores.suggestions,
        settings=settings,
        db=stores.db,
    )


# ── get_metrics ──────────────────────────────────────────────────────────────


def test_get_metrics_empty_returns_zero_buckets(processor):
    result = processor.get_metrics(hours=24)
    assert result["hours"] == 24
    assert result["buckets"] == []
    assert result["tools"] == []
    assert result["data"] == {}


def test_get_metrics_bucketed_by_tool(processor, stores):
    stores.metrics.increment_metric_safe("lore_search")
    stores.metrics.increment_metric_safe("lore_search")
    stores.metrics.increment_metric_safe("lore_insert")

    result = processor.get_metrics(hours=24)
    assert result["tools"] == ["lore_insert", "lore_search"]
    assert len(result["buckets"]) == 1
    bucket = result["buckets"][0]
    assert result["data"][bucket]["lore_search"] == 2
    assert result["data"][bucket]["lore_insert"] == 1


# ── get_config ───────────────────────────────────────────────────────────────


def test_get_config_returns_settings_and_overrides(processor):
    result = processor.get_config()
    assert "data_dir" in result
    assert "w_semantic" in result
    assert result["_overridden_keys"] == []


def test_get_config_lists_overridden_keys(processor, settings):
    processor.set_config("w_semantic", 0.8)
    result = processor.get_config()
    assert result["_overridden_keys"] == ["w_semantic"]
    assert result["w_semantic"] == 0.8


# ── set_config: validation ──────────────────────────────────────────────────


def test_set_config_readonly_key_is_silently_skipped(processor, settings):
    original = str(settings.data_dir)
    processor.set_config("data_dir", "/tmp/should-not-apply")
    assert str(settings.data_dir) == original


def test_set_config_unknown_key_raises_value_error(processor):
    with pytest.raises(ValueError, match="Unknown config key"):
        processor.set_config("not_a_real_setting", 1)


def test_set_config_wrong_type_raises_value_error(processor):
    with pytest.raises(ValueError, match="expects float, got str"):
        processor.set_config("w_semantic", "banana")


def test_set_config_int_field_accepts_int(processor, settings):
    """search_limit is int-typed; bool is a subclass of int in Python so
    isinstance(True, int) is True — same quirk as the pre-refactor Pydantic
    check this replaces. Not tightened here (pure refactor, no behavior change)."""
    processor.set_config("search_limit", 10)
    assert settings.search_limit == 10


# ── set_config: happy path + persistence ────────────────────────────────────


def test_set_config_updates_settings_attribute(processor, settings):
    processor.set_config("w_semantic", 0.8)
    assert settings.w_semantic == 0.8


def test_set_config_persists_override(processor, stores):
    processor.set_config("w_semantic", 0.8)
    overrides = stores.config.get_overrides()
    assert overrides["w_semantic"] == 0.8


# ── trigger_sweep ────────────────────────────────────────────────────────────


def test_trigger_sweep_sets_override(processor, stores):
    processor.trigger_sweep()
    overrides = stores.config.get_overrides()
    assert "sweep_next_run_at" in overrides


# ── sweep_status ─────────────────────────────────────────────────────────────


def test_sweep_status_no_data_returns_none(processor):
    result = processor.sweep_status()
    assert result["last_run_at"] is None
    assert result["next_run_at"] is None


def test_sweep_status_uses_override_when_present(processor, stores):
    stores.config.set_override("sweep_last_run_at", "2026-01-01T00:00:00+00:00")
    stores.config.commit()
    result = processor.sweep_status()
    assert result["last_run_at"] == "2026-01-01T00:00:00+00:00"


def test_sweep_status_falls_back_to_newest_suggestion(processor, stores):
    now = "2026-01-01T00:00:00+00:00"
    stores.memories.upsert_memory_row(
        "mem-a", "title a", "desc", "content", now, now
    )
    stores.memories.upsert_memory_row(
        "mem-b", "title b", "desc", "content", now, now
    )
    stores.suggestions.insert_suggestion(
        source_memory_id="mem-a",
        target_memory_id="mem-b",
        source_title="title a",
        target_title="title b",
        weighted_score=0.9,
    )
    stores.db.commit()

    result = processor.sweep_status()
    assert result["last_run_at"] is not None


# ── get_tool_calls ────────────────────────────────────────────────────────────


def test_get_tool_calls_empty_returns_zero_totals(processor):
    result = processor.get_tool_calls(hours=168)
    assert result["hours"] == 168
    assert result["timezone"] == "UTC"
    assert result["total_calls"] == 0
    assert result["avg_calls_per_day"] == 0.0
    assert result["tools"] == []
    assert result["tool_totals"] == {}
    assert len(result["days"]) == 8  # 168h = 7 full days + partial day boundary


def test_get_tool_calls_aggregates_by_day_and_hour(processor, stores):
    # Insert two metric rows in the same day/hour
    stores.metrics.increment_metric("lore_search")
    stores.metrics.increment_metric("lore_search")
    stores.metrics.increment_metric("lore_insert")
    stores.db.commit()

    result = processor.get_tool_calls(hours=168)
    assert result["total_calls"] == 3
    assert "lore_search" in result["tools"]
    assert "lore_insert" in result["tools"]
    assert result["tool_totals"]["lore_search"] == 2
    assert result["tool_totals"]["lore_insert"] == 1


def test_get_tool_calls_heatmap_cell_has_total_key(processor, stores):
    stores.metrics.increment_metric("lore_reflect")
    stores.db.commit()

    result = processor.get_tool_calls(hours=168)
    # Find the cell that has data
    found = False
    for day in result["days"]:
        for _hour_str, cell in result["heatmap"][day].items():
            assert "total" in cell
            assert cell["total"] == sum(v for k, v in cell.items() if k != "total")
            found = True
    assert found, "Expected at least one non-empty heatmap cell"


def test_get_tool_calls_all_7_days_present(processor):
    result = processor.get_tool_calls(hours=168)
    # Must have at least 7 day entries (boundary condition can produce 8)
    assert len(result["days"]) >= 7
    # Days must be sorted oldest-first
    assert result["days"] == sorted(result["days"])


def test_get_tool_calls_clamps_hours_below_1(processor):
    """hours < 1 is clamped to 1 — never crashes, always returns valid shape."""
    result = processor.get_tool_calls(hours=0)
    assert result["hours"] == 1


def test_get_tool_calls_clamps_hours_above_2160(processor):
    """hours > 2160 (90d) is clamped to 2160."""
    result = processor.get_tool_calls(hours=99999)
    assert result["hours"] == 2160


def test_get_tool_calls_avg_excludes_partial_today(processor, stores):
    """avg_calls_per_day denominator must be completed days, not total days.

    A 168h window spans ~8 day buckets (7 complete + current partial day).
    If we have 7 total_calls and the denominator were 8, avg would be 0.9.
    With the partial day excluded the denominator is 7, giving avg == 1.0.
    """
    for _ in range(7):
        stores.metrics.increment_metric("lore_search")
    stores.db.commit()

    result = processor.get_tool_calls(hours=168)
    # total_calls == 7; completed days == 7 → avg == 1.0 (not 0.9 from /8)
    assert result["total_calls"] == 7
    # avg should be total / completed_days; denominator is NOT len(days)
    from datetime import UTC, datetime
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    completed = [d for d in result["days"] if d != today]
    expected = round(7 / max(len(completed), 1), 1)
    assert result["avg_calls_per_day"] == expected
