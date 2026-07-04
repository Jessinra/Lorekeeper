"""AdminProcessor — cross-cutting operational use cases: metrics, config, sweep control.

Consolidates dashboard-only operational endpoints that don't belong to any
single domain slice. Lives in the processors layer (between presentation and
domains) and owns validation, metrics-bucket assembly, and commit boundaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
    from lorekeeper.infra.database import Database
    from lorekeeper.infra.settings import Settings
    from lorekeeper.platform.config.repository import ConfigStore
    from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()

_READONLY_KEYS = {"data_dir", "embedding_model"}


class AdminProcessor:
    """Orchestrates metrics reads, config get/set, and sweep-scheduler control.

    Single home for the operational routes that used to reach into
    ``get_service()`` (settings/config/metrics) and ``get_suggestions_store()``
    directly from the dashboard layer.
    """

    def __init__(
        self,
        config: ConfigStore,
        metrics: MetricsStore,
        suggestions: LinkSuggestionStore,
        settings: Settings,
        db: Database,
    ) -> None:
        self._config = config
        self._metrics = metrics
        self._suggestions = suggestions
        self._settings = settings
        self._db = db

    # ── metrics ──────────────────────────────────────────────────────────────

    def get_metrics(self, hours: int = 24) -> dict[str, Any]:
        """Return per-minute API call counts bucketed by tool, for the last `hours` hours."""
        rows = self._metrics.get_metrics(hours=hours)
        buckets: list[str] = []
        tools: set[str] = set()
        data: dict[str, dict[str, int]] = {}
        for row in rows:
            bucket = row["minute_bucket"]
            tool = row["tool_name"]
            count = row["count"]
            tools.add(tool)
            if bucket not in data:
                data[bucket] = {}
                buckets.append(bucket)
            data[bucket][tool] = count
        return {
            "hours": hours,
            "buckets": buckets,
            "tools": sorted(tools),
            "data": data,
        }

    # ── config ───────────────────────────────────────────────────────────────

    def get_config(self) -> dict[str, Any]:
        """Return current effective settings plus the set of overridden keys."""
        s = self._settings
        overridden_keys = set(self._config.get_overrides().keys())
        return {
            "data_dir": str(s.data_dir),
            "embedding_model": s.embedding_model,
            "duplicate_threshold": s.duplicate_threshold,
            "w_semantic": s.w_semantic,
            "w_keyword": s.w_keyword,
            "w_memory": s.w_memory,
            "w_usage": s.w_usage,
            "score_bump_up": s.score_bump_up,
            "score_bump_down": s.score_bump_down,
            "score_min": s.score_min,
            "score_max": s.score_max,
            "soft_delete_confidence_threshold": s.soft_delete_confidence_threshold,
            "confidence_window_size": s.confidence_window_size,
            "search_limit": s.search_limit,
            "max_links_per_memory": s.max_links_per_memory,
            "usage_normalisation_cap": s.usage_normalisation_cap,
            "decay_lambda": s.decay_lambda,
            "new_memory_default_score": s.new_memory_default_score,
            "auto_link_enabled": s.auto_link_enabled,
            "auto_link_k": s.auto_link_k,
            "auto_link_threshold": s.auto_link_threshold,
            "_overridden_keys": sorted(overridden_keys),
        }

    def set_config(self, key: str, value: Any) -> None:
        """Validate, apply, and persist a single config override.

        Read-only keys (``data_dir``, ``embedding_model``) are silently
        skipped — they are not part of ``ConfigUpdate`` today, but the guard
        stays in case a future field is added there.  Type validation is
        against the *current* value on ``Settings`` — mirrors the previous
        Pydantic-annotation-derived check byte for byte, since every
        ``ConfigUpdate`` field name maps 1:1 to a ``Settings`` attribute of
        the same type.

        Raises:
            ValueError: If ``key`` is unknown on ``Settings``, or ``value``'s
                type does not match the current attribute's type.
        """
        if key in _READONLY_KEYS:
            return
        if not hasattr(self._settings, key):
            raise ValueError(f"Unknown config key: {key!r}")

        expected = type(getattr(self._settings, key))
        if not isinstance(value, expected):
            raise ValueError(
                f"Config '{key}' expects {expected.__name__}, got {type(value).__name__}"
            )

        setattr(self._settings, key, value)
        self._config.set_override(key, value)
        self._db.commit()

    # ── sweep control ────────────────────────────────────────────────────────

    def trigger_sweep(self) -> None:
        """Trigger the sweep scheduler immediately by resetting its timer."""
        self._config.set_override("sweep_next_run_at", datetime.now(UTC).isoformat())
        self._db.commit()

    def sweep_status(self) -> dict[str, str | None]:
        """Return last and next sweep run timestamps.

        Falls back to the newest suggestion's ``created_at`` for
        ``last_run_at`` when no sweep has recorded a run yet — that's the
        most recent time the sweep produced output.
        """
        overrides = self._config.get_overrides()
        last_run = overrides.get("sweep_last_run_at")
        next_run = overrides.get("sweep_next_run_at")

        if not last_run:
            last_run = self._suggestions.get_newest_suggestion_created_at()

        return {
            "last_run_at": str(last_run) if last_run else None,
            "next_run_at": str(next_run) if next_run else None,
        }
