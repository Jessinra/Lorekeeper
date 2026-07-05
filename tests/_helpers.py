"""Shared test helpers for building Lorekeeper stores + complete app wiring.

Encapsulates the standard Database + focused-stores wiring so tests don't have
to repeat the boilerplate. Use ``build_stores(tmp_path)`` to get a ``Stores`` bundle
with all five focused stores sharing a single migrated Database, and
``build_app(stores, engine, kw, settings)`` to construct a full ``App`` with all
domain services and processors wired in the same order as ``server.init_service()``.

WIRING ORDER (must mirror server.py init_service() 1:1):
  settings -> engine (+probe) -> Database -> stores -> config overrides ->
  KeywordIndex -> ns_filter -> MemoryCache -> LinkCandidateGenerator ->
  domain services (link -> write -> search -> reflection -> suggestion -> import)
  -> processors (memory, link, reflection, suggestion, admin) -> BM25 bootstrap
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.link.service import LinkService
from lorekeeper.domains.memory.cache import MemoryCache
from lorekeeper.domains.memory.import_service import ImportService
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.memory.service import (
    MemorySearchService,
    MemoryWriteService,
)
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.domains.reflection.service import ReflectionService
from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator
from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
from lorekeeper.domains.suggestion.service import SuggestionService
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.config.repository import ConfigStore
from lorekeeper.platform.metrics.repository import MetricsStore
from lorekeeper.processors.admin import AdminProcessor
from lorekeeper.processors.link import LinkProcessor
from lorekeeper.processors.memory import MemoryProcessor
from lorekeeper.processors.reflection import ReflectionProcessor
from lorekeeper.processors.suggestion import SuggestionProcessor


@dataclass
class Stores:
    """Bundle of all focused stores plus the shared Database."""
    db: Database
    memories: MemoryStore
    links: LinkStore
    suggestions: LinkSuggestionStore
    reflections: ReflectionStore
    metrics: MetricsStore
    config: ConfigStore

    def close(self) -> None:
        """Close the shared SQLite connection. Call in fixture teardown."""
        self.db.close()


def build_stores(db_path: Path) -> Stores:
    """Build a migrated Database and all five focused stores."""
    db = Database(db_path)
    db.migrate()
    return Stores(
        db=db,
        memories=MemoryStore(db),
        links=LinkStore(db),
        suggestions=LinkSuggestionStore(db),
        reflections=ReflectionStore(db),
        metrics=MetricsStore(db),
        config=ConfigStore(db),
    )


@dataclass
class App:
    """Complete app wiring — mirrors server.py init_service() in composition root order.

    Tests that previously used ``build_service()`` -> ``MemoryService`` should
    use ``build_app()`` -> ``App`` instead.
    """

    stores: Stores
    cache: MemoryCache
    db: Database
    memories: MemoryStore
    links: LinkStore
    reflections: ReflectionStore
    metrics: MetricsStore
    config: ConfigStore
    settings: Settings
    link_service: LinkService
    write_service: MemoryWriteService
    search_service: MemorySearchService
    reflection_service: ReflectionService
    suggestion_service: SuggestionService
    import_service: ImportService
    link_candidate_generator: LinkCandidateGenerator
    memory_processor: MemoryProcessor
    link_processor: LinkProcessor
    reflection_processor: ReflectionProcessor
    suggestion_processor: SuggestionProcessor
    admin_processor: AdminProcessor
    kw: KeywordIndex = field(repr=False)
    engine: Any = field(repr=False)

    # ── Backward-compat properties (old MemoryService API) ───────────────────

    @property
    def _engine(self) -> Any:
        return self.engine

    @property
    def _conn(self) -> Any:
        return self.db.conn

    def _invalidate_cache(self) -> None:
        self.cache.invalidate()

    def _increment_metric(self, tool_name: str) -> None:
        self.metrics.increment_metric_safe(tool_name)

    @property
    def memory_search_service(self) -> MemorySearchService:
        return self.search_service

    @property
    def memory_write_service(self) -> MemoryWriteService:
        return self.write_service

    # ── Convenience methods (delegate to the appropriate domain service) ─────

    def insert(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.write_service.insert(*args, **kwargs)

    def update(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.write_service.update(*args, **kwargs)

    def forget(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.write_service.forget(*args, **kwargs)

    def search(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self.search_service.search(*args, **kwargs)

    def submit_reflection(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.reflection_service.submit_reflection(*args, **kwargs)

    def get_processed_session_ids(self) -> list[str]:
        return self.reflection_service.get_processed_session_ids()

    def recommend_links(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self.suggestion_service.recommend_links(*args, **kwargs)

    def _all_memories(self, include_deleted: bool = False) -> dict[str, Any]:
        return self.cache.all_memories(include_deleted)

    def _rebuild_kw(self) -> None:
        self.cache.rebuild_kw()

    def rebuild_kw(self) -> None:
        self.cache.rebuild_kw()


def build_app(
    stores: Stores,
    engine: Any,
    kw: KeywordIndex,
    settings: Settings,
) -> App:
    """Construct a full App — all stores, domain services, and processors.

    Wiring order mirrors server.py init_service() — keep both in sync.
    Use the cross-reference comment in server.py as the source of truth.
    """
    ns_filter: list[str] | None = (
        None if settings.namespace == "shared" else [settings.namespace, "shared"]
    )
    cache = MemoryCache(stores.memories, kw, ns_filter)
    link_candidate_generator = LinkCandidateGenerator(
        engine=engine, memory_store=stores.memories, link_store=stores.links,
        keyword_index=kw, settings=settings, ns_filter=ns_filter,
    )
    link_service = LinkService(links=stores.links)
    write_service = MemoryWriteService(
        engine=engine, memories=stores.memories, links=stores.links, cache=cache,
        metrics=stores.metrics, settings=settings, db=stores.db,
        namespace=settings.namespace, ns_filter=ns_filter,
        link_service=link_service, kw=kw,
    )
    search_service = MemorySearchService(
        engine=engine, kw=kw, memories=stores.memories, links=stores.links, cache=cache,
        metrics=stores.metrics, settings=settings, db=stores.db, ns_filter=ns_filter,
    )
    reflection_service = ReflectionService(
        reflections=stores.reflections, metrics=stores.metrics, db=stores.db,
        cache=cache, write_service=write_service,
    )
    suggestion_service = SuggestionService(
        candidate_generator=link_candidate_generator, engine=engine, kw=kw,
        memories=stores.memories, links=stores.links, metrics=stores.metrics,
        settings=settings, db=stores.db, ns_filter=ns_filter,
    )
    import_service = ImportService(
        engine=engine, memories=stores.memories, links=stores.links, cache=cache,
        db=stores.db, namespace=settings.namespace,
    )
    memory_processor = MemoryProcessor(
        search_service=search_service, write_service=write_service,
        import_service=import_service, metrics=stores.metrics, db=stores.db, settings=settings,
    )
    reflection_processor = ReflectionProcessor(
        reflection_service=reflection_service, reflections=stores.reflections,
        metrics=stores.metrics, db=stores.db,
    )
    link_processor = LinkProcessor(
        link_service=link_service, memories=stores.memories, links=stores.links,
        metrics=stores.metrics, db=stores.db,
    )
    suggestion_processor = SuggestionProcessor(
        suggestion_service=suggestion_service, suggestions=stores.suggestions,
        metrics=stores.metrics, db=stores.db,
    )
    admin_processor = AdminProcessor(
        config=stores.config, metrics=stores.metrics, suggestions=stores.suggestions,
        settings=settings, db=stores.db,
    )
    all_mems = list(cache.all_memories(include_deleted=True).values())
    kw.rebuild(all_mems)
    return App(
        stores=stores,
        cache=cache,
        db=stores.db,
        memories=stores.memories,
        links=stores.links,
        reflections=stores.reflections,
        metrics=stores.metrics,
        config=stores.config,
        settings=settings,
        link_service=link_service,
        write_service=write_service,
        search_service=search_service,
        reflection_service=reflection_service,
        suggestion_service=suggestion_service,
        import_service=import_service,
        link_candidate_generator=link_candidate_generator,
        memory_processor=memory_processor,
        link_processor=link_processor,
        reflection_processor=reflection_processor,
        suggestion_processor=suggestion_processor,
        admin_processor=admin_processor,
        kw=kw,
        engine=engine,
    )


class FakeEngine:
    """Minimal stub: stores text by lore_id, returns configurable search results."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._search_results: list[dict] = []

    def probe_score_scale(self) -> None:
        pass

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
        self._store[lore_id] = text
        return lore_id

    def search(self, query: str, limit: int = 200) -> list[dict]:
        return self._search_results[:limit]

    def get_embeddings_batch(self, ids: list[str]) -> dict[str, list[float]]:
        import numpy as np

        out = {}
        for lid in ids:
            if lid in self._store:
                v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
                out[lid] = v
        return out

    def get_all(self) -> list[dict]:
        return [{"lore_id": k, "mem0_id": k} for k in self._store]

    def normalize_score(self, raw: float) -> float:
        return raw

    def find_vector_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None
