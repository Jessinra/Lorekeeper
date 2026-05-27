import pytest

from lorekeeper.services.link_store import LinkStore


@pytest.fixture
def store(tmp_path):
    s = LinkStore(tmp_path / "test.db")
    # seed two memory rows so FK constraints are satisfied
    for i in ("a", "b", "c"):
        s.upsert_memory_row(
            id=i, title=f"mem-{i}", description="d", content="c",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
    yield s
    s.close()


def test_insert_and_retrieve_link(store):
    link = store.insert_link("a", "b", "related_to", "they are related")
    assert link.id
    assert link.source_memory_id == "a"
    assert link.target_memory_id == "b"

    fetched = store.get_link(link.id)
    assert fetched is not None
    assert fetched.id == link.id


def test_links_for_memory_bidirectional(store):
    store.insert_link("a", "b", "related_to", "a→b")
    store.insert_link("c", "a", "used_in", "c→a")

    links = store.links_for_memory("a")
    assert len(links) == 2


def test_fk_rejects_missing_memory(store):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        store.insert_link("a", "nonexistent", "related_to", "bad link")


def test_update_link_score(store):
    link = store.insert_link("a", "b", "related_to", "r")
    store.update_link_fields(link.id, score=5.0)
    updated = store.get_link(link.id)
    assert updated is not None
    assert updated.score == 5.0


def test_cascade_delete(store):
    link = store.insert_link("a", "b", "related_to", "r")
    store.delete_memory_row("a")
    assert store.get_link(link.id) is None


def test_upsert_memory_row_updates(store):
    store.upsert_memory_row(
        id="a", title="updated", description="d2", content="c2",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        score=7.0,
    )
    row = store.get_memory_row("a")
    assert row["title"] == "updated"
    assert row["score"] == 7.0


def test_all_memory_rows_excludes_deleted(store):
    store.update_memory_fields("a", soft_deleted=1)
    rows = store.all_memory_rows(include_deleted=False)
    ids = [r["id"] for r in rows]
    assert "a" not in ids
    assert "b" in ids

    all_rows = store.all_memory_rows(include_deleted=True)
    assert len(all_rows) == 3


def test_upsert_memory_row_stores_namespace(tmp_path):
    s = LinkStore(tmp_path / "ns.db")
    s.upsert_memory_row(
        id="x", title="mem-x", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="diana",
    )
    row = s.get_memory_row("x")
    assert row is not None
    assert row["namespace"] == "diana"
    s.close()


def test_upsert_defaults_namespace_to_shared(tmp_path):
    s = LinkStore(tmp_path / "ns2.db")
    s.upsert_memory_row(
        id="y", title="mem-y", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    row = s.get_memory_row("y")
    assert row is not None
    assert row["namespace"] == "shared"
    s.close()


def test_upsert_does_not_overwrite_namespace(tmp_path):
    """ON CONFLICT update must not clobber the existing namespace."""
    s = LinkStore(tmp_path / "ns3.db")
    s.upsert_memory_row(
        id="z", title="mem-z", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="diana",
    )
    # Re-upsert with default namespace — should NOT overwrite
    s.upsert_memory_row(
        id="z", title="mem-z-updated", description="d2", content="c2",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    row = s.get_memory_row("z")
    assert row is not None
    assert row["namespace"] == "diana"  # preserved
    assert row["title"] == "mem-z-updated"  # other fields updated
    s.close()


def test_all_memory_rows_namespace_filter(tmp_path):
    s = LinkStore(tmp_path / "ns4.db")
    s.upsert_memory_row(
        id="1", title="m1", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="diana",
    )
    s.upsert_memory_row(
        id="2", title="m2", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="shared",
    )
    s.upsert_memory_row(
        id="3", title="m3", description="d", content="c",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        namespace="bella",
    )

    # diana reads own + shared
    rows = s.all_memory_rows(namespaces=["diana", "shared"])
    ids = {r["id"] for r in rows}
    assert ids == {"1", "2"}

    # no filter → all
    rows = s.all_memory_rows()
    assert len(rows) == 3

    s.close()

