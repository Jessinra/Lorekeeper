from typing import Any

import structlog
from fastmcp import FastMCP
from pydantic import ValidationError

from lorekeeper.config import Settings
from lorekeeper.handlers import (
    handle_get_suggestions,
    handle_insert,
    handle_recommend_links,
    handle_review_suggestion,
    handle_search,
)
from lorekeeper.models import WRITE_SOURCE_TYPES
from lorekeeper.services.config_store import ConfigStore
from lorekeeper.services.database import Database
from lorekeeper.services.encouragement import (
    for_forget,
    for_insert,
    for_reflect,
    for_remember,
    for_update,
    set_rate,
)
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.lancedb_engine import LanceDBEngine
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.orchestrator import MemoryService
from lorekeeper.services.reflection_store import ReflectionStore
from lorekeeper.services.suggestion_store import LinkSuggestionStore

log = structlog.get_logger()
mcp: FastMCP = FastMCP(name="lorekeeper-mcp-server")
_svc: MemoryService | None = None
_suggestions_store: LinkSuggestionStore | None = None


def get_service() -> MemoryService:
    global _svc
    if _svc is None:
        raise RuntimeError("MemoryService not initialised — call init_service() first")
    return _svc


def get_suggestions_store() -> LinkSuggestionStore:
    global _suggestions_store
    if _suggestions_store is None:
        raise RuntimeError("LinkSuggestionStore not initialised — call init_service() first")
    return _suggestions_store


def init_service(settings: Settings | None = None) -> MemoryService:
    global _svc, _suggestions_store
    s = settings or Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)

    log.info("init_lorekeeper", data_dir=str(s.data_dir), vector_store="lancedb")
    engine = LanceDBEngine(s.lancedb_path, s.embedding_model)
    engine.probe_score_scale()

    # Shared SQLite connection + versioned migrations
    db = Database(s.sqlite_path, busy_timeout_ms=s.busy_timeout_ms)
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

    # Build namespace filter (shared agents see everything; scoped agents see own + shared)
    ns_filter: list[str] | None = (
        None if s.namespace == "shared" else [s.namespace, "shared"]
    )

    # LKPR-58: instantiate LinkCandidateGenerator once so spaCy model is only loaded once.
    from lorekeeper.services.link_candidate import LinkCandidateGenerator

    link_candidate_generator = LinkCandidateGenerator(
        engine=engine,
        memory_store=memories,
        link_store=links,
        keyword_index=kw,
        settings=s,
        ns_filter=ns_filter,
    )

    svc = MemoryService(
        engine, memories, links, reflections, metrics, config, kw, s,
        link_candidate_generator=link_candidate_generator,
    )
    # Bootstrap BM25 from existing memories
    all_mems = list(svc._all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    log.info("bm25_rebuilt", count=len(all_mems))

    # Set guidance injection rate for write responses
    set_rate(s.enc_rate)
    log.info("enc_rate_set", rate=s.enc_rate)

    # Start internal sweep scheduler (LKPR-99) — standalone SweepService,
    # not coupled to MemoryService internals.
    #
    # IMPORTANT: sweep gets its OWN Database + store instances so it never
    # shares the sqlite3.Connection with the main MCP thread.  Both threads
    # issuing commit() on the same connection at the same time would corrupt
    # transactions (Python's sqlite3 provides zero thread synchronisation even
    # with check_same_thread=False).  WAL mode handles concurrent access at
    # the database-file level — each thread gets its own connection.
    from lorekeeper.scheduler import PeriodicJob
    from lorekeeper.services.sweep_service import SweepService

    sweep_db = Database(s.sqlite_path, busy_timeout_ms=s.busy_timeout_ms)
    sweep_memories = MemoryStore(sweep_db)
    sweep_links = LinkStore(sweep_db)
    sweep_suggestions = LinkSuggestionStore(sweep_db)
    sweep_metrics = MetricsStore(sweep_db)

    from lorekeeper.services.link_candidate import LinkCandidateGenerator

    sweep_generator = LinkCandidateGenerator(
        engine=engine,
        memory_store=sweep_memories,
        link_store=sweep_links,
        keyword_index=kw,
        settings=s,
        ns_filter=ns_filter,
    )
    sweep_svc = SweepService(
        memory_store=sweep_memories,
        link_store=sweep_links,
        suggestion_store=sweep_suggestions,
        link_candidate_generator=sweep_generator,
        settings=s,
        metrics_store=sweep_metrics,
        conn=sweep_db.conn,
    )
    PeriodicJob(
        config, sweep_svc.run, "sweep",
        interval_hours=s.suggest_interval_hours,
        poll_seconds=s.suggest_poll_seconds,
    ).start()
    log.info("sweep_scheduler_started")

    _svc = svc
    _suggestions_store = LinkSuggestionStore(db)
    return svc


# ── MCP tool registration ────────────────────────────────────────────────────

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
        created_after: ISO 8601 UTC timestamp. Only return memories created on
            or after this time (e.g. ``'2026-06-04T00:00:00'``). UTC only;
            non-UTC offsets raise a validation error.
        updated_after: ISO 8601 UTC timestamp. Only return memories updated on
            or after this time. Composes with ``created_after`` and all other
            filters.
        sort_by: ``'relevance'`` (default) ranks by hybrid score when the search
            pipeline runs. In ``ids`` lookup mode there is no scoring, so
            ``'relevance'`` preserves the caller-provided ``ids`` order instead.
            ``'recent'`` sorts by ``updated_at DESC``. ``'frequent'`` sorts by
            ``usage_count DESC``. Composes with timestamp filters.
        source_type: Optional provenance filter. When set, only return memories
            with this exact source_type. One of: ``observed``, ``inferred``,
            ``user_stated``, ``consolidated``, ``injected``, ``unknown``.
    """
    try:
        return handle_search(
            get_service(), query, limit, min_score, include_links, include_deleted,
            refine_from=refine_from, format=format, ids=ids,
            created_after=created_after, updated_after=updated_after,
            sort_by=sort_by, source_type=source_type,
        )
    except Exception:
        log.exception("lore_search_failed", query=query)
        raise


@mcp.tool(name="lore_insert")
async def lore_insert(
    memories: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Insert memories and/or links into the store.

    Each memory dict must include:
      - title (str, required): short unique label for the memory
      - content (str, optional): the full text to store
      - description (str, optional): brief summary
      - score (float, optional, default 5.0): initial quality score 0-10
      - source_type (str, optional, default 'observed'): provenance tag.
        One of: ``observed``, ``inferred``, ``user_stated``,
        ``consolidated``, ``injected``.
      - links (list[dict[str, Any]], optional): inline links to create after insert.
        Each link dict: {target_memory_id (str, required), relation_type (str, required),
        reason? (str)}

    Each top-level link dict must include source_memory_id, target_memory_id,
    relation_type, and reason.
    """
    try:
        result = handle_insert(get_service(), memories or [], links or [], force)
        mem_count = len(memories or [])
        link_count = len(links or [])
        result.update(for_insert(memory_count=mem_count, link_count=link_count))
        return result
    except Exception:
        log.exception("lore_insert_failed", memory_count=len(memories or []))
        raise


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
    """
    lore_id: The source memory to find link candidates for.
    top_k: Max candidates to return (default: LORE_LINK_TOP_M from settings).
    """
    try:
        svc = get_service()
        return handle_recommend_links(
            svc, lore_id=lore_id, top_k=top_k
        )
    except Exception:
        log.exception("lore_recommend_links_failed", lore_id=lore_id)
        raise


@mcp.tool(name="lore_remember")
async def lore_remember(thought: str, source_type: str = "observed") -> dict[str, Any]:
    """Capture a thought instantly — one fact, one call.

    Use this when you discover something worth keeping:
    a decision, a bug root cause, a user preference, a pattern.

    Minimal effort, high reward. Your future self will find this useful.

    Args:
        thought: The fact or observation to store verbatim.
        source_type: Provenance tag for this memory. Defaults to ``'observed'``
            (extracted from conversation). Other values: ``'inferred'``,
            ``'user_stated'``, ``'consolidated'``, ``'injected'``.
    """
    if source_type not in WRITE_SOURCE_TYPES:
        raise ValueError(
            f"Unknown source_type {source_type!r}. Must be one of: {sorted(WRITE_SOURCE_TYPES)}"
        )
    try:
        result = get_service().remember(thought, source_type=source_type)
        result.update(for_remember())
        return result
    except Exception:
        log.exception("lore_remember_failed", thought=thought[:80])
        raise


@mcp.tool(name="lore_update")
async def lore_update(
    memory_feedback: list[dict[str, Any]] | None = None,
    link_feedback: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rate memories and links after using them. Drives the quality signal loop.

    Each memory_feedback dict: {id (str), useful (bool), confidence (int 1-10)}.
    Each link_feedback dict: {id (str), useful (bool), confidence (int 1-10)}.

    ``useful=True`` bumps score; ``useful=False`` deducts. Confidence scales the delta.
    Repeated ``useful=False`` with low confidence triggers soft-delete.
    Call after every ``lore_search`` to keep scores calibrated.
    """
    try:
        result = get_service().update(memory_feedback or [], link_feedback or [])
        result.update(for_update())
        return result
    except Exception:
        log.exception("lore_update_failed")
        raise


@mcp.tool(name="lore_processed_sessions")
async def lore_processed_sessions() -> dict[str, Any]:
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
) -> dict[str, Any]:
    """Reflect on a completed session — save what you learned.

    Minimal usage: pass session_id and summary. That's enough.
    The rest are extras for when you discovered something substantial.

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
        result = get_service().submit_reflection(
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
    except Exception:
        log.exception("lore_reflect_failed", session_id=session_id)
        raise


@mcp.tool()
async def lore_forget(
    memory_ids: list[str],
    reason: str = "unspecified",
) -> dict[str, Any]:
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
        result = get_service().forget(memory_ids, reason)
        forgotten_count = len(result.get("forgotten", []))
        result.update(for_forget(count=forgotten_count))
        return result
    except Exception:
        log.exception("lore_forget_failed", memory_ids=memory_ids, reason=reason)
        raise


# ── MCP tools — suggestion review ─────────────────────────────────────────────


@mcp.tool(name="lore_get_suggestions")
async def lore_get_suggestions(
    limit: int = 20,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Retrieve pending link suggestions for review, sorted by quality score.

    Returns the top candidates from the sweep engine's pending queue.
    Use ``lore_review_suggestion`` to accept or reject them.

    Args:
        limit: Max suggestions to return (default 20, capped at 100).
        min_score: Minimum weighted_score filter, 0.0-1.0 (default 0.0 = all).

    Returns:
        {
          "suggestions": [
            {
              "id": "uuid",
              "source_memory_id": "...",
              "source_title": "...",
              "target_memory_id": "...",
              "target_title": "...",
              "weighted_score": 0.72,
              "cosine_score": 0.81,
              "bm25_score": 0.65,
              "entity_score": 0.30,
              "temporal_score": 0.55,
              "suggested_type": "references",
              "confidence": "standard",
              "created_at": "2026-06-20T12:00:00"
            }
          ],
          "count": 20,
          "total_pending": 142
        }
    """
    try:
        return handle_get_suggestions(
            get_service(), get_suggestions_store(), limit=limit, min_score=min_score
        )
    except Exception:
        log.exception("lore_get_suggestions_failed")
        raise


@mcp.tool(name="lore_review_suggestion")
async def lore_review_suggestion(
    suggestion_ids: list[str],
    action: str,
) -> dict[str, Any]:
    """Accept or reject one or more link suggestions in a single call.

    Processes each suggestion independently — a failure on one does not block
    the rest. Suggestion rows are never deleted; status is updated to
    'accepted' or 'rejected' for audit trail.

    On accept: creates a real ``memory_links`` row using the suggestion's
    ``suggested_type`` (falls back to ``'references'`` if None or unrecognised).

    On reject: marks the suggestion as rejected. Future sweeps skip this pair.

    Idempotent per item: double-accept and double-reject both return
    ``status='skipped'`` with an explanatory message.

    Args:
        suggestion_ids: List of suggestion UUIDs to process (one or many).
        action: Either ``'accept'`` or ``'reject'``.

    Returns:
        {
          "results": [
            {"id": "uuid", "status": "accepted"|"rejected"|"skipped"|"error",
             "link_id": "uuid"|null, "message": "..."}
          ],
          "accepted": int,
          "rejected": int,
          "skipped": int,
          "errors": [{"id": "uuid", "error": "..."}]
        }

        Note: ``status="error"`` is set on a result item when the per-item
        operation raises an unexpected exception. That item is *also* appended
        to ``errors[]``. Callers that iterate ``results[*].status`` should
        treat ``"error"`` as a failure sentinel and consult ``errors[]`` for
        the exception message.
    """
    try:
        return handle_review_suggestion(
            get_service(), get_suggestions_store(),
            suggestion_ids=suggestion_ids, action=action,
        )
    except Exception:
        log.exception("lore_review_suggestion_failed", suggestion_ids=suggestion_ids)
        raise
