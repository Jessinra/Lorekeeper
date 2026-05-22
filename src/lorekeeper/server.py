import structlog
from fastmcp import FastMCP

from lorekeeper.config import Settings
from lorekeeper.handlers import handle_search
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_engine import MemoryEngine, build_mem0
from lorekeeper.services.orchestrator import MemoryService

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

    log.info("init_lorekeeper", data_dir=str(s.data_dir))
    mem0 = build_mem0(s.chroma_path, s.embedding_model)
    engine = MemoryEngine(mem0)
    engine.probe_score_scale()

    store = LinkStore(s.sqlite_path)

    # Apply persisted config overrides (dashboard changes that survived restart)
    overrides = store.get_config_overrides()
    for key, value in overrides.items():
        try:
            setattr(s, key, value)
        except Exception:
            log.warning("config_override_skipped", key=key, value=value)
    if overrides:
        log.info("config_overrides_loaded", keys=list(overrides))

    kw = KeywordIndex()

    svc = MemoryService(engine, store, kw, s)
    # Bootstrap BM25 from existing memories
    all_mems = list(svc._all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    log.info("bm25_rebuilt", count=len(all_mems))

    _svc = svc
    return svc


@mcp.tool(name="lore_search")
async def lore_search(
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,
) -> dict:
    try:
        if refine_from is not None and len(refine_from) > 200:
            raise ValueError(f"refine_from exceeds cap of 200 IDs (got {len(refine_from)})")
        return handle_search(get_service(), query, limit, min_score, include_links, include_deleted, refine_from=refine_from)
    except Exception:
        log.exception("lore_search_failed", query=query)
        raise


@mcp.tool(name="lore_insert")
async def lore_insert(
    memories: list[dict] | None = None,
    links: list[dict] | None = None,
    force: bool = False,
) -> dict:
    try:
        return get_service().insert(memories or [], links or [], force)
    except Exception:
        log.exception("lore_insert_failed", memory_count=len(memories or []))
        raise


@mcp.tool(name="lore_update")
async def lore_update(
    memory_feedback: list[dict] | None = None,
    link_feedback: list[dict] | None = None,
) -> dict:
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
) -> dict:
    """Call once per session — reflect on one session, submit, then move to the next."""
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
        )
    except Exception:
        log.exception("lore_reflect_failed", session_id=session_id)
        raise
