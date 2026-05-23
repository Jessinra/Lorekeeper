import math
from dataclasses import dataclass
from datetime import UTC, datetime

from lorekeeper.config import Settings
from lorekeeper.models import Memory, MemoryLink


@dataclass
class SearchResult:
    memory: Memory
    combined_score: float
    semantic_score: float
    keyword_score: float
    links: list[MemoryLink]
    decay_factor: float = 1.0  # e^(-λ·days); 1.0 when decay disabled


def hybrid_score(
    semantic: float,
    keyword: float,
    memory_score: float,
    usage_count: int,
    settings: Settings,
) -> float:
    cap = settings.usage_normalisation_cap
    log_usage = math.log2(1 + usage_count) / math.log2(1 + cap) if usage_count > 0 else 0.0
    return (
        settings.w_semantic * semantic
        + settings.w_keyword * keyword
        + settings.w_memory * (memory_score / 10.0)
        + settings.w_usage * log_usage
    )


def time_decay(memory: Memory, lam: float) -> float:
    """Compute e^(-λ · days_since_last_used).

    Uses memory.last_used if set, falls back to memory.created_at.
    Returns 1.0 if λ == 0 (decay disabled).
    """
    if lam == 0.0:
        return 1.0
    ref_str = memory.last_used or memory.created_at
    try:
        ref_dt = datetime.fromisoformat(ref_str)
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        days = max((now - ref_dt).total_seconds() / 86400.0, 0.0)
    except (ValueError, TypeError):
        return 1.0
    return math.exp(-lam * days)


REFINE_FROM_CAP = 200


def rank_results(
    semantic_hits: list[dict],   # [{lore_id, score}]
    keyword_hits: dict[str, float],  # {lore_id: score}
    memories_by_id: dict[str, Memory],
    links_by_id: dict[str, list[MemoryLink]],
    settings: Settings,
    limit: int,
    min_score: float,
    include_deleted: bool,
    refine_from: list[str] | None = None,
) -> list[SearchResult]:
    if refine_from is not None:
        # Iterative narrowing: restrict candidates to the provided ID set
        allowed = set(refine_from)
        candidate_ids = allowed
        sem_map = {h["lore_id"]: h["score"] for h in semantic_hits if h["lore_id"] in allowed}
    else:
        # Union of candidate ids
        candidate_ids = {h["lore_id"] for h in semantic_hits} | set(keyword_hits)
        sem_map = {h["lore_id"]: h["score"] for h in semantic_hits}

    lam = settings.decay_lambda

    results = []
    for lore_id in candidate_ids:
        mem = memories_by_id.get(lore_id)
        if mem is None:
            continue
        if not include_deleted and mem.soft_deleted:
            continue
        sem = sem_map.get(lore_id, 0.0)
        kw = keyword_hits.get(lore_id, 0.0)
        combined = hybrid_score(sem, kw, mem.score, mem.usage_count, settings)
        if combined < min_score:
            continue
        decay = time_decay(mem, lam)
        final_score = combined * decay
        results.append(SearchResult(
            memory=mem,
            combined_score=final_score,
            semantic_score=sem,
            keyword_score=kw,
            links=links_by_id.get(lore_id, []),
            decay_factor=decay,
        ))

    results.sort(key=lambda r: r.combined_score, reverse=True)
    return results[:limit]
