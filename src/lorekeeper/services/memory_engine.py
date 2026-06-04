"""MemoryEngine — abstract base class for vector store backends."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


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
    def add(self, text: str, lore_id: str, extra_metadata: dict[str, Any] | None = None) -> str: ...

    @abstractmethod
    def search(self, query: str, limit: int = 200) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_all(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def find_mem0_id(self, lore_id: str) -> str | None:
        """Look up the internal mem0_id for a given lore_id.

        Returns None if the lore_id is not stored in the vector index.
        Used by external tooling to correlate lore IDs with vector-store
        internal IDs.

        Note: this is a best-effort lookup. The ChromaDB engine limits the
        search to the first 5000 results from mem0.get_all() (top_k=5000).
        For deployments with more memories than top_k, a matching lore_id
        may silently return None if its mem0 record falls outside the
        queried range. The LanceDB engine scans the full table and has no
        such limit.
        """

    @abstractmethod
    def get_embeddings_batch(self, lore_ids: list[str]) -> dict[str, np.ndarray]:
        """Return embedding vectors keyed by lore_id.

        Implementations may read stored vectors (LanceDB) or re-encode on the fly (ChromaDB).
        Missing lore_ids are silently omitted from the result dict.
        """
