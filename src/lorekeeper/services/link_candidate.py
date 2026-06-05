"""Stage 1 link candidate scoring — no LLM, no side-effects."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import numpy as np
import structlog

if TYPE_CHECKING:
    from lorekeeper.config import Settings
    from lorekeeper.services.keyword_index import KeywordIndex
    from lorekeeper.services.link_store import LinkStore
    from lorekeeper.services.memory_engine import MemoryEngine
    from lorekeeper.services.memory_store import MemoryStore

log = structlog.get_logger()


@dataclass
class LinkCandidate:
    source_lore_id: str
    target_lore_id: str
    cosine_score: float = 0.0
    bm25_score: float = 0.0
    entity_score: float = 0.0
    temporal_score: float = 0.0
    weighted_score: float = 0.0


class CosineScorer:
    """Cosine similarity using stored embeddings from the vector engine."""

    def __init__(self, engine: MemoryEngine) -> None:
        self._engine = engine

    def score_batch(self, source_id: str, candidate_ids: list[str]) -> dict[str, float]:
        """Cosine similarity between source and each candidate.

        Returns dict of {candidate_id: score}. Missing or zero-vector candidates
        get 0.0.
        """
        all_ids = [source_id, *candidate_ids]
        vecs = self._engine.get_embeddings_batch(all_ids)
        src = vecs.get(source_id)
        if src is None or np.linalg.norm(src) == 0:
            return {}
        src_norm = src / np.linalg.norm(src)
        out: dict[str, float] = {}
        for cid in candidate_ids:
            v = vecs.get(cid)
            if v is None or np.linalg.norm(v) == 0:
                out[cid] = 0.0
                continue
            out[cid] = float(np.dot(src_norm, v / np.linalg.norm(v)))
        return out


class BM25Scorer:
    """BM25 keyword similarity using the keyword index."""

    def __init__(self, keyword_index: KeywordIndex) -> None:
        self._kw = keyword_index

    def score_batch(self, source_content: str, candidate_ids: list[str]) -> dict[str, float]:
        """Use source content as BM25 query, return normalized scores for candidates."""
        scores = self._kw.search_normalized(source_content)
        return {cid: scores.get(cid, 0.0) for cid in candidate_ids}


class EntityOverlapScorer:
    """Named entity overlap using spaCy. Degrades gracefully if spaCy not installed."""

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self._nlp: Any = None
        self._model_name = model_name
        self._available = False
        try:
            import spacy  # noqa: F401

            self._available = True
        except ImportError:
            log.info(
                "spacy_not_installed",
                scorer="EntityOverlapScorer",
                note="scores will be 0.0",
            )

    def _get_nlp(self) -> Any:
        if self._nlp is None and self._available:
            import spacy

            try:
                self._nlp = spacy.load(self._model_name)
            except OSError:
                log.warning(
                    "spacy_model_not_found",
                    model=self._model_name,
                    note="run: python -m spacy download en_core_web_sm",
                )
                self._available = False
        return self._nlp

    def _entities(self, text: str) -> set[str]:
        nlp = self._get_nlp()
        if nlp is None:
            return set()
        doc = nlp(text)
        return {ent.text.lower() for ent in doc.ents}

    def score_batch(
        self, source_text: str, candidates: list[tuple[str, str]]
    ) -> dict[str, float]:
        """candidates: list of (lore_id, content). Returns Jaccard overlap scores."""
        if not self._available:
            return {lore_id: 0.0 for lore_id, _ in candidates}
        src_ents = self._entities(source_text)
        out: dict[str, float] = {}
        for lore_id, text in candidates:
            cand_ents = self._entities(text)
            union = src_ents | cand_ents
            if not union:
                out[lore_id] = 0.0
            else:
                out[lore_id] = len(src_ents & cand_ents) / len(union)
        return out


class TemporalProximityScorer:
    """Exponential decay by time delta. score = exp(-|Δdays| / tau)."""

    def __init__(self, tau_days: float = 30.0) -> None:
        self._td = tau_days if tau_days > 0 else 1.0  # prevent div-by-zero

    def score_batch(
        self,
        source_created: datetime | None,
        candidates: list[tuple[str, datetime | None]],
    ) -> dict[str, float]:
        out: dict[str, float] = {}
        if source_created is None:
            return {lore_id: 0.0 for lore_id, _ in candidates}
        # Ensure timezone-awareness
        src = (
            source_created.replace(tzinfo=UTC)
            if source_created.tzinfo is None
            else source_created
        )
        for lore_id, cand_created in candidates:
            if cand_created is None:
                out[lore_id] = 0.0
                continue
            c = (
                cand_created.replace(tzinfo=UTC)
                if cand_created.tzinfo is None
                else cand_created
            )
            delta_days = abs((src - c).total_seconds()) / 86400.0
            out[lore_id] = math.exp(-delta_days / self._td)
        return out


class LinkCandidateGenerator:
    """Orchestrates Stage 1: cosine pre-filter → all scorers → weighted combination → top-M."""

    def __init__(
        self,
        engine: MemoryEngine,
        memory_store: MemoryStore,
        link_store: LinkStore,
        keyword_index: KeywordIndex,
        settings: Settings,
        ns_filter: list[str] | None = None,
    ) -> None:
        self._engine = engine
        self._memory_store = memory_store
        self._link_store = link_store
        self._cosine = CosineScorer(engine)
        self._bm25 = BM25Scorer(keyword_index)
        self._entity = EntityOverlapScorer(settings.link_spacy_model)
        self._temporal = TemporalProximityScorer(settings.link_temporal_tau_days)
        self._settings = settings
        self._ns_filter = ns_filter

    def _existing_linked_ids(self, lore_id: str) -> set[str]:
        """Return set of memory IDs already linked to this memory (both directions)."""
        links = self._link_store.links_for_memory(lore_id)
        linked: set[str] = set()
        for link in links:
            linked.add(link.source_memory_id)
            linked.add(link.target_memory_id)
        return linked

    def generate(self, source_lore_id: str) -> list[LinkCandidate]:
        """Run Stage 1. Returns top-M candidates sorted by weighted_score descending."""
        s = self._settings

        # 1. Load source memory
        source = self._memory_store.get_memory_row(source_lore_id, namespaces=self._ns_filter)
        if source is None:
            log.warning("link_candidate_source_not_found", lore_id=source_lore_id)
            return []

        # 2. Cosine pre-filter: top-K most similar by vector search
        sem_hits = self._engine.search(source["content"], limit=s.link_top_k + 1)
        candidate_ids = [
            h["lore_id"]
            for h in sem_hits
            if h["lore_id"] != source_lore_id
        ][: s.link_top_k]

        if not candidate_ids:
            return []

        # 3. Exclude already-linked pairs
        existing = self._existing_linked_ids(source_lore_id)
        candidate_ids = [cid for cid in candidate_ids if cid not in existing]
        if not candidate_ids:
            return []

        # 4. Load candidate content from SQLite (namespace-scoped)
        rows = self._memory_store.get_memory_rows(candidate_ids, namespaces=self._ns_filter)
        candidates_map = {r["id"]: r for r in rows}

        # Drop candidates not found in this namespace (vector index can return cross-ns hits)
        candidate_ids = [cid for cid in candidate_ids if cid in candidates_map]
        if not candidate_ids:
            return []

        # 5. Parse timestamps — SQLite stores ISO strings
        def _parse_dt(val: str | None) -> datetime | None:
            if val is None:
                return None
            try:
                dt = datetime.fromisoformat(val)
                return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
            except (ValueError, TypeError):
                return None

        source_dt = _parse_dt(source["created_at"])

        cand_with_dt = [
            (cid, _parse_dt(candidates_map[cid]["created_at"]) if cid in candidates_map else None)
            for cid in candidate_ids
        ]
        cand_with_text = [
            (cid, candidates_map[cid]["content"]) if cid in candidates_map else (cid, "")
            for cid in candidate_ids
        ]

        # 6. Run all scorers
        cosine_scores = self._cosine.score_batch(source_lore_id, candidate_ids)
        bm25_scores = self._bm25.score_batch(source["content"], candidate_ids)
        entity_scores = self._entity.score_batch(source["content"], cand_with_text)
        temporal_scores = self._temporal.score_batch(source_dt, cand_with_dt)

        # 7. Weighted combination
        w = (
            s.link_weight_cosine,
            s.link_weight_bm25,
            s.link_weight_entity,
            s.link_weight_temporal,
        )
        candidates: list[LinkCandidate] = []
        for cid in candidate_ids:
            c = cosine_scores.get(cid, 0.0)
            b = bm25_scores.get(cid, 0.0)
            e = entity_scores.get(cid, 0.0)
            t = temporal_scores.get(cid, 0.0)
            weighted = w[0] * c + w[1] * b + w[2] * e + w[3] * t
            if weighted < s.link_score_threshold:
                continue
            candidates.append(
                LinkCandidate(
                    source_lore_id=source_lore_id,
                    target_lore_id=cid,
                    cosine_score=c,
                    bm25_score=b,
                    entity_score=e,
                    temporal_score=t,
                    weighted_score=weighted,
                )
            )

        # 8. Sort and return top-M
        candidates.sort(key=lambda x: x.weighted_score, reverse=True)
        return candidates[: s.link_top_m]
