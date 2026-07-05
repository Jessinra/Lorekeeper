"""MCP tool registration — extracts all @mcp.tool() definitions from server.py.

Receives an MCPHandler instance and registers every tool with the FastMCP
server.  Each tool is a thin async function that:
1. Logs the call
2. Delegates to the handler struct (format only, no validation)
3. Catches + re-raises exceptions with structured logging

This file replaces the 9 ``@mcp.tool()`` decorated functions that previously
lived in ``server.py``.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastmcp import FastMCP

from lorekeeper.api.mcp.handlers import MCPHandler

log = structlog.get_logger()


def register_mcp_tools(mcp: FastMCP, handler: MCPHandler) -> None:
    """Register all MCP tools on the given FastMCP server.

    Called once at startup from ``server.py`` after the composition root has
    wired all dependencies and created the ``MCPHandler``.
    """

    # ── lore_search ──────────────────────────────────────────────────────────

    @mcp.tool(name="lore_search")
    async def lore_search(
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
        """Search memories by semantic + keyword query, or bulk-fetch by ID.

        When ``ids`` is provided, skips the vector/BM25 pipeline entirely and does
        a direct SQL lookup by lore_id. ``query`` is ignored in that path.
        """
        try:
            return handler.search(
                query=query, limit=limit, min_score=min_score,
                include_links=include_links, include_deleted=include_deleted,
                refine_from=refine_from, format=format, ids=ids,
                created_after=created_after, updated_after=updated_after,
                sort_by=sort_by, source_type=source_type,
            )
        except Exception:
            log.exception("lore_search_failed", query=query)
            raise

    # ── lore_insert ──────────────────────────────────────────────────────────

    @mcp.tool(name="lore_insert")
    async def lore_insert(
        memories: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Insert memories and/or links into the store."""
        try:
            return handler.insert(memories=memories, links=links, force=force)
        except Exception:
            log.exception("lore_insert_failed", memory_count=len(memories or []))
            raise

    # ── lore_recommend_links ─────────────────────────────────────────────────

    @mcp.tool(
        name="lore_recommend_links",
        description=(
            "Suggest link candidates between a memory and related memories. "
            "Returns ranked candidates with per-signal scores. "
            "Does NOT write any links — call lore_insert with links=[] to confirm."
        ),
    )
    async def lore_recommend_links(
        lore_id: str,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        try:
            return handler.recommend_links(lore_id=lore_id, top_k=top_k)
        except Exception:
            log.exception("lore_recommend_links_failed", lore_id=lore_id)
            raise

    # ── lore_remember ────────────────────────────────────────────────────────

    @mcp.tool(name="lore_remember")
    async def lore_remember(
        thought: str,
        source_type: str = "observed",
    ) -> dict[str, Any]:
        """Capture a thought instantly — one fact, one call."""
        try:
            return handler.remember(thought, source_type=source_type)
        except Exception:
            log.exception("lore_remember_failed", thought=thought[:80])
            raise

    # ── lore_update ──────────────────────────────────────────────────────────

    @mcp.tool(name="lore_update")
    async def lore_update(
        memory_feedback: list[dict[str, Any]] | None = None,
        link_feedback: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Rate memories and links after using them. Drives the quality signal loop."""
        try:
            return handler.update(
                memory_feedback=memory_feedback, link_feedback=link_feedback,
            )
        except Exception:
            log.exception("lore_update_failed")
            raise

    # ── lore_processed_sessions ──────────────────────────────────────────────

    @mcp.tool(name="lore_processed_sessions")
    async def lore_processed_sessions() -> dict[str, Any]:
        """Return all session IDs that have been marked as processed via lore_reflect."""
        try:
            return handler.processed_sessions()
        except Exception:
            log.exception("lore_processed_sessions_failed")
            raise

    # ── lore_reflect ─────────────────────────────────────────────────────────

    @mcp.tool(name="lore_reflect")
    async def lore_reflect(
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
        """Reflect on a completed session — save what you learned."""
        try:
            return handler.reflect(
                session_id=session_id, summary=summary,
                session_date=session_date, topic=topic, task_type=task_type,
                what_was_done=what_was_done, decisions=decisions,
                lessons_learnt=lessons_learnt, good_patterns=good_patterns,
                user_profile_updates=user_profile_updates,
                factual_discoveries=factual_discoveries,
                memory_ids=memory_ids, auto_insert=auto_insert,
            )
        except Exception:
            log.exception("lore_reflect_failed", session_id=session_id)
            raise

    # ── lore_forget ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def lore_forget(
        memory_ids: list[str],
        reason: str = "unspecified",
    ) -> dict[str, Any]:
        """Soft-delete one or more memories by ID."""
        try:
            if not memory_ids:
                raise ValueError("memory_ids must not be empty")
            return handler.forget(memory_ids, reason=reason)
        except Exception:
            log.exception("lore_forget_failed")
            raise

    # ── lore_get_suggestions ─────────────────────────────────────────────────

    @mcp.tool()
    async def lore_get_suggestions(
        limit: int = 20,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """Retrieve pending link suggestions for review, sorted by quality score."""
        try:
            return handler.get_suggestions(limit=limit, min_score=min_score)
        except Exception:
            log.exception("lore_get_suggestions_failed")
            raise

    # ── lore_review_suggestion ───────────────────────────────────────────────

    @mcp.tool()
    async def lore_review_suggestion(
        suggestion_ids: list[str],
        action: str,
    ) -> dict[str, Any]:
        """Accept or reject one or more link suggestions in a single call."""
        try:
            return handler.review_suggestion(
                suggestion_ids=suggestion_ids, action=action,
            )
        except Exception:
            log.exception("lore_review_suggestion_failed")
            raise
