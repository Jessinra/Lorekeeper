import uuid
from typing import Any, cast

import numpy as np
import structlog

from lorekeeper.services.memory_engine import MemoryEngine

log = structlog.get_logger()


class LanceDBEngine(MemoryEngine):
    """MemoryEngine-compatible backend using LanceDB directly.

    Uses sentence-transformers for embeddings and LanceDB for vector storage.
    No Mem0, no Chroma — clean concurrent multi-process access.
    """

    def __init__(self, db_path: str, embedding_model: str) -> None:
        import lancedb

        self._db = lancedb.connect(db_path)
        self._model = None  # lazy-loaded sentence-transformers model
        self._model_name = embedding_model
        self._dimension = 384  # all-MiniLM-L6-v2

        # Create or open the table
        try:
            self._table = self._db.open_table("lorekeeper")
        except Exception:
            self._table = self._db.create_table(
                "lorekeeper",
                data=[
                    {
                        "vector": np.zeros(self._dimension, dtype=np.float32),
                        "lore_id": "",
                        "mem0_id": "",
                        "text": "",
                    }
                ],
                mode="overwrite",
            )

    def _get_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def probe_score_scale(self) -> None:
        """No-op for LanceDB — scores are always cosine distance (lower=better)."""
        log.info("lancedb_probe_skipped", engine="lancedb")

    def normalize_score(self, raw: float) -> float:
        """Convert LanceDB cosine distance to similarity (higher=better)."""
        return max(0.0, min(1.0, 1.0 - raw))

    def add(self, text: str, lore_id: str, extra_metadata: dict[str, Any] | None = None) -> str:
        """Embed text, store in LanceDB. Returns internal mem0_id."""
        mem0_id = str(uuid.uuid4())
        vector = self._get_model().encode(text).astype(np.float32)
        self._table.add(
            [
                {
                    "vector": vector,
                    "lore_id": lore_id,
                    "mem0_id": mem0_id,
                    "text": text,
                }
            ]
        )
        return mem0_id

    def search(self, query: str, limit: int = 200) -> list[dict[str, Any]]:
        """Returns list of {lore_id, mem0_id, score (normalized)}.

        Embeds the query and searches LanceDB with cosine distance.
        Converts distance to similarity (higher=better).
        """
        vector = self._get_model().encode(query).astype(np.float32)
        try:
            results = self._table.search(vector).limit(limit).to_list()
        except Exception:
            return []

        out = []
        for row in results:
            lore_id = row.get("lore_id", "")
            mem0_id = row.get("mem0_id", "")
            if not lore_id:
                continue
            # LanceDB returns distance (lower=better). Convert to similarity.
            distance = row.get("_distance", 0.0)
            similarity = max(0.0, min(1.0, 1.0 - distance))
            out.append({"lore_id": lore_id, "mem0_id": mem0_id, "score": similarity})
        return out

    def get_all(self) -> list[dict[str, Any]]:
        """Returns all entries as {lore_id, mem0_id}. Used for BM25 rebuild."""
        try:
            tbl = self._table.to_arrow()
        except Exception:
            log.error("lancedb_get_all_failed", exc_info=True)
            return []
        out = []
        lore_ids = tbl.column("lore_id")
        mem0_ids = tbl.column("mem0_id")
        for i in range(tbl.num_rows):
            lore_id = lore_ids[i].as_py()
            mem0_id = mem0_ids[i].as_py()
            if lore_id:
                out.append({"lore_id": lore_id, "mem0_id": mem0_id})
        return out

    def find_vector_id(self, lore_id: str) -> str | None:
        """Look up the internal vector-store ID (mem0_id column) by lore_id."""
        try:
            tbl = self._table.to_arrow()
        except Exception:
            log.error("lancedb_find_vector_id_failed", lore_id=lore_id, exc_info=True)
            return None
        ids = tbl.column("lore_id")
        mem0_ids = tbl.column("mem0_id")
        for i in range(tbl.num_rows):
            if ids[i].as_py() == lore_id:
                return cast(str, mem0_ids[i].as_py())
        return None

    def delete_by_vector_id(self, vector_id: str) -> None:
        """Delete a row by internal vector-store ID (mem0_id column)."""
        escaped = vector_id.replace("'", "''")
        self._table.delete(f"mem0_id = '{escaped}'")

    def get_embeddings_batch(self, lore_ids: list[str]) -> dict[str, np.ndarray]:
        """Read stored vectors from LanceDB table — no re-encoding needed."""
        if not lore_ids:
            return {}
        try:
            tbl = self._table.to_arrow()
        except Exception:
            log.error("lancedb_get_embeddings_batch_failed", exc_info=True)
            return {}
        id_set = set(lore_ids)
        out: dict[str, np.ndarray] = {}
        lore_id_col = tbl.column("lore_id")
        vector_col = tbl.column("vector")
        for i in range(tbl.num_rows):
            lid = lore_id_col[i].as_py()
            if lid in id_set:
                out[lid] = np.array(vector_col[i].as_py(), dtype=np.float32)
        return out
