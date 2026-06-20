"""LinkStore tests — post-LKPR-51 decomposition.

LinkStore now owns only link CRUD; memory rows are seeded through MemoryStore
(via the shared Database).
"""

import sqlite3

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


def test_insert_and_retrieve_link(stores):
    link = stores.links.insert_link("a", "b", "references", "they are related")
    assert link.id
    assert link.source_memory_id == "a"
    assert link.target_memory_id == "b"

    fetched = stores.links.get_link(link.id)
    assert fetched is not None
    assert fetched.id == link.id


def test_links_for_memory_bidirectional(stores):
    stores.links.insert_link("a", "b", "references", "a→b")
    stores.links.insert_link("c", "a", "part_of", "c→a")

    links = stores.links.links_for_memory("a")
    assert len(links) == 2


def test_fk_rejects_missing_memory(stores):
    with pytest.raises(sqlite3.IntegrityError):
        stores.links.insert_link("a", "nonexistent", "references", "bad link")


def test_update_link_score(stores):
    link = stores.links.insert_link("a", "b", "references", "r")
    stores.links.update_link_fields(link.id, score=5.0)
    updated = stores.links.get_link(link.id)
    assert updated is not None
    assert updated.score == 5.0


def test_cascade_delete(stores):
    """Deleting a memory cascades to remove links referencing it.

    Crosses MemoryStore + LinkStore — kept here because it verifies the FK
    cascade semantics of the link table.
    """
    link = stores.links.insert_link("a", "b", "references", "r")
    stores.memories.delete_memory_row("a")
    assert stores.links.get_link(link.id) is None


def test_upsert_memory_row_updates(stores):
    """Sanity check that MemoryStore upsert still updates fields correctly.

    Lives here historically — could move to test_memory_store.py in a follow-up.
    """
    ts = "2026-01-01T00:00:00+00:00"
    stores.memories.upsert_memory_row(
        id="a", title="updated", description="d2", content="c2",
        created_at=ts,
        updated_at="2026-01-02T00:00:00+00:00",
        score=7.0,
    )
    row = stores.memories.get_memory_row("a")
    assert row["title"] == "updated"
    assert row["score"] == 7.0


def test_all_memory_rows_excludes_deleted(stores):
    stores.memories.update_memory_fields("a", soft_deleted=1)
    rows = stores.memories.all_memory_rows(include_deleted=False)
    ids = [r["id"] for r in rows]
    assert "a" not in ids
    assert "b" in ids

    all_rows = stores.memories.all_memory_rows(include_deleted=True)
    assert len(all_rows) == 3


def test_upsert_memory_row_stores_namespace(tmp_path):
    s = build_stores(tmp_path / "ns.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="x", title="mem-x", description="d", content="c",
        created_at=ts, updated_at=ts, namespace="diana",
    )
    row = s.memories.get_memory_row("x")
    assert row is not None
    assert row["namespace"] == "diana"
    s.db.close()


def test_upsert_defaults_namespace_to_shared(tmp_path):
    s = build_stores(tmp_path / "ns2.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="y", title="mem-y", description="d", content="c",
        created_at=ts, updated_at=ts,
    )
    row = s.memories.get_memory_row("y")
    assert row is not None
    assert row["namespace"] == "shared"
    s.db.close()


def test_upsert_does_not_overwrite_namespace(tmp_path):
    """ON CONFLICT update must not clobber the existing namespace."""
    s = build_stores(tmp_path / "ns3.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="z", title="mem-z", description="d", content="c",
        created_at=ts, updated_at=ts, namespace="diana",
    )
    # Re-upsert with default namespace — should NOT overwrite
    s.memories.upsert_memory_row(
        id="z", title="mem-z-updated", description="d2", content="c2",
        created_at=ts,
        updated_at="2026-01-02T00:00:00+00:00",
    )
    row = s.memories.get_memory_row("z")
    assert row is not None
    assert row["namespace"] == "diana"  # preserved
    assert row["title"] == "mem-z-updated"  # other fields updated
    s.db.close()


def test_all_memory_rows_namespace_filter(tmp_path):
    s = build_stores(tmp_path / "ns4.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="1", title="m1", description="d", content="c",
        created_at=ts, updated_at=ts, namespace="diana",
    )
    s.memories.upsert_memory_row(
        id="2", title="m2", description="d", content="c",
        created_at=ts, updated_at=ts, namespace="shared",
    )
    s.memories.upsert_memory_row(
        id="3", title="m3", description="d", content="c",
        created_at=ts, updated_at=ts, namespace="bella",
    )

    # diana reads own + shared
    rows = s.memories.all_memory_rows(namespaces=["diana", "shared"])
    ids = {r["id"] for r in rows}
    assert ids == {"1", "2"}

    # no filter → all
    rows = s.memories.all_memory_rows()
    assert len(rows) == 3

    s.db.close()


def test_get_memory_rows_batching_exceeds_500_ids(tmp_path):
    """get_memory_rows batches queries into 500-ID chunks — should handle 600+ IDs."""
    s = build_stores(tmp_path / "batch.db")
    ts = "2026-01-01T00:00:00+00:00"
    ids = []
    for i in range(600):
        lid = f"batch-{i:04d}"
        ids.append(lid)
        s.memories.upsert_memory_row(
            id=lid, title=f"mem-{i}", description="d", content="c",
            created_at=ts, updated_at=ts,
        )

    rows = s.memories.get_memory_rows(ids)
    assert len(rows) == 600

    # With namespace filter
    rows = s.memories.get_memory_rows(ids[:300], namespaces=["shared"])
    assert len(rows) == 300

    s.db.close()


def test_get_memory_rows_dedup(tmp_path):
    """get_memory_rows de-duplicates input IDs (returns no duplicate rows)."""
    s = build_stores(tmp_path / "dedup.db")
    ts = "2026-01-01T00:00:00+00:00"
    s.memories.upsert_memory_row(
        id="a", title="alpha", description="d", content="c",
        created_at=ts, updated_at=ts,
    )
    s.memories.upsert_memory_row(
        id="b", title="beta", description="d", content="c",
        created_at=ts, updated_at=ts,
    )

    rows = s.memories.get_memory_rows(["a", "b", "a", "b"])
    assert len(rows) == 2  # no duplicates

    s.db.close()


def test_read_side_migration_map_normalises_legacy_types(stores):
    """Legacy relation_type strings stored in DB are normalised on read.

    Insert a link row with each legacy type directly via SQL (bypassing the
    application-layer validator), fetch it back by ID, and assert the exact
    new canonical type returned — per-type, no overlap ambiguity.
    """
    import uuid
    from datetime import UTC, datetime

    ts = datetime.now(UTC).isoformat()

    type_pairs: list[tuple[str, str, str]] = [
        ("related_to", "references", "related spot-check"),
        ("used_in",    "part_of",    "used_in spot-check"),
        ("used_for",   "references", "used_for spot-check"),
        ("used_by",    "depends_on", "used_by spot-check"),
        ("used_as",    "references", "used_as spot-check"),
    ]

    for old_type, expected_new, reason in type_pairs:
        lid = str(uuid.uuid4())

        # Bypass insert_link (which would reject old types) — write raw SQL.
        stores.db.conn.execute(
            """INSERT INTO memory_links
              (id, source_memory_id, target_memory_id, relation_type,
               reason, score, created_at, updated_at, usage_count,
               confidence, confidence_count)
            VALUES (?, 'a', 'b', ?, ?, 1.0, ?, ?, 0, NULL, 0)
            """,
            (lid, old_type, reason, ts, ts),
        )
        stores.db.conn.commit()

        # Fetch by exact ID and assert the mapped type.
        fetched = stores.links.get_link(lid)
        assert fetched is not None, f"link {lid} (old={old_type}) not found"
        assert fetched.relation_type == expected_new, (
            f"old='{old_type}' expected='{expected_new}' "
            f"got='{fetched.relation_type}'"
        )


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
