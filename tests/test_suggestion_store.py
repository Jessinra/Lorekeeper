"""LinkSuggestionStore tests (LKPR-99) — extracted from test_link_store.py."""

import pytest

from tests._helpers import build_stores


@pytest.fixture
def stores(tmp_path):
    s = build_stores(tmp_path / "test.db")
    ts = "2026-01-01T00:00:00+00:00"
    # Seed memory rows so FK constraints are satisfied
    for i in ("a", "b", "c"):
        s.memories.upsert_memory_row(
            id=i, title=f"mem-{i}", description="d", content="c",
            created_at=ts, updated_at=ts,
        )
    yield s
    s.db.close()


class TestLinkSuggestionStore:
    """LinkSuggestionStore CRUD tests (LKPR-99)."""

    def test_insert_and_retrieve_suggestion(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="Memory A", target_title="Memory B",
            weighted_score=0.85,
        )
        assert sug.id is not None
        assert sug.confidence == "standard"
        assert sug.status == "pending"
        fetched = stores.suggestions.get_suggestion(sug.id)
        assert fetched is not None
        assert fetched.source_memory_id == "a"
        assert fetched.target_memory_id == "b"

    def test_confidence_default_is_standard(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        assert sug.confidence == "standard"

    def test_high_confidence_explicit(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.95,
            confidence="high",
        )
        assert sug.confidence == "high"

    def test_canonical_pair_ordering(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="b", target_memory_id="a",
            source_title="B", target_title="A", weighted_score=0.5,
        )
        assert sug.source_memory_id == "a"
        assert sug.target_memory_id == "b"

    def test_upsert_replaces_existing_pair(self, stores):
        s1 = stores.suggestions.upsert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        s2 = stores.suggestions.upsert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A-updated", target_title="B-updated",
            weighted_score=0.9, confidence="high",
        )
        fetched = stores.suggestions.get_suggestion(s1.id)
        assert fetched is None
        assert s2.weighted_score == 0.9
        assert s2.confidence == "high"

    def test_get_suggestions_for_memory(self, stores):
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="c",
            source_title="A", target_title="C", weighted_score=0.6,
        )
        assert len(stores.suggestions.get_suggestions_for_memory("a")) == 2

    def test_get_suggestions_for_memory_with_status_filter(self, stores):
        s1 = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="c",
            source_title="A", target_title="C", weighted_score=0.6,
        )
        stores.suggestions.update_suggestion_status(s1.id, "accepted")
        assert len(stores.suggestions.get_suggestions_for_memory("a", status="accepted")) == 1
        assert len(stores.suggestions.get_suggestions_for_memory("a", status="pending")) == 1

    def test_update_suggestion_status(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        stores.suggestions.update_suggestion_status(sug.id, "accepted")
        assert stores.suggestions.get_suggestion(sug.id).status == "accepted"
        stores.suggestions.update_suggestion_status(sug.id, "rejected")
        assert stores.suggestions.get_suggestion(sug.id).status == "rejected"

    def test_delete_suggestion(self, stores):
        sug = stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        stores.suggestions.delete_suggestion(sug.id)
        assert stores.suggestions.get_suggestion(sug.id) is None

    def test_rejected_pairs(self, stores):
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
            status="rejected",
        )
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="c",
            source_title="A", target_title="C", weighted_score=0.5,
            status="pending",
        )
        rejected = stores.suggestions.rejected_pairs()
        assert ("a", "b") in rejected
        assert ("a", "c") not in rejected

    def test_pending_pairs(self, stores):
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
            status="pending",
        )
        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="c",
            source_title="A", target_title="C", weighted_score=0.5,
            status="rejected",
        )
        pending = stores.suggestions.pending_pairs()
        assert ("a", "b") in pending
        assert ("a", "c") not in pending

    def test_prune_expired(self, stores):
        from datetime import UTC, datetime, timedelta

        stores.suggestions.insert_suggestion(
            source_memory_id="a", target_memory_id="b",
            source_title="A", target_title="B", weighted_score=0.5,
        )
        old_ts = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        stores.db.conn.execute(
            "UPDATE link_suggestions SET updated_at=? WHERE source_memory_id=?",
            (old_ts, "a"),
        )
        stores.db.conn.commit()
        assert stores.suggestions.prune_expired(ttl_days=30) == 1
        assert len(stores.suggestions.get_suggestions_for_memory("a")) == 0
