"""MemoryEngine — abstract base class for vector store backends."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class MemoryEngine(ABC):
    """Abstract base for vector store backends."""

    @abstractmethod
    def probe_score_scale(self) -> None: ...

    @abstractmethod
    def normalize_score(self, raw: float) -> float:
        """Normalize a raw score from the backend to [0, 1] (higher = better)."""

    @abstractmethod
    def add(self, text: str, lore_id: str, extra_metadata: dict[str, Any] | None = None) -> str: ...

    @abstractmethod
    def search(self, query: str, limit: int = 200) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_all(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def find_vector_id(self, lore_id: str) -> str | None:
        """Look up the internal vector-store ID for a given lore_id.

        Returns None if the lore_id is not found in the vector index.
        """

    @abstractmethod
    def delete_by_vector_id(self, vector_id: str) -> None: ...

    @abstractmethod
    def get_embeddings_batch(self, lore_ids: list[str]) -> dict[str, np.ndarray]:
        """Return embedding vectors keyed by lore_id.

        Missing lore_ids are silently omitted from the result dict.
        """
