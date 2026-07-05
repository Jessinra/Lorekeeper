"""Composition root — wires all dependencies, creates handler structs, registers MCP tools.

Layer 6 — exempt from layer import rules.  This is the single place where
services, processors, stores, and handlers are instantiated and wired together.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from fastmcp import FastMCP
from pydantic import ValidationError

if TYPE_CHECKING:
    from lorekeeper.dashboard.handler import DashboardHandler

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.link.service import LinkService
from lorekeeper.domains.memory.cache import MemoryCache
from lorekeeper.domains.memory.import_service import ImportService
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.memory.service import MemorySearchService, MemoryWriteService
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.domains.reflection.service import ReflectionService
from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator
from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
from lorekeeper.domains.suggestion.service import SuggestionService
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.config.repository import ConfigStore
from lorekeeper.platform.metrics.repository import MetricsStore
from lorekeeper.processors.admin import AdminProcessor
from lorekeeper.processors.link import LinkProcessor
from lorekeeper.processors.memory import MemoryProcessor
from lorekeeper.processors.reflection import ReflectionProcessor
from lorekeeper.processors.suggestion import SuggestionProcessor

log = structlog.get_logger()
mcp: FastMCP = FastMCP(name="lorekeeper-mcp-server")


@dataclass
class Server:
    """Public interface of the composed Lorekeeper server.

    Returned by ``init_service()``.  Consumers access their slice through
    this struct rather than reaching into module-level globals.
    """

    dashboard_handler: "DashboardHandler"


# ── Module-level singletons (DEPRECATED — will be removed when dashboard   ──
#    routes migrate to app.state.dashboard_handler)                          ──
_settings: Settings | None = None
_memory_store: MemoryStore | None = None
_link_store: LinkStore | None = None
_db: Database | None = None
_suggestion_processor: SuggestionProcessor | None = None
_memory_processor: MemoryProcessor | None = None
_reflection_processor: ReflectionProcessor | None = None
_link_processor: LinkProcessor | None = None
_admin_processor: AdminProcessor | None = None


# ── Store getters (DEPRECATED — dashboard routes will migrate to            ──
#    DashboardHandler)                                                       ──


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        raise RuntimeError("MemoryStore not initialised — call init_service() first")
    return _memory_store


def get_link_store() -> LinkStore:
    global _link_store
    if _link_store is None:
        raise RuntimeError("LinkStore not initialised — call init_service() first")
    return _link_store


def get_db() -> Database:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialised — call init_service() first")
    return _db


def get_suggestion_processor() -> SuggestionProcessor:
    global _suggestion_processor
    if _suggestion_processor is None:
        raise RuntimeError("SuggestionProcessor not initialised")
    return _suggestion_processor


def get_memory_processor() -> MemoryProcessor:
    global _memory_processor
    if _memory_processor is None:
        raise RuntimeError("MemoryProcessor not initialised")
    return _memory_processor


def get_reflection_processor() -> ReflectionProcessor:
    global _reflection_processor
    if _reflection_processor is None:
        raise RuntimeError("ReflectionProcessor not initialised")
    return _reflection_processor


def get_link_processor() -> LinkProcessor:
    global _link_processor
    if _link_processor is None:
        raise RuntimeError("LinkProcessor not initialised")
    return _link_processor


def get_admin_processor() -> AdminProcessor:
    global _admin_processor
    if _admin_processor is None:
        raise RuntimeError("AdminProcessor not initialised")
    return _admin_processor


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        raise RuntimeError("Settings not initialised — call init_service() first")
    return _settings


# ── Composition root ──────────────────────────────────────────────────────


def init_service(settings: Settings | None = None) -> Server:
    """Wire everything bottom-up: stores → domain services → processors → handlers.

    Returns a ``Server`` struct that consumers use to access their handler slice
    (e.g. ``server.dashboard_handler``).
    """
    from lorekeeper.api.mcp.handlers import MCPHandler
    from lorekeeper.api.mcp.tools import register_mcp_tools
    from lorekeeper.dashboard.handler import DashboardHandler
    from lorekeeper.shared.encouragement import set_rate

    # ── Infra ────────────────────────────────────────────────────────────────

    global _settings, _memory_store, _link_store, _db
    global _suggestion_processor, _memory_processor, _reflection_processor
    global _link_processor, _admin_processor

    s = settings or Settings()
    _settings = s
    s.data_dir.mkdir(parents=True, exist_ok=True)

    log.info("init_lorekeeper", data_dir=str(s.data_dir), vector_store="lancedb")
    engine = LanceDBEngine(s.lancedb_path, s.embedding_model)
    engine.probe_score_scale()

    db = Database(s.sqlite_path, busy_timeout_ms=s.busy_timeout_ms)
    db.migrate()
    _db = db

    memories = MemoryStore(db)
    links = LinkStore(db)
    reflections = ReflectionStore(db)
    metrics = MetricsStore(db)
    config = ConfigStore(db)
    suggestions = LinkSuggestionStore(db)
    _memory_store = memories
    _link_store = links

    # Apply persisted config overrides
    overrides = config.get_overrides()
    for key, value in overrides.items():
        try:
            setattr(s, key, value)
            getattr(s, key)
        except (ValueError, TypeError, AttributeError, ValidationError) as e:
            log.warning("config_override_skipped", key=key, value=value, error=str(e))
    if overrides:
        log.info("config_overrides_loaded", keys=list(overrides))

    kw = KeywordIndex()

    ns_filter: list[str] | None = (
        None if s.namespace == "shared" else [s.namespace, "shared"]
    )

    cache = MemoryCache(memories, kw, ns_filter)

    link_candidate_generator = LinkCandidateGenerator(
        engine=engine,
        memory_store=memories,
        link_store=links,
        keyword_index=kw,
        settings=s,
        ns_filter=ns_filter,
    )

    # ── Domain services ──────────────────────────────────────────────────────

    link_service = LinkService(links=links)
    write_service = MemoryWriteService(
        engine=engine, memories=memories, links=links, cache=cache,
        metrics=metrics, settings=s, db=db,
        namespace=s.namespace, ns_filter=ns_filter,
        link_service=link_service, kw=kw,
    )
    search_service = MemorySearchService(
        engine=engine, kw=kw, memories=memories, links=links, cache=cache,
        metrics=metrics, settings=s, db=db, ns_filter=ns_filter,
    )
    reflection_service = ReflectionService(
        reflections=reflections, metrics=metrics, db=db,
        cache=cache, write_service=write_service,
    )
    suggestion_service = SuggestionService(
        candidate_generator=link_candidate_generator, engine=engine, kw=kw,
        memories=memories, links=links, metrics=metrics,
        settings=s, db=db, ns_filter=ns_filter,
    )
    import_service = ImportService(
        engine=engine, memories=memories, links=links, cache=cache,
        db=db, namespace=s.namespace,
    )

    # ── Processors ───────────────────────────────────────────────────────────

    _memory_processor = MemoryProcessor(
        search_service=search_service, write_service=write_service,
        import_service=import_service, metrics=metrics, db=db, settings=s,
    )
    _reflection_processor = ReflectionProcessor(
        reflection_service=reflection_service, reflections=reflections,
        metrics=metrics, db=db,
    )
    _link_processor = LinkProcessor(
        link_service=link_service, memories=memories, links=links,
        metrics=metrics, db=db,
    )
    _suggestion_processor = SuggestionProcessor(
        suggestion_service=suggestion_service, suggestions=suggestions,
        metrics=metrics, db=db,
    )
    _admin_processor = AdminProcessor(
        config=config, metrics=metrics, suggestions=suggestions,
        settings=s, db=db,
    )

    # Bootstrap BM25 from existing memories
    all_mems = list(cache.all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    log.info("bm25_rebuilt", count=len(all_mems))

    # Set guidance injection rate for write responses
    set_rate(s.enc_rate)
    log.info("enc_rate_set", rate=s.enc_rate)

    # ── Handlers (one per API level) ─────────────────────────────────────────

    mcp_handler = MCPHandler(
        memory_processor=_memory_processor,
        suggestion_processor=_suggestion_processor,
        reflection_processor=_reflection_processor,
        link_processor=_link_processor,
        admin_processor=_admin_processor,
    )

    dashboard_handler = DashboardHandler(
        memory_processor=_memory_processor,
        suggestion_processor=_suggestion_processor,
        reflection_processor=_reflection_processor,
        link_processor=_link_processor,
        admin_processor=_admin_processor,
        memory_store=memories,
        link_store=links,
        settings=s,
    )

    # Register MCP tools on the FastMCP server
    register_mcp_tools(mcp, mcp_handler)
    log.info("mcp_tools_registered", count=10)

    # ── Internal sweep scheduler (LKPR-99) ───────────────────────────────────

    from lorekeeper.domains.suggestion.sweep import SweepService
    from lorekeeper.infra.scheduler import PeriodicJob

    sweep_db = Database(s.sqlite_path, busy_timeout_ms=s.busy_timeout_ms)
    sweep_memories = MemoryStore(sweep_db)
    sweep_links = LinkStore(sweep_db)
    sweep_suggestions = LinkSuggestionStore(sweep_db)
    sweep_metrics = MetricsStore(sweep_db)

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

    return Server(dashboard_handler=dashboard_handler)
