"""Unit tests for LanceDBEngine — insert + search validation."""

import pathlib
import tempfile

import pytest

from lorekeeper.config import Settings
from lorekeeper.services.lancedb_engine import LanceDBEngine


@pytest.fixture(scope="module")
def lancedb_engine():
    """Shared LanceDB engine seeded with semantically distinct memories."""
    s = Settings()
    tmpdir = pathlib.Path(tempfile.mkdtemp())
    engine = LanceDBEngine(str(tmpdir / "lancedb"), s.embedding_model)

    seeds = [
        ("Python is a programming language used for data science and ML", "id-python"),
        ("The sky is blue, clouds are white and fluffy", "id-sky"),
        ("Quarterly financial report: revenue and budget analysis", "id-finance"),
    ]
    for text, lid in seeds:
        engine.add(text, lid)

    return engine


class TestLanceDBSearch:
    """Search scoring tests — mirrors test_chromadb_engine.py structure."""

    def test_exact_match_scores_highest(self, lancedb_engine):
        results = lancedb_engine.search("Python programming language data science")
        top = results[0]
        assert top["lore_id"] == "id-python"
        assert top["score"] > 0.4, f"Expected real similarity, got {top['score']}"

    def test_unrelated_query_scores_low(self, lancedb_engine):
        results = lancedb_engine.search("quantum entanglement physics experiment")
        for r in results:
            assert r["score"] < 0.7, (
                f"Unrelated query returned high score {r['score']} for '{r['lore_id']}'"
            )

    def test_scores_not_uniformly_one(self, lancedb_engine):
        results = lancedb_engine.search("Python data science")
        assert len(results) >= 2, "Need at least 2 results"
        scores = [r["score"] for r in results]
        assert max(scores) - min(scores) > 0.1, f"All scores near-identical: {scores}"

    def test_scores_in_valid_range(self, lancedb_engine):
        results = lancedb_engine.search("any query")
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"

    def test_results_sorted_descending(self, lancedb_engine):
        results = lancedb_engine.search("financial report budget")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), f"Not sorted: {scores}"

    def test_empty_store_returns_empty(self):
        s = Settings()
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        engine = LanceDBEngine(str(tmpdir / "lancedb"), s.embedding_model)
        assert engine.search("anything") == []

    def test_relevant_beats_irrelevant(self, lancedb_engine):
        results = lancedb_engine.search("financial budget revenue")
        by_id = {r["lore_id"]: r["score"] for r in results}
        if "id-finance" in by_id and "id-sky" in by_id:
            assert by_id["id-finance"] > by_id["id-sky"], (
                f"Finance ({by_id['id-finance']:.3f}) should beat sky "
                f"({by_id['id-sky']:.3f}) for financial query"
            )
