"""MCPHandler — single struct for all MCP tool request/response formatting.

Thin shim between MCP tool registration and processors.
Only handles serialization and encouragement — no validation, no metrics,
no commit boundaries. Those belong in the processor layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.shared.encouragement import (
    for_forget,
    for_insert,
    for_reflect,
    for_remember,
    for_update,
)

if TYPE_CHECKING:
    from lorekeeper.processors.admin import AdminProcessor
    from lorekeeper.processors.link import LinkProcessor
    from lorekeeper.processors.memory import MemoryProcessor
    from lorekeeper.processors.reflection import ReflectionProcessor
    from lorekeeper.processors.suggestion import SuggestionProcessor


class MCPHandler:
    """Single handler struct owning all five processors for MCP tool dispatch.

    Each method is a thin pass-through that formats request/response and
    applies encouragement wrappers.  Validation, metrics, and commit
    boundaries are owned by the processor layer.
    """

    def __init__(
        self,
        memory_processor: MemoryProcessor,
        suggestion_processor: SuggestionProcessor,
        reflection_processor: ReflectionProcessor,
        link_processor: LinkProcessor,
        admin_processor: AdminProcessor,
    ) -> None:
        self._memp = memory_processor
        self._sugp = suggestion_processor
        self._refp = reflection_processor
        self._lnkp = link_processor
        self._admp = admin_processor

    # ── lore_search ──────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        limit: int | None = None,
        min_score: float = 0.1,
        include_links: bool = True,
        include_deleted: bool = False,
        refine_from: list[str] | None = None,
        format: str = "full",
        ids: list[str] | None = None,
        created_after: str | None = None,
        updated_after: str | None = None,
        sort_by: str = "relevance",
        source_type: str | None = None,
    ) -> dict[str, Any]:
        # TODO: serialize SearchResult → dict with serialize_search_result
        results = self._memp.search(
            query=query, limit=limit, min_score=min_score,
            include_links=include_links, include_deleted=include_deleted,
            refine_from=refine_from, search_format=format, ids=ids,
            created_after=created_after, updated_after=updated_after,
            sort_by=sort_by, source_type=source_type,
        )
        return {"results": results, "total_matched": len(results), "query": query}

    # ── lore_insert ──────────────────────────────────────────────────────────

    def insert(
        self,
        memories: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        result = self._memp.insert(memories=memories, links=links, force=force)
        mem_count = len(memories or [])
        link_count = len(links or [])
        result.update(for_insert(memory_count=mem_count, link_count=link_count))
        return result

    # ── lore_recommend_links ─────────────────────────────────────────────────

    def recommend_links(
        self,
        lore_id: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        # TODO: serialize LinkCandidate → dict with serialize_link_candidate
        candidates = self._sugp.recommend_links(lore_id=lore_id, top_k=top_k)
        return {"candidates": candidates, "count": len(candidates), "source_lore_id": lore_id}

    # ── lore_remember ────────────────────────────────────────────────────────

    def remember(self, thought: str, source_type: str = "observed") -> dict[str, Any]:
        result = self._memp.remember(thought, source_type=source_type)
        result.update(for_remember())
        return result

    # ── lore_update ──────────────────────────────────────────────────────────

    def update(
        self,
        memory_feedback: list[dict[str, Any]] | None = None,
        link_feedback: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        result = self._memp.update(memory_feedback or [], link_feedback or [])
        result.update(for_update())
        return result

    # ── lore_processed_sessions ──────────────────────────────────────────────

    def processed_sessions(self) -> dict[str, Any]:
        return {"session_ids": self._refp.processed_session_ids()}

    # ── lore_reflect ─────────────────────────────────────────────────────────

    def reflect(
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
        result = self._refp.submit_reflection(
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
        result.update(for_reflect(
            already_processed=result.get("already_processed", False)
        ))
        return result

    # ── lore_forget ──────────────────────────────────────────────────────────

    def forget(self, memory_ids: list[str], reason: str = "unspecified") -> dict[str, Any]:
        result = self._memp.forget(memory_ids, reason=reason)
        result.update(for_forget(count=len(memory_ids)))
        return result

    # ── lore_get_suggestions ─────────────────────────────────────────────────

    def get_suggestions(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        # TODO: serialize tuple[list[LinkSuggestion], int] → dict
        items, total = self._sugp.get_pending(limit=limit, min_score=min_score)
        return {"suggestions": items, "count": len(items), "total_pending": total}

    # ── lore_review_suggestion ───────────────────────────────────────────────

    def review_suggestion(
        self,
        suggestion_ids: list[str],
        action: str,
    ) -> dict[str, Any]:
        # TODO: serialize ReviewResult → dict
        result = self._sugp.review(suggestion_ids=suggestion_ids, action=action)
        return {"results": result.results, "accepted": result.accepted,
                "rejected": result.rejected, "skipped": result.skipped,
                "errors": [e["error"] for e in result.errors]}
