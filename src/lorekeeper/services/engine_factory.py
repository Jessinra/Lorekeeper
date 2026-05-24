"""Factory: returns the appropriate vector store engine based on config."""

from pathlib import Path

from lorekeeper.services.chromadb_engine import ChromaDBEngine, build_mem0
from lorekeeper.services.lancedb_engine import LanceDBEngine
from lorekeeper.services.memory_engine import MemoryEngine


def build_engine(
    vector_store: str, chroma_path: Path, lancedb_path: str, embedding_model: str
) -> MemoryEngine:
    """Factory: returns the appropriate engine based on vector_store config."""
    if vector_store == "lancedb":
        return LanceDBEngine(lancedb_path, embedding_model)
    # Default: Chroma
    mem0 = build_mem0(chroma_path, embedding_model)
    return ChromaDBEngine(mem0)
