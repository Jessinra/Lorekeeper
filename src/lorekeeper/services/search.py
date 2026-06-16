import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lorekeeper.config import Settings
from lorekeeper.models import Memory, MemoryLink

# Valid sort_by values for lore_search.
VALID_SORT_BY: frozenset[str] = frozenset({"relevance", "recent", "frequent"})


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


def _parse_iso_utc(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp and return a UTC-aware datetime.

    Accepts naive strings (treated as UTC) and UTC-offset strings.
    Rejects non-UTC offsets with a clear ValueError.
    """
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    # Allow only UTC (offset == 0) — keeps handling simple and unambiguous.
    utcoff = dt.utcoffset()
    if utcoff is not None and utcoff.total_seconds() != 0:
        raise ValueError(
            f"Non-UTC timezone offset in timestamp {ts!r}. "
            "Pass UTC timestamps (e.g. '2026-06-01T00:00:00Z' or "
            "'2026-06-01T00:00:00+00:00')."
        )
    return dt


def _parse_filter_dt(value: str, field_name: str) -> datetime:
    """Validate and parse a timestamp filter value; raise ValueError on bad input."""
    try:
        return _parse_iso_utc(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO timestamp for {field_name!r}: {exc}") from exc


def rank_results(
    semantic_hits: list[dict[str, Any]],   # [{lore_id, score}]
    keyword_hits: dict[str, float],  # {lore_id: score}
    memories_by_id: dict[str, Memory],
    links_by_id: dict[str, list[MemoryLink]],
    settings: Settings,
    limit: int,
    min_score: float,
    include_deleted: bool,
    refine_from: list[str] | None = None,
    created_after: datetime | None = None,
    updated_after: datetime | None = None,
    sort_by: str = "relevance",
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

        # LKPR-61: timestamp pre-filters — applied in Python against the cache.
        if created_after is not None:
            try:
                mem_created = _parse_iso_utc(mem.created_at)
            except ValueError:
                continue
            if mem_created < created_after:
                continue
        if updated_after is not None:
            try:
                mem_updated = _parse_iso_utc(mem.updated_at)
            except ValueError:
                continue
            if mem_updated < updated_after:
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

    # LKPR-80: sort_by — default is relevance (combined_score DESC).
    if sort_by == "recent":
        results.sort(key=lambda r: _parse_iso_utc(r.memory.updated_at), reverse=True)
    elif sort_by == "frequent":
        results.sort(key=lambda r: r.memory.usage_count, reverse=True)
    else:
        results.sort(key=lambda r: r.combined_score, reverse=True)

    return results[:limit]
