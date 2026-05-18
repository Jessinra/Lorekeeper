import structlog
from fastmcp import FastMCP

from lorekeeper.config import Settings
from lorekeeper.handlers import handle_insert, handle_search, handle_update
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
    limit: int = 10,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
) -> dict:
    return handle_search(get_service(), query, limit, min_score, include_links, include_deleted)


@mcp.tool(name="lore_insert")
async def lore_insert(
    memories: list[dict] = [],
    links: list[dict] = [],
    force: bool = False,
) -> dict:
    return handle_insert(get_service(), memories, links, force)


@mcp.tool(name="lore_update")
async def lore_update(
    memory_feedback: list[dict] = [],
    link_feedback: list[dict] = [],
) -> dict:
    return handle_update(get_service(), memory_feedback, link_feedback)
