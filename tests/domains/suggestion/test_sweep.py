"""SweepService integration tests (TestSweepLinks).

Relocated from tests/test_orchestrator.py (Step 6 of LKPR-105).
Uses real SQLite (via build_stores) + FakeEngine + real SweepService.
"""
import pytest

from lorekeeper.domains.suggestion.sweep import SweepService
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.settings import Settings
from tests._helpers import FakeEngine, build_app, build_stores


@pytest.fixture
def svc(tmp_path):
    store = build_stores(tmp_path / "test.db")
    engine = FakeEngine()
    kw = KeywordIndex()
    settings = Settings()
    yield build_app(store, engine, kw, settings), engine
    store.close()


class TestSweepLinks:
    """Sweep algorithm tests (LKPR-99) — uses SweepService + FakeEngine + real SQLite."""

    def _make_sweeper(self, service):
        from lorekeeper.domains.suggestion.repository import LinkSuggestionStore

        self._sug_store = LinkSuggestionStore(service.db)
        return SweepService(
            memory_store=service.memories,
            link_store=service.links,
            suggestion_store=self._sug_store,
            link_candidate_generator=service.link_candidate_generator,
            settings=service.settings,
            metrics_store=service.metrics,
            conn=service._conn,
        )

    def _seed_memories(self, service, engine):
        r = service.write_service.insert(memories=[
            {"title": "alpha", "description": "first", "content": "alpha about databases"},
            {"title": "beta", "description": "second", "content": "beta about caching"},
            {"title": "gamma", "description": "third", "content": "gamma about strategies"},
            {"title": "delta", "description": "fourth", "content": "delta about frameworks"},
        ], links=[])
        ids = [m["id"] for m in r["inserted_memories"]]
        engine._search_results = [
            {"lore_id": ids[1], "score": 0.85},
            {"lore_id": ids[2], "score": 0.75},
            {"lore_id": ids[0], "score": 0.65},
            {"lore_id": ids[3], "score": 0.30},
        ]
        return ids

    def test_sweep_generates_suggestions(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        self._seed_memories(service, engine)
        stats = sweeper.run()
        assert stats["memories_scanned"] == 4
        assert stats["candidates_generated"] >= 1
        pending = self._sug_store.get_pending_suggestions()
        assert len(pending) >= 1

    def test_sweep_creates_no_real_links(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        self._seed_memories(service, engine)
        before = len(service.links.all_links())
        sweeper.run()
        after = len(service.links.all_links())
        assert after == before

    def test_sweep_skips_already_linked(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        ids = self._seed_memories(service, engine)
        service.links.insert_link(
            source_memory_id=ids[0], target_memory_id=ids[1],
            relation_type="references", reason="test",
        )
        service.db.conn.commit()
        sweeper.run()
        pending = self._sug_store.get_pending_suggestions()
        assert len(pending) >= 1

    def test_sweep_skips_rejected_pairs(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        ids = self._seed_memories(service, engine)
        self._sug_store.insert_suggestion(
            source_memory_id=ids[0], target_memory_id=ids[1],
            source_title="", target_title="", weighted_score=0.0,
            status="rejected",
        )
        service.db.conn.commit()
        stats = sweeper.run()
        assert stats["skipped_rejected"] >= 1

    def test_sweep_skips_pending_pairs(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        ids = self._seed_memories(service, engine)
        sug = self._sug_store.insert_suggestion(
            source_memory_id=ids[0], target_memory_id=ids[1],
            source_title="", target_title="", weighted_score=0.0,
            status="pending",
        )
        original_id = sug.id
        service.db.conn.commit()
        stats = sweeper.run()
        assert stats["skipped_pending"] >= 1
        still = self._sug_store.get_suggestion(original_id)
        assert still is not None
        assert still.status == "pending"

    def test_sweep_stats_structure(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)
        self._seed_memories(service, engine)
        stats = sweeper.run()
        expected = {
            "memories_scanned", "candidates_generated", "high_confidence",
            "standard", "skipped_rejected", "skipped_pending", "skipped_linked", "expired_pruned",
        }
        assert set(stats.keys()) == expected

    def test_sweep_prunes_expired(self, svc):
        service, engine = svc
        sweeper = self._make_sweeper(service)

        # Verify the sweep calls prune_expired (stats key present).
        # Actual pruning behavior is tested in TestLinkSuggestionStore.
        self._seed_memories(service, engine)
        stats = sweeper.run()
        assert "expired_pruned" in stats
        assert isinstance(stats["expired_pruned"], int)
