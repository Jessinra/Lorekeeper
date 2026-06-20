"""Generic periodic job runner — daemon thread, no external cron needed.

Each job persists its next-run timestamp in ``config_overrides`` under the key
``{name}_next_run_at``, so the schedule survives server restarts.

Adding a new periodic job in ``server.py``::

    from lorekeeper.scheduler import PeriodicJob

    PeriodicJob(config, job_fn, "sweep",
                interval_hours=12, poll_seconds=300).start()

    PeriodicJob(config, job_fn, "reflect",
                interval_hours=6, poll_seconds=300).start()

``config`` is a ``ConfigStore`` instance and ``job_fn`` is a zero-arg callable
returning a stats dict. Each job gets its own daemon thread. Exceptions are
caught and logged — the server never crashes from a job failure.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from lorekeeper.services.config_store import ConfigStore

log = structlog.get_logger()


class PeriodicJob:
    """Daemon thread that runs a callable on a configurable schedule.

    Args:
        config: ConfigStore — used for timer persistence via ``config_overrides``.
        job_fn: Zero-argument callable returning a stats dict. Called when
            the timer fires.
        name: Short identifier used for the timer key in ``config_overrides``
            (``{name}_next_run_at``) and log messages.
        interval_hours: Time between job runs (default 12).
        poll_seconds: How often to check the timer (default 300 / 5 min).
    """

    def __init__(
        self,
        config: ConfigStore,
        job_fn: Callable[[], dict[str, Any]],
        name: str,
        interval_hours: int = 12,
        poll_seconds: int = 300,
    ) -> None:
        self._config = config
        self._job_fn = job_fn
        self._name = name
        self._interval = timedelta(hours=interval_hours)
        self._poll = poll_seconds
        self._timer_key = f"{name}_next_run_at"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.wait(self._poll):
            try:
                overrides = self._config.get_overrides()
                raw = overrides.get(self._timer_key)
                if raw is not None:
                    next_run = datetime.fromisoformat(str(raw))
                    if datetime.now(UTC) < next_run:
                        continue  # Not time yet

                # First run (no key) or timer elapsed
                stats = self._job_fn()
                next_time = datetime.now(UTC) + self._interval
                self._config.set_override(self._timer_key, next_time.isoformat())
                log.info("periodic_job_completed", name=self._name, stats=stats)
            except Exception:
                log.exception("periodic_job_failed", name=self._name)
