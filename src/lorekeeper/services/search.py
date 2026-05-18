import math
from dataclasses import dataclass

from lorekeeper.config import Settings
from lorekeeper.models import Memory, MemoryLink


@dataclass
class SearchResult:
    memory: Memory
    combined_score: float
    semantic_score: float
    keyword_score: float
    links: list[MemoryLink]


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


def rank_results(
    semantic_hits: list[dict],   # [{lore_id, score}]
    keyword_hits: dict[str, float],  # {lore_id: score}
    memories_by_id: dict[str, Memory],
    links_by_id: dict[str, list[MemoryLink]],
    settings: Settings,
    limit: int,
    min_score: float,
    include_deleted: bool,
) -> list[SearchResult]:
    # Union of candidate ids
    candidate_ids = {h["lore_id"] for h in semantic_hits} | set(keyword_hits)
    sem_map = {h["lore_id"]: h["score"] for h in semantic_hits}

    results = []
    for lore_id in candidate_ids:
        mem = memories_by_id.get(lore_id)
        if mem is None:
            continue
        if not include_deleted and mem.soft_deleted:
            continue
        sem = sem_map.get(lore_id, 0.0)
        kw = keyword_hits.get(lore_id, 0.0)
        score = hybrid_score(sem, kw, mem.score, mem.usage_count, settings)
        if score < min_score:
            continue
        results.append(SearchResult(
            memory=mem,
            combined_score=score,
            semantic_score=sem,
            keyword_score=kw,
            links=links_by_id.get(lore_id, []),
        ))

    results.sort(key=lambda r: r.combined_score, reverse=True)
    return results[:limit]
