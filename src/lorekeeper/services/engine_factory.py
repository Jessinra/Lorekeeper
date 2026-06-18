"""Factory: returns the vector store engine (LanceDB)."""

from lorekeeper.services.lancedb_engine import LanceDBEngine
from lorekeeper.services.memory_engine import MemoryEngine


def build_engine(lancedb_path: str, embedding_model: str) -> MemoryEngine:
    """Return a LanceDB-backed MemoryEngine."""
    return LanceDBEngine(lancedb_path, embedding_model)
