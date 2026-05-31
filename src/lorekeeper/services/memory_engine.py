"""MemoryEngine — abstract base class for vector store backends."""

from abc import ABC, abstractmethod


class MemoryEngine(ABC):
    """Abstract base for vector store backends (ChromaDB, LanceDB, etc.)."""

    @abstractmethod
    def probe_score_scale(self) -> None: ...

    @abstractmethod
    def normalize_score(self, raw: float) -> float:
        """Normalize a raw score from the backend to [0, 1] (higher = better).

        Each engine handles normalization inline in ``search()``, but this
        method is available for direct callers that need to normalize an
        arbitrary raw score (e.g., during bulk migration or testing).
        """

    @abstractmethod
    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str: ...

    @abstractmethod
    def search(self, query: str, limit: int = 200) -> list[dict]: ...

    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def find_mem0_id(self, lore_id: str) -> str | None:
        """Look up the internal mem0_id for a given lore_id.

        Returns None if the lore_id is not stored in the vector index.
        Used by external tooling to correlate lore IDs with vector-store
        internal IDs.
        """
