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
