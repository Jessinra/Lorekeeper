"""Reflection + Session CRUD — extracted from LinkStore as part of LKPR-51.

Reflections and sessions share an FK (`sessions.reflection_id → reflections.id`)
and were added together for the loop infrastructure, so they share one store
to preserve transactional locality.
"""

from __future__ import annotations

import sqlite3
from typing import cast

from lorekeeper.infra.database import Database

_SESSION_UPSERT_SQL = """
    INSERT INTO sessions
      (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
       transcript, what_was_done, decisions, lessons_learnt,
       good_patterns, user_profile, discoveries)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(session_id) DO UPDATE SET
      session_date=COALESCE(excluded.session_date, session_date),
      topic=COALESCE(excluded.topic, topic),
      task_type=COALESCE(excluded.task_type, task_type),
      reviewed_at=excluded.reviewed_at,
      reflection_id=COALESCE(excluded.reflection_id, reflection_id),
      transcript=COALESCE(excluded.transcript, transcript),
      what_was_done=COALESCE(excluded.what_was_done, what_was_done),
      decisions=COALESCE(excluded.decisions, decisions),
      lessons_learnt=COALESCE(excluded.lessons_learnt, lessons_learnt),
      good_patterns=COALESCE(excluded.good_patterns, good_patterns),
      user_profile=COALESCE(excluded.user_profile, user_profile),
      discoveries=COALESCE(excluded.discoveries, discoveries)
"""


class ReflectionStore:
    """CRUD for `reflections` and `sessions` tables."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    # ── Reflections ───────────────────────────────────────────────────────────

    def insert_reflection(
        self,
        id: str,
        created_at: str,
        session_count: int,
        lessons_learnt: str,
        summary: str,
        good_patterns: str | None = None,
        user_profile_updates: str | None = None,
        factual_discoveries: str | None = None,
        memory_ids: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO reflections
              (id, created_at, session_count, lessons_learnt, good_patterns,
               user_profile_updates, factual_discoveries, summary, memory_ids)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (id, created_at, session_count, lessons_learnt, good_patterns,
             user_profile_updates, factual_discoveries, summary, memory_ids),
        )

    def get_reflection(self, reflection_id: str) -> sqlite3.Row | None:
        return cast(sqlite3.Row | None, self._conn.execute(
            "SELECT * FROM reflections WHERE id = ?", (reflection_id,)
        ).fetchone())

    def all_reflections(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM reflections ORDER BY created_at DESC"
        ).fetchall()

    # ── Sessions ──────────────────────────────────────────────────────────────

    def upsert_session(
        self,
        session_id: str,
        reviewed_at: str,
        session_date: str | None = None,
        topic: str | None = None,
        task_type: str | None = None,
        reflection_id: str | None = None,
        transcript: str | None = None,
        what_was_done: str | None = None,
        decisions: str | None = None,
        lessons_learnt: str | None = None,
        good_patterns: str | None = None,
        user_profile: str | None = None,
        discoveries: str | None = None,
    ) -> None:
        self._conn.execute(
            _SESSION_UPSERT_SQL,
            (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
             transcript, what_was_done, decisions, lessons_learnt,
             good_patterns, user_profile, discoveries),
        )

    def upsert_sessions_bulk(self, rows: list[tuple[str | None, ...]]) -> None:
        """Insert/update multiple sessions in a single transaction.

        Each tuple: (session_id, session_date, topic, task_type, reviewed_at,
                     reflection_id, transcript, what_was_done, decisions,
                     lessons_learnt, good_patterns, user_profile, discoveries)
        """
        self._conn.executemany(_SESSION_UPSERT_SQL, rows)

    def all_processed_session_ids(self) -> set[str]:
        """Return all session IDs marked processed. Used by loop skill scripts."""
        rows = self._conn.execute("SELECT session_id FROM sessions").fetchall()
        return {r["session_id"] for r in rows}

    def all_sessions(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions ORDER BY reviewed_at DESC"
        ).fetchall()

    def sessions_with_content(self) -> list[sqlite3.Row]:
        """Sessions that have a topic (i.e. were matched to a session log)."""
        return self._conn.execute(
            "SELECT * FROM sessions WHERE topic IS NOT NULL "
            "ORDER BY session_date DESC, topic"
        ).fetchall()

    def list_sessions_filtered(
        self,
        q: str | None = None,
        task: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[sqlite3.Row], int]:
        """Return (rows, total_count) with optional search + task-type filter."""
        conditions: list[str] = []
        params: list[str | int] = []

        if q:
            conditions.append(
                "(INSTR(LOWER(session_id), LOWER(?)) > 0"
                " OR INSTR(LOWER(COALESCE(topic,'')), LOWER(?)) > 0)"
            )
            params.extend([q, q])
        if task:
            conditions.append("task_type = ?")
            params.append(task)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        count_row = self._conn.execute(
            f"SELECT COUNT(*) FROM sessions {where}", params
        ).fetchone()
        total: int = count_row[0]

        offset = (page - 1) * page_size
        rows = self._conn.execute(
            f"SELECT * FROM sessions {where}"
            " ORDER BY session_date DESC, reviewed_at DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()
        return rows, total

    def count_sessions_by_task(self) -> dict[str, int]:
        """Return a mapping of task_type → count for all sessions."""
        rows = self._conn.execute(
            "SELECT task_type, COUNT(*) as cnt FROM sessions GROUP BY task_type"
        ).fetchall()
        return {r["task_type"]: r["cnt"] for r in rows if r["task_type"]}

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        return cast(sqlite3.Row | None, self._conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone())

    def sessions_for_reflection(self, reflection_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions WHERE reflection_id = ? "
            "ORDER BY session_date, session_id",
            (reflection_id,),
        ).fetchall()
