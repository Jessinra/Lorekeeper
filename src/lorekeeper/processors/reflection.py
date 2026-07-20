"""ReflectionProcessor — orchestrates session reflection submission and lookup.

Consolidates the input validation that lived in the ``lore_reflect`` MCP tool
body plus thin read passthroughs for the dashboard reflection/session routes.

Lives in the processors layer (between presentation and domains) and owns
validation, metrics, and commit boundaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import sqlite3

    from lorekeeper.domains.reflection.repository import ReflectionStore
    from lorekeeper.domains.reflection.service import ReflectionService
    from lorekeeper.infra.database import Database
    from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()


class ReflectionProcessor:
    """Orchestrates session reflection submission, processed-session lookup,
    and read-only dashboard access to reflections/sessions.

    Validates input before reaching the domain service, increments metrics,
    and delegates to the reflection service / store.
    """

    def __init__(
        self,
        reflection_service: ReflectionService,
        reflections: ReflectionStore,
        metrics: MetricsStore,
        db: Database,
    ) -> None:
        self._reflection_service = reflection_service
        self._reflections = reflections
        self._metrics = metrics
        self._db = db

    # ── submit_reflection ────────────────────────────────────────────────────

    def submit_reflection(
        self,
        session_id: str,
        summary: str,
        session_date: str | None = None,
        topic: str | None = None,
        task_type: str | None = None,
        what_was_done: str | None = None,
        decisions: str | None = None,
        lessons_learnt: list[str] | None = None,
        good_patterns: list[str] | None = None,
        user_profile_updates: list[str] | None = None,
        factual_discoveries: list[str] | None = None,
        memory_ids: list[str] | None = None,
        auto_insert: bool = True,
    ) -> dict[str, Any]:
        """Validate + submit a session reflection.

        Validates that session_id and summary are non-empty (moved from the
        ``lore_reflect`` MCP tool body), then delegates to the reflection
        service. Metric increment moves here from ``ReflectionService``.

        Returns a dict with reflection_id, session_id, created_at, and
        memories_created.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id is required and must not be empty")
        if not summary or not summary.strip():
            raise ValueError("summary is required and must not be empty")

        self._metrics.increment_metric_safe("lore_reflect")

        return self._reflection_service.submit_reflection(
            session_id=session_id,
            session_date=session_date,
            topic=topic,
            task_type=task_type,
            what_was_done=what_was_done,
            decisions=decisions,
            lessons_learnt=lessons_learnt or [],
            good_patterns=good_patterns or [],
            user_profile_updates=user_profile_updates or [],
            factual_discoveries=factual_discoveries or [],
            summary=summary,
            memory_ids=memory_ids or [],
            auto_insert=auto_insert,
        )

    # ── processed_session_ids ────────────────────────────────────────────────

    def processed_session_ids(self) -> list[str]:
        """Return all session IDs that have been marked as processed."""
        return self._reflection_service.get_processed_session_ids()

    # ── dashboard reads (thin passthroughs — uniformity over cleverness) ────

    def list_reflections(self) -> list[sqlite3.Row]:
        return self._reflections.all_reflections()

    def recent_reflections(self, limit: int = 5) -> list[sqlite3.Row]:
        return self._reflections.recent_reflections(limit)

    def get_reflection(self, reflection_id: str) -> sqlite3.Row | None:
        return self._reflections.get_reflection(reflection_id)

    def sessions_for_reflection(self, reflection_id: str) -> list[sqlite3.Row]:
        return self._reflections.sessions_for_reflection(reflection_id)

    def list_sessions(self, with_content: bool = True) -> list[sqlite3.Row]:
        return (
            self._reflections.sessions_with_content()
            if with_content
            else self._reflections.all_sessions()
        )

    def list_sessions_filtered(
        self,
        q: str | None = None,
        task: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[sqlite3.Row], int]:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 200:
            page_size = 50
        return self._reflections.list_sessions_filtered(
            q=q, task=task, page=page, page_size=page_size
        )

    def count_sessions_by_task(self) -> dict[str, int]:
        return self._reflections.count_sessions_by_task()

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        return self._reflections.get_session(session_id)
