from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.link.service import LinkService
from lorekeeper.domains.memory.import_service import ImportService
from lorekeeper.domains.memory.models import Memory
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.memory.service import (
    MemorySearchService,
    MemoryWriteService,
    extract_title,
    row_to_memory,
)
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.domains.reflection.service import ReflectionService
from lorekeeper.domains.suggestion.service import SuggestionService
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.config.repository import ConfigStore
from lorekeeper.platform.metrics.repository import MetricsStore

if TYPE_CHECKING:
    from lorekeeper.domains.suggestion.candidate import LinkCandidate, LinkCandidateGenerator

log = structlog.get_logger()


class MemoryService:
    """Facade over the domain services — search, insert, remember, update, reflect.

    LKPR-104 Phase 5: this class used to contain all business logic directly.
    That logic now lives in focused domain services
    (``MemorySearchService``, ``MemoryWriteService``, ``LinkService``,
    ``SuggestionService``, ``ReflectionService``, ``ImportService``), each of
    which takes this facade instance and reaches back into it for shared
    infra (engine, keyword index, connection, cache, metrics). This facade
    is temporary — deleted in Phase 7, at which point callers (``handlers.py``,
    dashboard routes) talk to the domain services directly and each service
    owns its own infra references instead of borrowing them from here.

    Public method names/signatures are unchanged from the pre-Phase-5
    orchestrator so no caller needs to change in this phase.
    """

    @staticmethod
    def _extract_title(thought: str) -> str:
        """Smart title: first complete word at or after ~80 chars,
        ending at sentence boundary if possible.

        Kept as a static method (not a free function call) because tests
        monkey-patch ``service._extract_title`` as an instance attribute to
        simulate extraction failures — routing through this method preserves
        that override point after the Phase 5 split.
        """
        return extract_title(thought)

    def __init__(
        self,
        engine: LanceDBEngine,
        memories: MemoryStore,
        links: LinkStore,
        reflections: ReflectionStore,
        metrics: MetricsStore,
        config: ConfigStore,
        keyword_index: KeywordIndex,
        settings: Settings,
        link_candidate_generator: LinkCandidateGenerator | None = None,
    ) -> None:
        self._engine = engine
        self.memories = memories
        self.links = links
        self.reflections = reflections
        self.metrics = metrics
        self.config = config
        self._kw = keyword_index
        self.settings = settings
        self._namespace: str = settings.namespace
        # Orchestrator owns commit control — all stores share this connection
        self._conn = memories._conn
        # Namespace filter for all read/write operations: None = no filter (shared sees all).
        self._ns_filter: list[str] | None = (
            None if self._namespace == "shared" else [self._namespace, "shared"]
        )
        # LKPR-60: in-process cache for all_memories(include_deleted=True).
        # None means dirty — must reload from SQLite. Cache always holds the full
        # (include_deleted=True) dataset; include_deleted=False is filtered in Python.
        self._memory_cache: dict[str, Memory] | None = None
        # LKPR-58: instantiate LinkCandidateGenerator once so spaCy model is only loaded once.
        if link_candidate_generator is not None:
            self._link_candidate_generator = link_candidate_generator
        else:
            from lorekeeper.domains.suggestion.candidate import LinkCandidateGenerator

            self._link_candidate_generator = LinkCandidateGenerator(
                engine=self._engine,
                memory_store=self.memories,
                link_store=self.links,
                keyword_index=self._kw,
                settings=self.settings,
                ns_filter=self._ns_filter,
            )

        # Domain services — each borrows this facade for shared infra access.
        self.memory_search_service = MemorySearchService(self)
        self.memory_write_service = MemoryWriteService(self)
        self.link_service = LinkService(self)
        self.suggestion_service = SuggestionService(self)
        self.reflection_service = ReflectionService(self)
        self.import_service = ImportService(self)

    def _invalidate_cache(self) -> None:
        """Mark the memory cache dirty. Call at every write that adds/removes memories."""
        self._memory_cache = None

    def commit(self) -> None:
        """Flush all pending writes to disk.

        Dashboard routes use this instead of accessing _conn directly.
        """
        self._conn.commit()

    def _all_memories(self, include_deleted: bool = False) -> dict[str, Memory]:
        # None → no filter → reads all rows (backward-compat for the default "shared" agent).
        # Non-shared agents scope reads to their own namespace + the shared pool.
        namespaces = self._ns_filter
        if self._memory_cache is None:
            rows = self.memories.all_memory_rows(include_deleted=True, namespaces=namespaces)
            self._memory_cache = {r["id"]: row_to_memory(r) for r in rows}
        if include_deleted:
            return dict(self._memory_cache)
        return {mid: m for mid, m in self._memory_cache.items() if not m.soft_deleted}

    def _rebuild_kw(self) -> None:
        self._invalidate_cache()
        mems = list(self._all_memories(include_deleted=True).values())
        self._kw.rebuild(mems)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _increment_metric(self, tool_name: str) -> None:
        try:
            self.metrics.increment_metric(tool_name)
            self._conn.commit()
        except sqlite3.Error:
            # Metrics must never break a real call, but the failure should be
            # observable. Log at WARNING (not ERROR) — metric write is degraded,
            # not a request failure.
            log.warning("metric_increment_failed", tool_name=tool_name, exc_info=True)

    # ── Search — delegates to MemorySearchService ────────────────────────────

    def search(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self.memory_search_service.search(*args, **kwargs)

    def search_by_ids(self, *args: Any, **kwargs: Any) -> list[Any]:
        return self.memory_search_service.search_by_ids(*args, **kwargs)

    # ── Insert / Remember / Update / Forget — delegates to MemoryWriteService ─

    def insert(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.insert(*args, **kwargs)

    def remember(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.remember(*args, **kwargs)

    def update(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.update(*args, **kwargs)

    def forget(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.forget(*args, **kwargs)

    def _auto_link(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        return self.memory_write_service.auto_link(*args, **kwargs)

    def _insert_one_memory(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.insert_one_memory(*args, **kwargs)

    def _remember_with_score(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.memory_write_service.remember_with_score(*args, **kwargs)

    # ── Link — delegates to LinkService ───────────────────────────────────────

    def _insert_one_link(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.link_service.insert_one_link(*args, **kwargs)

    @staticmethod
    def _validate_relation_type(relation: str) -> None:
        LinkService.validate_relation_type(relation)

    # ── Import (backup restore) — delegates to ImportService ─────────────────

    def import_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.import_service.import_dump(*args, **kwargs)

    # ── Reflect — delegates to ReflectionService ──────────────────────────────

    def submit_reflection(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.reflection_service.submit_reflection(*args, **kwargs)

    def get_processed_session_ids(self) -> list[str]:
        return self.reflection_service.get_processed_session_ids()

    # ── Suggestions — delegates to SuggestionService ──────────────────────────

    def recommend_links(self, *args: Any, **kwargs: Any) -> list[LinkCandidate]:
        return self.suggestion_service.recommend_links(*args, **kwargs)
