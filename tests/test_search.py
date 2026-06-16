"""Unit tests for the hybrid search ranking engine.

Tests the pure rank_results function — no database, no orchestrator.
"""
import pytest

from lorekeeper.config import Settings
from lorekeeper.models import Memory
from lorekeeper.services.search import _parse_iso_utc, rank_results

S = Settings()


def _mem(
    id: str,
    score: float = 5.0,
    soft_deleted: bool = False,
    usage: int = 0,
    created_at: str = "2026-01-01T00:00:00+00:00",
    updated_at: str = "2026-01-01T00:00:00+00:00",
) -> Memory:
    return Memory(
        id=id, title=f"mem {id}", description="d", content="c",
        created_at=created_at,
        updated_at=updated_at,
        score=score,
        soft_deleted=soft_deleted,
        usage_count=usage,
    )


@pytest.fixture
def mems():
    return {m.id: m for m in [_mem("a"), _mem("b"), _mem("c")]}


def test_returns_ranked_results(mems):
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.3}]
    kw = {"a": 0.8}
    results = rank_results(sem, kw, mems, {}, S, limit=10, min_score=0.1, include_deleted=False)
    assert results[0].memory.id == "a"
    assert results[0].combined_score > results[1].combined_score


def test_min_score_filters(mems):
    sem = [{"lore_id": "a", "score": 0.01}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.5, include_deleted=False)
    assert len(results) == 0


def test_limit_truncates(mems):
    sem = [{"lore_id": m, "score": 0.9} for m in ["a", "b", "c"]]
    results = rank_results(sem, {}, mems, {}, S, limit=2, min_score=0.0, include_deleted=False)
    assert len(results) == 2


def test_excludes_soft_deleted_by_default():
    mems = {"a": _mem("a", soft_deleted=True), "b": _mem("b")}
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.5}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.0, include_deleted=False)
    ids = [r.memory.id for r in results]
    assert "a" not in ids
    assert "b" in ids


def test_include_deleted_returns_soft_deleted():
    mems = {"a": _mem("a", soft_deleted=True)}
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.0, include_deleted=True)
    assert len(results) == 1


# ── refine_from tests ────────────────────────────────────────────────────────

def test_refine_from_restricts_candidates(mems):
    """refine_from limits results to the provided ID set."""
    sem = [
        {"lore_id": "a", "score": 0.9},
        {"lore_id": "b", "score": 0.8},
        {"lore_id": "c", "score": 0.7},
    ]
    results = rank_results(
        sem, {}, mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False, refine_from=["b", "c"],
    )
    ids = [r.memory.id for r in results]
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids


def test_refine_from_none_is_passthrough(mems):
    """refine_from=None gives identical behavior to omitting it."""
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.5}]
    kw = {"a": 0.8}
    r1 = rank_results(sem, kw, mems, {}, S, limit=10, min_score=0.1, include_deleted=False)
    r2 = rank_results(
        sem, kw, mems, {}, S,
        limit=10, min_score=0.1, include_deleted=False, refine_from=None,
    )
    assert [r.memory.id for r in r1] == [r.memory.id for r in r2]


def test_refine_from_unknown_ids_silently_ignored(mems):
    """Unknown IDs in refine_from produce no error and no results for those IDs."""
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(
        sem, {}, mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        refine_from=["a", "nonexistent-id"],
    )
    ids = [r.memory.id for r in results]
    assert "a" in ids
    assert "nonexistent-id" not in ids


def test_refine_from_empty_list_returns_nothing(mems):
    """An empty refine_from list means no candidates — returns empty results."""
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(
        sem, {}, mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False, refine_from=[],
    )
    assert results == []


# ── LKPR-61: created_after / updated_after filter tests ─────────────────────

@pytest.fixture
def time_mems():
    """Three memories at different timestamps."""
    return {
        "old": _mem("old",
                    created_at="2026-01-01T00:00:00+00:00",
                    updated_at="2026-01-01T00:00:00+00:00"),
        "mid": _mem("mid",
                    created_at="2026-03-01T00:00:00+00:00",
                    updated_at="2026-03-01T00:00:00+00:00"),
        "new": _mem("new",
                    created_at="2026-06-01T00:00:00+00:00",
                    updated_at="2026-06-15T00:00:00+00:00"),
    }


def _sem_all(mems: dict) -> list[dict]:
    return [{"lore_id": k, "score": 0.9} for k in mems]


def test_created_after_filters_older_memories(time_mems):
    cutoff = _parse_iso_utc("2026-02-01T00:00:00")
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        created_after=cutoff,
    )
    ids = {r.memory.id for r in results}
    assert "old" not in ids
    assert "mid" in ids
    assert "new" in ids


def test_created_after_exact_boundary_is_inclusive(time_mems):
    """created_after=T returns memories where created_at >= T (inclusive)."""
    cutoff = _parse_iso_utc("2026-03-01T00:00:00+00:00")
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        created_after=cutoff,
    )
    ids = {r.memory.id for r in results}
    assert "mid" in ids   # exactly at boundary — included
    assert "old" not in ids


def test_updated_after_filters_by_updated_at(time_mems):
    cutoff = _parse_iso_utc("2026-06-01T00:00:00")
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        updated_after=cutoff,
    )
    ids = {r.memory.id for r in results}
    # "new" has updated_at="2026-06-15" — passes; "mid" has "2026-03-01" — filtered
    assert "new" in ids
    assert "mid" not in ids
    assert "old" not in ids


def test_created_after_and_updated_after_compose(time_mems):
    """Both filters are AND'd — only memories passing both are returned."""
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        created_after=_parse_iso_utc("2026-02-01T00:00:00"),
        updated_after=_parse_iso_utc("2026-06-01T00:00:00"),
    )
    ids = {r.memory.id for r in results}
    assert ids == {"new"}


def test_no_timestamp_filter_unchanged_behavior(mems):
    """Omitting both filters gives identical results to the current default."""
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.5}]
    r1 = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.1, include_deleted=False)
    r2 = rank_results(
        sem, {}, mems, {}, S,
        limit=10, min_score=0.1, include_deleted=False,
        created_after=None, updated_after=None,
    )
    assert [r.memory.id for r in r1] == [r.memory.id for r in r2]


def test_timestamp_filter_composes_with_min_score(time_mems):
    """min_score is still applied even when timestamp filter is active."""
    cutoff = _parse_iso_utc("2026-02-01T00:00:00")
    # Use sem=1.0 for "new" so hybrid_score clears min_score=0.5 (sem=0.9 only gets ~0.48)
    sem = [{"lore_id": "mid", "score": 0.01}, {"lore_id": "new", "score": 1.0}]
    results = rank_results(
        sem, {}, time_mems, {}, S,
        limit=10, min_score=0.5, include_deleted=False,
        created_after=cutoff,
    )
    ids = {r.memory.id for r in results}
    assert "mid" not in ids   # filtered by min_score
    assert "new" in ids


def test_timestamp_filter_composes_with_refine_from(time_mems):
    """created_after + refine_from are AND'd."""
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        created_after=_parse_iso_utc("2026-02-01T00:00:00"),
        refine_from=["old", "mid"],  # excludes "new" via refine_from
    )
    ids = {r.memory.id for r in results}
    assert ids == {"mid"}


# ── LKPR-80: sort_by tests ───────────────────────────────────────────────────

@pytest.fixture
def sort_mems():
    return {
        "a": _mem("a", usage=10, updated_at="2026-06-01T00:00:00+00:00"),
        "b": _mem("b", usage=5,  updated_at="2026-06-10T00:00:00+00:00"),
        "c": _mem("c", usage=1,  updated_at="2026-06-05T00:00:00+00:00"),
    }


def _sem_equal(mems: dict) -> list[dict]:
    """All memories with equal semantic scores so sort_by is the tiebreaker."""
    return [{"lore_id": k, "score": 0.9} for k in mems]


def test_sort_by_relevance_is_default(sort_mems):
    """sort_by='relevance' (default) ranks by combined_score DESC."""
    sem = [
        {"lore_id": "a", "score": 0.9},
        {"lore_id": "b", "score": 0.5},
        {"lore_id": "c", "score": 0.3},
    ]
    r1 = rank_results(sem, {}, sort_mems, {}, S, limit=10, min_score=0.0, include_deleted=False)
    r2 = rank_results(
        sem, {}, sort_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False, sort_by="relevance",
    )
    assert [r.memory.id for r in r1] == [r.memory.id for r in r2]
    assert r1[0].memory.id == "a"


def test_sort_by_recent_orders_by_updated_at_desc(sort_mems):
    results = rank_results(
        _sem_equal(sort_mems), {}, sort_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        sort_by="recent",
    )
    ids = [r.memory.id for r in results]
    # "b" updated 2026-06-10, "c" 2026-06-05, "a" 2026-06-01
    assert ids[0] == "b"
    assert ids[1] == "c"
    assert ids[2] == "a"


def test_sort_by_frequent_orders_by_usage_count_desc(sort_mems):
    results = rank_results(
        _sem_equal(sort_mems), {}, sort_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        sort_by="frequent",
    )
    ids = [r.memory.id for r in results]
    # usage: a=10, b=5, c=1
    assert ids[0] == "a"
    assert ids[1] == "b"
    assert ids[2] == "c"


def test_sort_by_unknown_raises_at_handler_layer():
    """sort_by validation is done at handler layer — tested in test_handlers.py."""
    # rank_results itself doesn't validate — falls back to relevance sort.
    # This documents the intended split: handler validates, rank_results trusts.
    mems = {"a": _mem("a")}
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(
        sem, {}, mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False, sort_by="bogus",
    )
    assert len(results) == 1  # falls through to relevance sort silently


def test_sort_by_recent_composes_with_created_after(time_mems):
    """Timestamp filter narrows the pool; sort_by='recent' orders the survivors."""
    results = rank_results(
        _sem_all(time_mems), {}, time_mems, {}, S,
        limit=10, min_score=0.0, include_deleted=False,
        created_after=_parse_iso_utc("2026-02-01T00:00:00"),
        sort_by="recent",
    )
    ids = [r.memory.id for r in results]
    # "old" filtered out; "new" (updated_at=2026-06-15) before "mid" (updated_at=2026-03-01)
    assert "old" not in ids
    assert ids[0] == "new"


def test_sort_by_frequent_composes_with_limit(sort_mems):
    """limit applies after sort — returns top-N by usage_count."""
    results = rank_results(
        _sem_equal(sort_mems), {}, sort_mems, {}, S,
        limit=2, min_score=0.0, include_deleted=False,
        sort_by="frequent",
    )
    assert len(results) == 2
    assert results[0].memory.id == "a"   # usage=10
    assert results[1].memory.id == "b"   # usage=5

