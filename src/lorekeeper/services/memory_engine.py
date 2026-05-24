import os
import uuid
from pathlib import Path

import numpy as np
import structlog
from mem0 import Memory as Mem0Memory

log = structlog.get_logger()

LORE_USER_ID = "lorekeeper"

# Suppress Mem0/Chroma stdout noise before import
os.environ.setdefault("MEM0_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")


# ── Chroma (Mem0-based) ─────────────────────────────────────────────────────


def build_mem0(chroma_path: Path, embedding_model: str) -> Mem0Memory:
    chroma_path.mkdir(parents=True, exist_ok=True)
    config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "lorekeeper",
                "path": str(chroma_path),
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": embedding_model},
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "api_key": "sk-noop",  # LLM layer disabled: infer=False on every add()
            },
        },
    }
    return Mem0Memory.from_config(config)


class MemoryEngine:
    """Thin facade over Mem0. Manages add/search/delete; does NOT handle metadata."""

    def __init__(self, mem0: Mem0Memory) -> None:
        self._mem0 = mem0
        self._score_is_distance = False  # updated by probe_score_scale()

    def probe_score_scale(self) -> None:
        """
        Chroma can return similarity (higher=better) or distance (lower=better).
        Probe by inserting a known text, querying with the same text, and checking
        whether the score is near 0 (distance) or near 1 (similarity).
        """
        probe_text = "probe: semantic scale detection"
        mem0_id: str | None = None
        try:
            add_result = self._mem0.add(
                probe_text,
                user_id=LORE_USER_ID,
                metadata={"lore_id": "__lorekeeper_probe__"},
                infer=False,
            )
            add_items = add_result.get("results") if isinstance(add_result, dict) else add_result
            mem0_id = add_items[0]["id"] if add_items else None

            results = self._mem0.search(probe_text, top_k=1, filters={"user_id": LORE_USER_ID})
            items = results.get("results") if isinstance(results, dict) else results
            if items:
                score = items[0].get("score", 0.5)
                self._score_is_distance = score < 0.1
                log.info(
                    "semantic_scale_probe",
                    score=score,
                    mode="distance" if self._score_is_distance else "similarity",
                )
        except Exception as e:
            log.warning("semantic_scale_probe_failed", error=str(e))
        finally:
            if mem0_id:
                try:
                    self._mem0.delete(mem0_id)
                except Exception:
                    pass

    def normalize_score(self, raw: float) -> float:
        if self._score_is_distance:
            return max(0.0, 1.0 - raw)
        return max(0.0, min(1.0, raw))

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
        """Insert verbatim (infer=False). Returns Mem0's internal id."""
        metadata = {"lore_id": lore_id, **(extra_metadata or {})}
        result = self._mem0.add(
            text,
            user_id=LORE_USER_ID,
            metadata=metadata,
            infer=False,
        )
        items = result.get("results") if isinstance(result, dict) else result
        if items:
            return items[0]["id"]
        return ""

    def search(self, query: str, limit: int = 200) -> list[dict]:
        """Returns list of {lore_id, mem0_id, score (normalized)}.

        Uses Chroma directly to avoid mem0 v2's broken scoring pipeline:
        mem0 passes cosine distances (lower=better) to score_and_rank as if
        they were similarities (higher=better), causing near-matches to be
        filtered out and unrelated items to score 1.0. We bypass that by
        embedding the query ourselves and querying Chroma with n_results.
        """
        embeddings = self._mem0.embedding_model.embed(query, "search")
        where_clause = self._mem0.vector_store._generate_where_clause({"user_id": LORE_USER_ID})
        try:
            n = min(limit, self._mem0.vector_store.collection.count())
        except Exception:
            n = limit
        if n == 0:
            return []
        raw = self._mem0.vector_store.collection.query(
            query_embeddings=[embeddings],
            n_results=n,
            where=where_clause,
            include=["distances", "metadatas"],
        )
        ids = raw.get("ids", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        out = []
        for mem0_id, dist, meta in zip(ids, distances, metadatas, strict=False):
            lore_id = (meta or {}).get("lore_id")
            if not lore_id:
                continue
            # Chroma cosine distance: 0=identical, 2=opposite. Clamp to [0, 1].
            similarity = max(0.0, min(1.0, 1.0 - dist))
            out.append({"lore_id": lore_id, "mem0_id": mem0_id, "score": similarity})
        # Sort by score descending (Chroma already returns sorted by distance ascending)
        out.sort(key=lambda x: x["score"], reverse=True)
        return out

    def get_all(self) -> list[dict]:
        """Returns all entries as {lore_id, mem0_id}. Used for BM25 rebuild."""
        results = self._mem0.get_all(filters={"user_id": LORE_USER_ID}, top_k=5000)
        items = results.get("results") if isinstance(results, dict) else results
        out = []
        for item in (items or []):
            meta = item.get("metadata") or {}
            lore_id = meta.get("lore_id")
            if lore_id:
                out.append({"lore_id": lore_id, "mem0_id": item["id"]})
        return out

    def delete_by_mem0_id(self, mem0_id: str) -> None:
        self._mem0.delete(mem0_id)


# ── LanceDB (direct, no Mem0) ────────────────────────────────────────────────


class LanceDBEngine:
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

    def _get_model(self):
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

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
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

    def search(self, query: str, limit: int = 200) -> list[dict]:
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

    def get_all(self) -> list[dict]:
        """Returns all entries as {lore_id, mem0_id}. Used for BM25 rebuild."""
        try:
            tbl = self._table.to_arrow()
        except Exception:
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

    def delete_by_mem0_id(self, mem0_id: str) -> None:
        """Delete a row by mem0_id."""
        escaped = mem0_id.replace("'", "''")
        self._table.delete(f"mem0_id = '{escaped}'")


# ── Factory ──────────────────────────────────────────────────────────────────


def build_engine(
    vector_store: str, chroma_path: Path, lancedb_path: str, embedding_model: str
) -> MemoryEngine | LanceDBEngine:
    """Factory: returns the appropriate engine based on vector_store config."""
    if vector_store == "lancedb":
        return LanceDBEngine(lancedb_path, embedding_model)
    # Default: Chroma
    mem0 = build_mem0(chroma_path, embedding_model)
    return MemoryEngine(mem0)
