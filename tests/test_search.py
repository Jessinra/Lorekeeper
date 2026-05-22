import pytest
from lorekeeper.config import Settings
from lorekeeper.models import Memory
from lorekeeper.services.search import rank_results

S = Settings()


def _mem(id: str, score: float = 5.0, soft_deleted: bool = False, usage: int = 0) -> Memory:
    return Memory(
        id=id, title=f"mem {id}", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
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
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.8}, {"lore_id": "c", "score": 0.7}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.0, include_deleted=False, refine_from=["b", "c"])
    ids = [r.memory.id for r in results]
    assert "a" not in ids
    assert "b" in ids
    assert "c" in ids


def test_refine_from_none_is_passthrough(mems):
    """refine_from=None gives identical behavior to omitting it."""
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.5}]
    kw = {"a": 0.8}
    r1 = rank_results(sem, kw, mems, {}, S, limit=10, min_score=0.1, include_deleted=False)
    r2 = rank_results(sem, kw, mems, {}, S, limit=10, min_score=0.1, include_deleted=False, refine_from=None)
    assert [r.memory.id for r in r1] == [r.memory.id for r in r2]


def test_refine_from_unknown_ids_silently_ignored(mems):
    """Unknown IDs in refine_from produce no error and no results for those IDs."""
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.0, include_deleted=False, refine_from=["a", "nonexistent-id"])
    ids = [r.memory.id for r in results]
    assert "a" in ids
    assert "nonexistent-id" not in ids


def test_refine_from_empty_list_returns_nothing(mems):
    """An empty refine_from list means no candidates — returns empty results."""
    sem = [{"lore_id": "a", "score": 0.9}]
    results = rank_results(sem, {}, mems, {}, S, limit=10, min_score=0.0, include_deleted=False, refine_from=[])
    assert results == []
