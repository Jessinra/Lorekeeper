"""
Unit tests for MemoryEngine.search() scoring correctness.

These tests verify the fix for LKPR-16: mem0 v2 + Chroma 1.5.x returned
score=1.0 for ALL memories regardless of relevance, because Chroma cosine
distances (0=identical) were passed through mem0's scoring pipeline as if
they were similarities (1=identical).

The fix queries Chroma directly and converts: similarity = 1.0 - distance.
"""
import os
import pathlib
import tempfile

import pytest

os.environ.setdefault("MEM0_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

from lorekeeper.config import Settings
from lorekeeper.services.chromadb_engine import LORE_USER_ID, ChromaDBEngine, build_mem0


@pytest.fixture(scope="module")
def engine_with_memories():
    """Shared engine seeded with 3 semantically distinct memories."""
    s = Settings()
    tmpdir = pathlib.Path(tempfile.mkdtemp())
    mem0 = build_mem0(tmpdir / "chroma", s.embedding_model)
    engine = ChromaDBEngine(mem0)

    seeds = [
        ("Python is a programming language used for data science and ML", "id-python"),
        ("The sky is blue, clouds are white and fluffy", "id-sky"),
        ("Quarterly financial report: revenue and budget analysis", "id-finance"),
    ]
    for text, lid in seeds:
        mem0.add(text, user_id=LORE_USER_ID, metadata={"lore_id": lid}, infer=False)

    return engine


class TestSearchScoring:
    def test_exact_match_scores_highest(self, engine_with_memories):
        """The most relevant memory should rank first and score meaningfully high."""
        results = engine_with_memories.search("Python programming language data science")
        top = results[0]
        assert top["lore_id"] == "id-python"
        # all-MiniLM-L6-v2 paraphrase similarity is typically 0.5–0.8;
        # must be substantially above random (> 0.4) and rank first
        assert top["score"] > 0.4, f"Expected a real similarity score, got {top['score']}"

    def test_unrelated_query_scores_low(self, engine_with_memories):
        """A query unrelated to all seeded memories should return low scores, not 1.0."""
        results = engine_with_memories.search("quantum entanglement physics experiment")
        for r in results:
            assert r["score"] < 0.7, (
                f"Unrelated query returned suspiciously high score {r['score']} "
                f"for '{r['lore_id']}' — likely the LKPR-16 distance/similarity bug"
            )

    def test_scores_not_uniformly_one(self, engine_with_memories):
        """
        Core regression test for LKPR-16.
        Before the fix, every result scored 1.0 regardless of relevance.
        After the fix, scores must vary across semantically different memories.
        """
        results = engine_with_memories.search("Python data science")
        assert len(results) >= 2, "Need at least 2 results to check variance"
        scores = [r["score"] for r in results]
        assert max(scores) - min(scores) > 0.1, (
            f"All scores are near-identical {scores} — "
            "likely LKPR-16 regression (all distances mapped to 1.0)"
        )

    def test_scores_in_valid_range(self, engine_with_memories):
        """All scores must be in [0.0, 1.0]."""
        results = engine_with_memories.search("any query")
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"

    def test_results_sorted_descending(self, engine_with_memories):
        """Results must be sorted by score descending."""
        results = engine_with_memories.search("financial report budget")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), f"Results not sorted: {scores}"

    def test_empty_store_returns_empty(self):
        """Searching an empty store returns []."""
        s = Settings()
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        mem0 = build_mem0(tmpdir / "chroma", s.embedding_model)
        engine = ChromaDBEngine(mem0)
        assert engine.search("anything") == []

    def test_relevant_beats_irrelevant(self, engine_with_memories):
        """
        The memory most relevant to the query should score higher than
        a clearly unrelated one. Validates relative ordering.
        """
        results = engine_with_memories.search("financial budget revenue")
        by_id = {r["lore_id"]: r["score"] for r in results}

        if "id-finance" in by_id and "id-sky" in by_id:
            assert by_id["id-finance"] > by_id["id-sky"], (
                f"Finance memory ({by_id['id-finance']:.3f}) should outscore "
                f"sky memory ({by_id['id-sky']:.3f}) for a financial query"
            )
