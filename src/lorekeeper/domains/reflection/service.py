"""Reflection domain service — session reflection submission.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()


class ReflectionService:
    """Session reflection submission and processed-session lookup."""

    def __init__(self, svc: MemoryService) -> None:
        self._svc = svc

    def submit_reflection(
        self,
        session_id: str,
        session_date: str | None,
        topic: str | None,
        task_type: str | None,
        what_was_done: str | None,
        decisions: str | None,
        lessons_learnt: list[str],
        good_patterns: list[str],
        user_profile_updates: list[str],
        factual_discoveries: list[str],
        summary: str,
        memory_ids: list[str],
        auto_insert: bool = True,
    ) -> dict[str, Any]:
        svc = self._svc
        svc._increment_metric("lore_reflect")

        # Guard: if this session has already been processed, return idempotent no-op.
        # Root cause confirmed (LKPR-1): without this check, every duplicate call inserts a
        # fresh orphaned reflection row and overwrites the session's reflection_id pointer.
        existing_session = svc.reflections.get_session(session_id)
        if existing_session is not None:
            log.info(
                "reflection_already_processed",
                session_id=session_id,
                existing_reflection_id=existing_session["reflection_id"],
            )
            return {
                "reflection_id": existing_session["reflection_id"],
                "session_id": session_id,
                "created_at": existing_session["reviewed_at"],
                "already_processed": True,
                "memories_created": [],
            }

        reflection_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        def _bullets(items: list[str]) -> str | None:
            return "\n".join(f"- {item}" for item in items) if items else None

        svc.reflections.insert_reflection(
            id=reflection_id,
            created_at=now,
            session_count=1,
            lessons_learnt=_bullets(lessons_learnt) or "",
            good_patterns=_bullets(good_patterns),
            user_profile_updates=_bullets(user_profile_updates),
            factual_discoveries=_bullets(factual_discoveries),
            summary=summary,
            memory_ids=json.dumps(memory_ids) if memory_ids else None,
        )

        svc.reflections.upsert_session(
            session_id=session_id,
            reviewed_at=now,
            session_date=session_date,
            topic=topic,
            task_type=task_type,
            reflection_id=reflection_id,
            what_was_done=what_was_done,
            decisions=decisions,
            lessons_learnt=_bullets(lessons_learnt),
            good_patterns=_bullets(good_patterns),
            user_profile=_bullets(user_profile_updates),
            discoveries=_bullets(factual_discoveries),
        )

        log.info("reflection_submitted", reflection_id=reflection_id, session_id=session_id)
        svc._conn.commit()  # commit reflection + session rows before auto-insert

        # Auto-insert factual_discoveries and lessons_learnt as memories (best-effort)
        memories_created: list[dict[str, Any]] = []
        if auto_insert:
            _auto_items: list[tuple[list[str], str, float]] = [
                (factual_discoveries, "discovered_in", 7.0),
                (lessons_learnt, "learned_in", 8.0),
            ]
            new_inserts = 0
            skipped = 0
            for items_list, relation, score in _auto_items:
                for text in items_list:
                    try:
                        title = svc._extract_title(text)
                        result = svc.memory_write_service.insert_one_memory(
                            {"title": title, "description": title, "content": text, "score": score},
                            force=False,
                        )
                        if "duplicate" in result:
                            mem_id = result["duplicate"]["existing_memory"]["id"]
                            status = "duplicate"
                        elif "inserted" in result:
                            mem_id = result["inserted"]["id"]
                            status = "inserted"
                            new_inserts += 1
                        else:
                            raise ValueError(
                                f"unexpected insert_one_memory result shape: {result!r}"
                            )
                        memories_created.append(
                            {"id": mem_id, "title": title, "relation": relation, "status": status}
                        )
                    except Exception:
                        skipped += 1
                        log.warning(
                            "reflect_auto_insert_failed",
                            text=str(text)[:80],
                            relation=relation,
                            exc_info=True,
                        )

            if skipped:
                log.info(
                    "reflect_auto_insert_partial",
                    skipped=skipped,
                    inserted=new_inserts,
                    session_id=session_id,
                )
            if new_inserts:
                svc._rebuild_kw()
                svc._conn.commit()

        return {
            "reflection_id": reflection_id,
            "session_id": session_id,
            "created_at": now,
            "memories_created": memories_created,
        }

    def get_processed_session_ids(self) -> list[str]:
        svc = self._svc
        svc._increment_metric("lore_processed_sessions")
        return list(svc.reflections.all_processed_session_ids())
