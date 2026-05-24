"""MemoryEngine — abstract base class for vector store backends."""

from abc import ABC, abstractmethod


class MemoryEngine(ABC):
    """Abstract base for vector store backends (ChromaDB, LanceDB, etc.)."""

    @abstractmethod
    def probe_score_scale(self) -> None: ...

    @abstractmethod
    def normalize_score(self, raw: float) -> float: ...

    @abstractmethod
    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str: ...

    @abstractmethod
    def search(self, query: str, limit: int = 200) -> list[dict]: ...

    @abstractmethod
    def get_all(self) -> list[dict]: ...

    @abstractmethod
    def delete_by_mem0_id(self, mem0_id: str) -> None: ...