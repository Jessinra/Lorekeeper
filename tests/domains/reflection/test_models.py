"""Reflection domain model tests — SessionRecord and Reflection Pydantic schemas."""
from __future__ import annotations

from lorekeeper.domains.reflection.models import Reflection, SessionRecord


def test_session_record_minimal_fields():
    rec = SessionRecord(session_id="s1", reviewed_at="2026-01-01T00:00:00+00:00")
    assert rec.session_id == "s1"
    assert rec.session_date is None
    assert rec.topic is None
    assert rec.task_type is None
    assert rec.reflection_id is None


def test_session_record_all_fields():
    rec = SessionRecord(
        session_id="s2",
        session_date="2026-01-02",
        topic="refactor",
        task_type="build",
        reviewed_at="2026-01-02T10:00:00+00:00",
        reflection_id="r2",
    )
    assert rec.topic == "refactor"
    assert rec.task_type == "build"
    assert rec.reflection_id == "r2"


def test_reflection_minimal_fields():
    ref = Reflection(
        id="r1",
        created_at="2026-01-01T00:00:00+00:00",
        session_count=3,
        lessons_learnt="learned things",
        summary="a session",
    )
    assert ref.id == "r1"
    assert ref.session_count == 3
    assert ref.lessons_learnt == "learned things"
    assert ref.good_patterns is None
    assert ref.user_profile_updates is None
    assert ref.factual_discoveries is None
    assert ref.memory_ids is None


def test_reflection_all_optional_fields():
    ref = Reflection(
        id="r2",
        created_at="2026-01-01T00:00:00+00:00",
        session_count=1,
        lessons_learnt="l",
        good_patterns="p",
        user_profile_updates="u",
        factual_discoveries="f",
        summary="s",
        memory_ids='["a","b"]',
    )
    assert ref.good_patterns == "p"
    assert ref.user_profile_updates == "u"
    assert ref.factual_discoveries == "f"
    assert ref.memory_ids == '["a","b"]'
