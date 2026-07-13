"""Tests for list_sessions_filtered and count_sessions_by_task."""
import datetime

import pytest

from tests._helpers import build_stores

N = None  # shorthand for None in row tuples


@pytest.fixture
def stores(tmp_path):
    s = build_stores(tmp_path / "test.db")
    now = datetime.datetime.now(datetime.UTC).isoformat()
    # (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
    #  transcript, what_was_done, decisions, lessons_learnt, good_patterns,
    #  user_profile, discoveries)
    rows = [
        ("s1", "2024-01-01", "Alpha topic", "coding", now, N, N, "did alpha", N, N, N, N, N),
        ("s2", "2024-01-02", "Beta topic", "coding", now, N, N, "did beta", N, N, N, N, N),
        ("s3", "2024-01-03", "Gamma topic", "research", now, N, N, "did gamma", N, N, N, N, N),
        ("s4", "2024-01-04", "Delta notes", "research", now, N, N, "did delta", N, N, N, N, N),
        ("s5", "2024-01-05", "Epsilon misc", None, now, N, N, "did epsilon", N, N, N, N, N),
    ]
    s.reflections.upsert_sessions_bulk(rows)
    return s


def test_list_all_no_filters(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task=None, page=1, page_size=10
    )
    assert total == 5
    assert len(rows) == 5


def test_list_filter_by_task(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task="coding", page=1, page_size=10
    )
    assert total == 2
    assert all(r["task_type"] == "coding" for r in rows)


def test_list_filter_by_query(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q="alpha", task=None, page=1, page_size=10
    )
    assert total == 1
    assert rows[0]["session_id"] == "s1"


def test_list_filter_query_case_insensitive(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q="BETA", task=None, page=1, page_size=10
    )
    assert total == 1
    assert rows[0]["session_id"] == "s2"


def test_list_filter_query_matches_topic(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q="gamma", task=None, page=1, page_size=10
    )
    assert total == 1
    assert rows[0]["session_id"] == "s3"


def test_list_filter_combined(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q="delta", task="research", page=1, page_size=10
    )
    assert total == 1
    assert rows[0]["session_id"] == "s4"


def test_list_filter_no_match(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q="nonexistent", task=None, page=1, page_size=10
    )
    assert total == 0
    assert rows == []


def test_pagination_page1(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task=None, page=1, page_size=2
    )
    assert total == 5
    assert len(rows) == 2


def test_pagination_page2(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task=None, page=2, page_size=2
    )
    assert total == 5
    assert len(rows) == 2


def test_pagination_last_page(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task=None, page=3, page_size=2
    )
    assert total == 5
    assert len(rows) == 1


def test_pagination_beyond_end(stores):
    rows, total = stores.reflections.list_sessions_filtered(
        q=None, task=None, page=99, page_size=10
    )
    assert total == 5
    assert rows == []


def test_count_by_task_excludes_null(stores):
    counts = stores.reflections.count_sessions_by_task()
    assert None not in counts
    assert "" not in counts


def test_count_by_task_values(stores):
    counts = stores.reflections.count_sessions_by_task()
    assert counts.get("coding") == 2
    assert counts.get("research") == 2


def test_count_by_task_empty_store(tmp_path):
    s = build_stores(tmp_path / "empty.db")
    counts = s.reflections.count_sessions_by_task()
    assert counts == {}
