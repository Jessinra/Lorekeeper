'''In-process cache for all Memory rows + BM25 rebuild coupling.

Cache always holds the full (include_deleted=True) dataset;
include_deleted=False is filtered in Python. None = dirty.
MUST be a single shared instance across all services -- two instances
silently split invalidation.
'''

from __future__ import annotations

from lorekeeper.domains.memory.models import Memory
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.memory.service import row_to_memory
from lorekeeper.infra.keyword_index import KeywordIndex


class MemoryCache:
    """In-process cache of all Memory rows + BM25 rebuild coupling.

    Cache always holds the full (include_deleted=True) dataset;
    include_deleted=False is filtered in Python. None = dirty.
    MUST be a single shared instance across all services -- two instances
    silently split invalidation.
    """

    def __init__(
        self,
        memories: MemoryStore,
        kw: KeywordIndex,
        ns_filter: list[str] | None,
    ) -> None:
        self._memories = memories
        self._kw = kw
        self._ns_filter = ns_filter
        self._memory_cache: dict[str, Memory] | None = None

    def all_memories(self, include_deleted: bool = False) -> dict[str, Memory]:
        """Return cached memories, populating from DB if dirty."""
        if self._memory_cache is None:
            rows = self._memories.all_memory_rows(
                include_deleted=True, namespaces=self._ns_filter
            )
            self._memory_cache = {r["id"]: row_to_memory(r) for r in rows}
        if include_deleted:
            return dict(self._memory_cache)
        return {mid: m for mid, m in self._memory_cache.items() if not m.soft_deleted}

    def invalidate(self) -> None:
        """Mark the memory cache as dirty. Call at every write that adds/removes memories."""
        self._memory_cache = None

    def rebuild_kw(self) -> None:
        """Invalidate cache and rebuild BM25 keyword index from all memories."""
        self.invalidate()
        mems = list(self.all_memories(include_deleted=True).values())
        self._kw.rebuild(mems)
