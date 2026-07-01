"""Stage 1: Link candidate scorers + LinkCandidateGenerator tests (LKPR-58)."""

import math
from datetime import UTC, datetime
from unittest.mock import patch

import numpy as np
import pytest

from lorekeeper.domains.suggestion.candidate import (
    BM25Scorer,
    CosineScorer,
    EntityOverlapScorer,
    LinkCandidate,
    LinkCandidateGenerator,
    TemporalProximityScorer,
)
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from tests._helpers import build_service, build_stores

# ── Helpers ────────────────────────────────────────────────────────────────────


class FakeVectorEngine:
    """Stand-in for MemoryEngine — exposes get_embeddings_batch + search + add."""

    def __init__(self) -> None:
        self._vectors: dict[str, np.ndarray] = {}
        self._search_results: list[dict] = []
        self._store: dict[str, str] = {}

    def get_embeddings_batch(self, lore_ids: list[str]) -> dict[str, np.ndarray]:
        # Honour real contract: missing IDs are silently omitted
        return {lid: self._vectors[lid] for lid in lore_ids if lid in self._vectors}

    def search(self, query: str, limit: int = 200) -> list[dict]:
        return self._search_results[:limit]

    def add(self, text: str, lore_id: str, extra_metadata: dict | None = None) -> str:
        self._store[lore_id] = text
        return lore_id

    def probe_score_scale(self) -> None:
        pass

    def normalize_score(self, raw: float) -> float:
        return raw

    def get_all(self) -> list[dict]:
        return [{"lore_id": k, "mem0_id": k} for k in self._store]

    def find_vector_id(self, lore_id: str) -> str | None:
        return lore_id if lore_id in self._store else None


def _insert_memory(service, title: str, content: str) -> str:
    result = service.insert(memories=[{"title": title, "content": content}], links=[])
    return result["inserted_memories"][0]["id"]


def _rebuild_kw(service) -> None:
    """Populate the keyword index with current memories."""
    from lorekeeper.domains.memory.models import Memory
    all_rows = service.memories.all_memory_rows()
    mems = []
    for r in all_rows:
        mems.append(Memory(
            id=r["id"], title=r["title"], description=r["description"],
            content=r["content"], created_at=r["created_at"],
            updated_at=r["updated_at"], usage_count=r["usage_count"],
            score=r["score"], soft_deleted=bool(r["soft_deleted"]),
            confidence=r["confidence"], confidence_count=r["confidence_count"],
            namespace=r["namespace"],
        ))
    service._kw.rebuild(mems)


def _seed_vectors_from_content(engine: FakeVectorEngine, service) -> None:
    """Assign deterministic vectors to all memories based on content hash."""
    for row in service.memories.all_memory_rows():
        seed = sum(ord(c) for c in (row["content"] or ""))
        engine._vectors[row["id"]] = np.full(384, (seed % 100) / 100.0, dtype=np.float32)


# ── CosineScorer ──────────────────────────────────────────────────────────────


def test_cosine_scorer_identical_vectors() -> None:
    vec = np.ones(384, dtype=np.float32) / np.linalg.norm(np.ones(384))
    engine = FakeVectorEngine()
    engine._vectors = {"src": vec, "tgt": vec}
    scorer = CosineScorer(engine)  # type: ignore[arg-type]
    scores = scorer.score_batch("src", ["tgt"])
    assert scores["tgt"] == pytest.approx(1.0, abs=1e-4)


def test_cosine_scorer_orthogonal_vectors() -> None:
    src = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    tgt = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    engine = FakeVectorEngine()
    engine._vectors = {"src": src, "tgt": tgt}
    scorer = CosineScorer(engine)  # type: ignore[arg-type]
    scores = scorer.score_batch("src", ["tgt"])
    assert scores["tgt"] == pytest.approx(0.0, abs=1e-4)


def test_cosine_scorer_zero_vector_source() -> None:
    engine = FakeVectorEngine()
    engine._vectors = {
        "src": np.zeros(384, dtype=np.float32),
        "tgt": np.ones(384, dtype=np.float32),
    }
    scorer = CosineScorer(engine)  # type: ignore[arg-type]
    scores = scorer.score_batch("src", ["tgt"])
    assert scores == {}


def test_cosine_scorer_missing_candidate_vector() -> None:
    engine = FakeVectorEngine()
    engine._vectors["src"] = np.ones(384, dtype=np.float32) / np.linalg.norm(np.ones(384))
    scorer = CosineScorer(engine)  # type: ignore[arg-type]
    scores = scorer.score_batch("src", ["missing"])
    assert scores["missing"] == 0.0


def test_cosine_scorer_returns_all_candidates() -> None:
    engine = FakeVectorEngine()
    vec_a = np.array([1.0, 1.0, 0.0], dtype=np.float32)
    vec_a_norm = vec_a / np.linalg.norm(vec_a)
    engine._vectors = {"src": vec_a_norm, "t1": vec_a_norm, "t2": vec_a_norm}
    scorer = CosineScorer(engine)  # type: ignore[arg-type]
    scores = scorer.score_batch("src", ["t1", "t2"])
    assert set(scores.keys()) == {"t1", "t2"}


# ── BM25Scorer ─────────────────────────────────────────────────────────────────


class FakeKW:
    def __init__(self) -> None:
        self._normalized: dict[str, float] = {}

    def search_normalized(self, query: str) -> dict[str, float]:
        return dict(self._normalized)


def test_bm25_scorer_returns_given_scores() -> None:
    kw = FakeKW()
    kw._normalized = {"a": 0.8, "b": 0.3}
    scorer = BM25Scorer(kw)  # type: ignore[arg-type]
    scores = scorer.score_batch("query", ["a", "b"])
    assert scores["a"] == pytest.approx(0.8)
    assert scores["b"] == pytest.approx(0.3)


def test_bm25_scorer_unknown_id_gets_zero() -> None:
    kw = FakeKW()
    kw._normalized = {"a": 0.9}
    scorer = BM25Scorer(kw)  # type: ignore[arg-type]
    scores = scorer.score_batch("query", ["a", "unknown"])
    assert scores["a"] == 0.9
    assert scores["unknown"] == 0.0


# ── EntityOverlapScorer ────────────────────────────────────────────────────────


def test_entity_overlap_identical() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = True
    with patch.object(scorer, "_entities", side_effect=[{"alice", "acme"}, {"alice", "acme"}]):
        scores = scorer.score_batch("src", [("m1", "tgt")])
    assert scores["m1"] == pytest.approx(1.0)


def test_entity_overlap_no_overlap() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = True
    with patch.object(scorer, "_entities", side_effect=[{"alice"}, {"bob"}]):
        scores = scorer.score_batch("src", [("m1", "tgt")])
    assert scores["m1"] == pytest.approx(0.0)


def test_entity_overlap_partial() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = True
    with patch.object(scorer, "_entities", side_effect=[{"a", "b"}, {"a", "c"}]):
        scores = scorer.score_batch("src", [("m1", "tgt")])
    # Jaccard: {a,b} ∩ {a,c} / {a,b,c} = 1/3
    assert scores["m1"] == pytest.approx(1.0 / 3.0)


def test_entity_overlap_no_entities() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = True
    with patch.object(scorer, "_entities", side_effect=[set(), {"alice"}]):
        scores = scorer.score_batch("src", [("m1", "tgt")])
    assert scores["m1"] == 0.0


def test_entity_overlap_spacy_unavailable() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = False
    scores = scorer.score_batch("src", [("m1", "target text")])
    assert scores["m1"] == 0.0


def test_entity_overlap_empty_union_is_zero() -> None:
    scorer = EntityOverlapScorer()
    scorer._available = True
    with patch.object(scorer, "_entities", side_effect=[set(), set()]):
        scores = scorer.score_batch("src", [("m1", "tgt")])
    assert scores["m1"] == 0.0


# ── TemporalProximityScorer ────────────────────────────────────────────────────


def test_temporal_exact_match() -> None:
    now = datetime.now(UTC)
    scorer = TemporalProximityScorer(tau_days=30.0)
    scores = scorer.score_batch(now, [("m1", now)])
    assert scores["m1"] == pytest.approx(1.0)


def test_temporal_decays_with_distance() -> None:
    src = datetime(2026, 1, 1, tzinfo=UTC)
    far = datetime(2026, 6, 1, tzinfo=UTC)
    scorer = TemporalProximityScorer(tau_days=30.0)
    scores = scorer.score_batch(src, [("m1", far)])
    expected = math.exp(-151.0 / 30.0)
    assert scores["m1"] == pytest.approx(expected, abs=1e-3)


def test_temporal_none_source() -> None:
    scorer = TemporalProximityScorer(tau_days=30.0)
    scores = scorer.score_batch(None, [("m1", datetime.now(UTC))])
    assert scores["m1"] == 0.0


def test_temporal_none_candidate() -> None:
    scorer = TemporalProximityScorer(tau_days=30.0)
    scores = scorer.score_batch(datetime.now(UTC), [("m1", None)])
    assert scores["m1"] == 0.0


def test_temporal_naive_timezone_handling() -> None:
    src = datetime(2026, 1, 1)  # naive — treated as UTC
    tgt = datetime(2026, 1, 1, tzinfo=UTC)
    scorer = TemporalProximityScorer(tau_days=30.0)
    scores = scorer.score_batch(src, [("m1", tgt)])
    assert scores["m1"] == pytest.approx(1.0, abs=1e-3)


def test_temporal_tau_default() -> None:
    """Default tau_days is 30.0."""
    scorer = TemporalProximityScorer()
    assert scorer._td == 30.0


def test_temporal_zero_tau_does_not_crash() -> None:
    """Guard against div-by-zero in constructor."""
    scorer = TemporalProximityScorer(tau_days=0.0)
    src = datetime(2026, 1, 1, tzinfo=UTC)
    tgt = datetime(2026, 1, 2, tzinfo=UTC)
    scores = scorer.score_batch(src, [("m1", tgt)])
    # tau was clamped to 1.0, so decay is exp(-1/1) ≈ 0.368
    assert scores["m1"] == pytest.approx(math.exp(-1.0), abs=1e-3)


# ── LinkCandidateGenerator ─────────────────────────────────────────────────────


def test_generator_empty_when_source_not_found(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    assert gen.generate("nonexistent") == []


def test_generator_empty_when_no_vector_hits(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    _insert_memory(svc, "lonely", "unique isolated content")
    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    candidates = gen.generate(stores.memories.all_memory_rows()[0]["id"])
    assert candidates == []


def test_generator_filters_existing_links(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    src = _insert_memory(svc, "src", "content A")
    tgt = _insert_memory(svc, "tgt", "content A related")
    # Pre-link
    svc.links.insert_link(src, tgt, "references", "manual")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    candidates = gen.generate(src)
    assert not any(c.target_lore_id == tgt for c in candidates)


def test_generator_respects_score_threshold(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    settings.link_score_threshold = 9.0  # impossibly high
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    _insert_memory(svc, "src", "content")
    _insert_memory(svc, "tgt", "content related")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    candidates = gen.generate(stores.memories.all_memory_rows()[0]["id"])
    assert len(candidates) == 0


def test_generator_respects_top_m(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    settings.link_top_m = 2
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    src = _insert_memory(svc, "src", "common topic")
    for i in range(5):
        _insert_memory(svc, f"cand_{i}", f"common topic variant {i}")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    candidates = gen.generate(src)
    assert len(candidates) <= 2


def test_generator_links_for_memory_filter_bidirectional(tmp_path):
    """Links in both directions (src→tgt and tgt→src) should prevent recommendations."""
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    a = _insert_memory(svc, "a", "shared topic")
    b = _insert_memory(svc, "b", "shared topic too")
    c = _insert_memory(svc, "c", "shared topic also")
    # Link a←b and a→c
    svc.links.insert_link(a, b, "references", "pre-existing")
    svc.links.insert_link(c, a, "references", "pre-existing")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    candidates = gen.generate(a)
    assert not any(c.target_lore_id in (b, c) for c in candidates)


def test_generator_logs_warning_on_missing_source(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    gen = LinkCandidateGenerator(eng, stores.memories, stores.links, kw, settings)  # type: ignore[arg-type]
    with patch("lorekeeper.domains.suggestion.candidate.log.warning") as mock_warn:
        gen.generate("nope")
        assert mock_warn.called
        args, _ = mock_warn.call_args
        assert "link_candidate_source_not_found" in str(args)


# ── Pipeline integration via MemoryService.recommend_links() ───────────────────


def test_recommend_links_returns_link_candidates(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    src = _insert_memory(svc, "src", "important project concept")
    _insert_memory(svc, "tgt", "related project concept")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    candidates = svc.recommend_links(src)
    assert isinstance(candidates, list)
    if candidates:
        assert isinstance(candidates[0], LinkCandidate)
        assert candidates[0].source_lore_id == src
        assert candidates[0].weighted_score >= 0


def test_recommend_links_empty_when_no_matches(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    _insert_memory(svc, "only mem", "isolated unique content")
    candidates = svc.recommend_links(stores.memories.all_memory_rows()[0]["id"])
    assert candidates == []


def test_recommend_links_read_only_no_writes(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    src = _insert_memory(svc, "src", "content")
    _insert_memory(svc, "tgt", "content related")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    before = list(svc.links.all_links())
    svc.recommend_links(src)
    after = list(svc.links.all_links())
    assert len(before) == len(after)


def test_recommend_links_returns_top_k_override(tmp_path):
    stores = build_stores(tmp_path / "test.db")
    kw = KeywordIndex()
    settings = Settings()
    settings.link_top_m = 10  # default high
    eng = FakeVectorEngine()
    svc = build_service(stores, eng, kw, settings)
    src = _insert_memory(svc, "src", "versatile topic")
    for i in range(5):
        _insert_memory(svc, f"rel_{i}", f"versatile topic extension {i}")
    _rebuild_kw(svc)
    _seed_vectors_from_content(eng, svc)

    candidates = svc.recommend_links(src, top_k=2)
    assert len(candidates) <= 2


# ── Namespace isolation ────────────────────────────────────────────────────────


def test_recommend_links_does_not_surface_foreign_namespace_candidates(tmp_path):
    """A namespace-scoped service must not return candidates from a foreign namespace.

    Setup: insert one memory as 'agent-a', one as 'agent-b'. Build a service
    scoped to 'agent-a'. recommend_links on the agent-a memory must return no
    candidates because the only other memory is owned by 'agent-b'.
    """
    from lorekeeper.domains.link.repository import LinkStore
    from lorekeeper.domains.memory.repository import MemoryStore
    from lorekeeper.infra.database import Database

    db = Database(tmp_path / "ns.db")
    db.migrate()
    mem_store = MemoryStore(db)
    link_store = LinkStore(db)
    kw = KeywordIndex()
    eng = FakeVectorEngine()
    settings = Settings()
    settings.link_score_threshold = 0.0  # accept everything that passes

    # Insert source memory under namespace 'agent-a'
    import uuid
    from datetime import UTC, datetime

    ts = datetime.now(UTC).isoformat()
    src_id = str(uuid.uuid4())
    mem_store.upsert_memory_row(
        id=src_id, title="src-a", description="", content="project planning memory",
        created_at=ts, updated_at=ts, score=5.0, namespace="agent-a",
    )
    # Insert candidate under foreign namespace 'agent-b'
    foreign_id = str(uuid.uuid4())
    mem_store.upsert_memory_row(
        id=foreign_id, title="foreign-b", description="", content="project planning memory",
        created_at=ts, updated_at=ts, score=5.0, namespace="agent-b",
    )
    db.conn.commit()

    # Seed vectors — both get nearly identical vectors so cosine would return both
    eng._vectors[src_id] = np.full(384, 0.9, dtype=np.float32)
    eng._vectors[foreign_id] = np.full(384, 0.9, dtype=np.float32)
    eng._search_results = [
        {"lore_id": foreign_id, "score": 0.95},
    ]

    # Build a generator scoped to agent-a only
    generator = LinkCandidateGenerator(
        engine=eng,
        memory_store=mem_store,
        link_store=link_store,
        keyword_index=kw,
        settings=settings,
        ns_filter=["agent-a", "shared"],
    )

    # Source is in agent-a — should load fine
    # Candidate foreign_id is in agent-b — must be excluded by ns_filter
    candidates = generator.generate(src_id)
    candidate_ids = {c.target_lore_id for c in candidates}
    assert foreign_id not in candidate_ids, (
        "Foreign namespace candidate leaked through ns_filter"
    )


def test_generator_excludes_soft_deleted_candidates(tmp_path):
    """Soft-deleted memories must never appear as link candidates."""
    import uuid
    from datetime import UTC, datetime

    from lorekeeper.domains.link.repository import LinkStore
    from lorekeeper.domains.memory.repository import MemoryStore
    from lorekeeper.infra.database import Database

    db = Database(tmp_path / "sd.db")
    db.migrate()
    mem_store = MemoryStore(db)
    link_store = LinkStore(db)
    kw = KeywordIndex()
    eng = FakeVectorEngine()
    settings = Settings()
    settings.link_score_threshold = 0.0

    ts = datetime.now(UTC).isoformat()
    src_id = str(uuid.uuid4())
    live_id = str(uuid.uuid4())
    deleted_id = str(uuid.uuid4())

    mem_store.upsert_memory_row(
        id=src_id, title="source", description="", content="python async patterns",
        created_at=ts, updated_at=ts, score=5.0, namespace="shared",
    )
    mem_store.upsert_memory_row(
        id=live_id, title="live", description="", content="asyncio event loop",
        created_at=ts, updated_at=ts, score=5.0, namespace="shared",
    )
    mem_store.upsert_memory_row(
        id=deleted_id, title="deleted", description="", content="async def coroutine",
        created_at=ts, updated_at=ts, score=5.0, namespace="shared",
        soft_deleted=True,
    )
    db.conn.commit()

    # Both live and deleted get similar vectors — cosine would return both
    for mid in (src_id, live_id, deleted_id):
        eng._vectors[mid] = np.full(384, 0.8, dtype=np.float32)
    eng._search_results = [
        {"lore_id": live_id, "score": 0.9},
        {"lore_id": deleted_id, "score": 0.9},
    ]

    generator = LinkCandidateGenerator(
        engine=eng,
        memory_store=mem_store,
        link_store=link_store,
        keyword_index=kw,
        settings=settings,
        ns_filter=None,
    )

    candidates = generator.generate(src_id)
    candidate_ids = {c.target_lore_id for c in candidates}
    assert deleted_id not in candidate_ids, "Soft-deleted memory surfaced as link candidate"
    assert live_id in candidate_ids, "Live memory unexpectedly missing from candidates"


def test_generator_candidates_sorted_by_score_descending(tmp_path):
    """generate() must return candidates sorted by weighted_score descending."""
    import uuid
    from datetime import UTC, datetime

    from lorekeeper.domains.link.repository import LinkStore
    from lorekeeper.domains.memory.repository import MemoryStore
    from lorekeeper.infra.database import Database

    db = Database(tmp_path / "sort.db")
    db.migrate()
    mem_store = MemoryStore(db)
    link_store = LinkStore(db)
    kw = KeywordIndex()
    eng = FakeVectorEngine()
    settings = Settings()
    settings.link_score_threshold = 0.0
    settings.link_top_m = 10

    ts = datetime.now(UTC).isoformat()
    src_id = str(uuid.uuid4())
    mem_store.upsert_memory_row(
        id=src_id, title="source", description="", content="source memory",
        created_at=ts, updated_at=ts, score=5.0, namespace="shared",
    )

    # Insert 3 candidates with distinct content hashes → distinct cosine scores
    ids = []
    for i, content in enumerate(["aaa bbb ccc", "ddd eee fff", "ggg hhh iii"]):
        mid = str(uuid.uuid4())
        ids.append(mid)
        mem_store.upsert_memory_row(
            id=mid, title=f"cand-{i}", description="", content=content,
            created_at=ts, updated_at=ts, score=5.0, namespace="shared",
        )
    db.conn.commit()

    # Assign different magnitudes so cosine differs
    eng._vectors[src_id] = np.array([1.0] * 384, dtype=np.float32)
    eng._vectors[ids[0]] = np.array([0.9] * 384, dtype=np.float32)
    eng._vectors[ids[1]] = np.array([0.5] * 384, dtype=np.float32)
    eng._vectors[ids[2]] = np.array([0.1] * 384, dtype=np.float32)
    eng._search_results = [{"lore_id": mid, "score": 0.9} for mid in ids]

    generator = LinkCandidateGenerator(
        engine=eng,
        memory_store=mem_store,
        link_store=link_store,
        keyword_index=kw,
        settings=settings,
        ns_filter=None,
    )

    candidates = generator.generate(src_id)
    assert len(candidates) >= 2, "Need at least 2 candidates to test sort order"
    for i in range(len(candidates) - 1):
        assert candidates[i].weighted_score >= candidates[i + 1].weighted_score, (
            f"Candidates not sorted: [{i}]={candidates[i].weighted_score:.3f} "
            f"< [{i+1}]={candidates[i+1].weighted_score:.3f}"
        )

