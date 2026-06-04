import structlog
from fastmcp import FastMCP
from pydantic import ValidationError

from lorekeeper.config import Settings
from lorekeeper.serializers import serialize_search_result, serialize_search_result_title
from lorekeeper.services.config_store import ConfigStore
from lorekeeper.services.database import Database
from lorekeeper.services.engine_factory import build_engine
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.orchestrator import MemoryService
from lorekeeper.services.reflection_store import ReflectionStore

log = structlog.get_logger()
mcp: FastMCP = FastMCP(name="lorekeeper-mcp-server")
_svc: MemoryService | None = None


def get_service() -> MemoryService:
    global _svc
    if _svc is None:
        raise RuntimeError("MemoryService not initialised — call init_service() first")
    return _svc


def init_service(settings: Settings | None = None) -> MemoryService:
    global _svc
    s = settings or Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)

    log.info("init_lorekeeper", data_dir=str(s.data_dir), vector_store=s.vector_store)
    engine = build_engine(s.vector_store, s.chroma_path, s.lancedb_path, s.embedding_model)
    engine.probe_score_scale()

    # Shared SQLite connection + versioned migrations
    db = Database(s.sqlite_path)
    db.migrate()

    # Focused stores all share the same Database connection
    memories = MemoryStore(db)
    links = LinkStore(db)
    reflections = ReflectionStore(db)
    metrics = MetricsStore(db)
    config = ConfigStore(db)

    # Apply persisted config overrides (dashboard changes that survived restart)
    overrides = config.get_overrides()
    for key, value in overrides.items():
        try:
            setattr(s, key, value)
            getattr(s, key)  # confirm it reads back (catches silent failures)
        except (ValueError, TypeError, AttributeError, ValidationError) as e:
            log.warning("config_override_skipped", key=key, value=value, error=str(e))
    if overrides:
        log.info("config_overrides_loaded", keys=list(overrides))

    kw = KeywordIndex()

    svc = MemoryService(engine, memories, links, reflections, metrics, config, kw, s)
    # Bootstrap BM25 from existing memories
    all_mems = list(svc._all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    log.info("bm25_rebuilt", count=len(all_mems))

    _svc = svc
    return svc


# ---------------------------------------------------------------------------
# MCP handler helpers — input sanitization and output formatting for MCP tools
# ---------------------------------------------------------------------------

_VALID_SEARCH_FORMATS = {"full", "title"}


def _handle_search(
    svc: MemoryService,
    query: str = "",
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,
    format: str = "full",
    ids: list[str] | None = None,
) -> dict:
    if format not in _VALID_SEARCH_FORMATS:
        raise ValueError(
            f"Unknown format {format!r}. Must be one of: {sorted(_VALID_SEARCH_FORMATS)}"
        )

    # When ids provided — skip search pipeline, bulk SQL lookup
    if ids is not None:
        if not ids:
            return {"results": [], "total_matched": 0, "query": query}
        if len(ids) > svc.settings.max_search_ids:
            raise ValueError(
                f"ids exceeds cap of {svc.settings.max_search_ids} IDs "
                f"(got {len(ids)})"
            )
        results = svc.search_by_ids(
            ids,
            include_deleted=include_deleted,
            include_links=include_links and format != "title",
        )
        if format == "title":
            serialized = [serialize_search_result_title(r) for r in results]
        else:
            serialized = [serialize_search_result(r, include_links=include_links) for r in results]
        return {"results": serialized, "total_matched": len(serialized), "query": query}

    # Guard against empty query when ids is not provided
    if not query or not query.strip():
        raise ValueError("query is required when ids is not provided")

    if refine_from is not None and len(refine_from) > svc.settings.max_refine_from_ids:
        raise ValueError(
            f"refine_from exceeds cap of {svc.settings.max_refine_from_ids} IDs "
            f"(got {len(refine_from)})"
        )
    results = svc.search(
        query, limit, min_score, include_links, include_deleted,
        refine_from=refine_from,
        search_format=format,
    )
    if format == "title":
        serialized = [serialize_search_result_title(r) for r in results]
    else:
        serialized = [serialize_search_result(r, include_links=include_links) for r in results]
    return {"results": serialized, "total_matched": len(serialized), "query": query}


def _handle_insert(
    svc: MemoryService,
    memories: list[dict] | None = None,
    links: list[dict] | None = None,
    force: bool = False,
) -> dict:
    memories = memories or []
    links = links or []
    for i, m in enumerate(memories):
        if "title" not in m:
            raise ValueError(f"memory at index {i} is missing required field: 'title'")
    return svc.insert(memories, links, force)


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------

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
) -> dict:
    """Search memories by semantic + keyword query, or bulk-fetch by ID.

    When ``ids`` is provided, skips the vector/BM25 pipeline entirely and does
    a direct SQL lookup by lore_id. ``query`` is ignored in that path.

    Args:
        query: Search text. Required unless ``ids`` is set.
        limit: Max results to return (default from settings).
        min_score: Minimum combined_score threshold (default 0.1).
        include_links: Attach memory links to results (default True; forced off
            in ``format='title'`` mode since links add tokens with no gain).
        include_deleted: Include soft-deleted memories (default False).
        refine_from: Restrict search candidates to these lore_ids (configurable
            cap, default 200 via ``LORE_MAX_REFINE_FROM_IDS``).
        format: ``'full'`` (default) returns complete memory objects with
            relevance scores. ``'title'`` returns compact ``{id, title, score}``
            dicts — lower token cost for listing before a targeted fetch.
        ids: When set, returns these specific lore_ids directly from SQL,
            bypassing the search pipeline. Silently skips unknown IDs. Pair
            with ``format='title'`` for a two-step list-then-fetch workflow.
            Max 50 IDs (configurable via ``max_search_ids``).
    """
    try:
        return _handle_search(
            get_service(), query, limit, min_score, include_links, include_deleted,
            refine_from=refine_from, format=format, ids=ids,
        )
    except Exception:
        log.exception("lore_search_failed", query=query)
        raise


@mcp.tool(name="lore_insert")
async def lore_insert(
    memories: list[dict] | None = None,
    links: list[dict] | None = None,
    force: bool = False,
) -> dict:
    """Insert memories and/or links into the store.

    Each memory dict must include:
      - title (str, required): short unique label for the memory
      - content (str, optional): the full text to store
      - description (str, optional): brief summary
      - score (float, optional, default 5.0): initial quality score 0-10
      - links (list[dict], optional): inline links to create after insert.
        Each link dict: {target_memory_id (str, required), relation_type (str, required),
        reason? (str)}

    Each top-level link dict must include source_memory_id, target_memory_id,
    relation_type, and reason.
    """
    try:
        return _handle_insert(get_service(), memories or [], links or [], force)
    except Exception:
        log.exception("lore_insert_failed", memory_count=len(memories or []))
        raise


@mcp.tool(name="lore_remember")
async def lore_remember(thought: str) -> dict:
    """Fast one-shot memory insert. Pass a thought, get a memory with auto-title."""
    try:
        return get_service().remember(thought)
    except Exception:
        log.exception("lore_remember_failed", thought=thought[:80])
        raise


@mcp.tool(name="lore_update")
async def lore_update(
    memory_feedback: list[dict] | None = None,
    link_feedback: list[dict] | None = None,
) -> dict:
    """Rate memories and links after using them. Drives the quality signal loop.

    Each memory_feedback dict: {id (str), useful (bool), confidence (int 1-10)}.
    Each link_feedback dict: {id (str), useful (bool), confidence (int 1-10)}.

    ``useful=True`` bumps score; ``useful=False`` deducts. Confidence scales the delta.
    Repeated ``useful=False`` with low confidence triggers soft-delete.
    Call after every ``lore_search`` to keep scores calibrated.
    """
    try:
        return get_service().update(memory_feedback or [], link_feedback or [])
    except Exception:
        log.exception("lore_update_failed")
        raise


@mcp.tool(name="lore_processed_sessions")
async def lore_processed_sessions() -> dict:
    """Return all session IDs that have been marked as processed via lore_reflect."""
    try:
        return {"session_ids": get_service().get_processed_session_ids()}
    except Exception:
        log.exception("lore_processed_sessions_failed")
        raise


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
) -> dict:
    """Call once per session — reflect on one session, submit, then move to the next.

    Args:
        session_id: Unique session identifier (required).
        summary: Short summary of what happened in the session (required).
        session_date: ISO date string (e.g. ``"2026-06-02"``). Defaults to today.
        topic: Domain or topic area (e.g. ``"lore_search refactor"``).
        task_type: Optional category for the session (e.g. ``"build"``,
            ``"debug"``, ``"review"``, ``"design"``).
        what_was_done: Longer narrative of the work completed.
        decisions: Key decisions made, with rationale.
        lessons_learnt: List of lessons to propagate to future sessions.
        good_patterns: Patterns that worked well and should be repeated.
        user_profile_updates: Updates about the user's preferences or context.
        factual_discoveries: New facts to record — stored as bullet text in the
            reflection. Also auto-inserted as memories when ``auto_insert=True``.
        memory_ids: IDs of existing memories this reflection relates to.
        auto_insert: When True (default), automatically inserts each item in
            ``factual_discoveries`` (score 7.0) and ``lessons_learnt`` (score 8.0)
            as standalone memories. Duplicate-guarded. Returns created IDs in
            ``memories_created``.

    If this ``session_id`` was already processed, returns immediately with
    ``already_processed=True`` and ``memories_created=[]``. The ``[]`` reflects
    the current call only — the original call's auto-inserts are not
    reconstructed. Check ``already_processed`` to distinguish a retry from a
    first-time call.
    """
    try:
        return get_service().submit_reflection(
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
    except Exception:
        log.exception("lore_reflect_failed", session_id=session_id)
        raise


@mcp.tool()
async def lore_forget(
    memory_ids: list[str],
    reason: str = "unspecified",
) -> dict:
    """Soft-delete one or more memories by ID.

    Memories are marked soft_deleted=1 and excluded from future search results.
    This is reversible at the DB level but no undelete tool is exposed in v1.

    Args:
        memory_ids: List of lore_ids to forget. Must not be empty.
        reason: Why this memory is being forgotten. One of:
            ``"duplicate"``, ``"hallucinated"``, ``"outdated"``,
            ``"expired"``, ``"unspecified"``.

    Returns:
        {
          "forgotten": [str],   # lore_ids successfully soft-deleted
          "not_found": [str],   # lore_ids that were not found
          "errors": [dict]      # any unexpected failures
        }
    """
    if not memory_ids:
        raise ValueError("memory_ids must not be empty")
    _VALID_REASONS = {"duplicate", "hallucinated", "outdated", "expired", "unspecified"}
    if reason not in _VALID_REASONS:
        raise ValueError(f"Unknown reason {reason!r}. Must be one of: {sorted(_VALID_REASONS)}")
    try:
        return get_service().forget(memory_ids, reason)
    except Exception:
        log.exception("lore_forget_failed", memory_ids=memory_ids, reason=reason)
        raise
