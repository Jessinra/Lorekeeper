"""Unit tests for the shared serializers module.

Covers serialize_memory, serialize_memory_link, and serialize_search_result
with truncation, exclusion, rounding, and edge cases.
"""
from lorekeeper.domains.link.models import MemoryLink
from lorekeeper.domains.memory.models import Memory
from lorekeeper.domains.memory.ranking import SearchResult
from lorekeeper.shared.serializers import (
    serialize_memory,
    serialize_memory_link,
    serialize_search_result,
    serialize_search_result_title,
)


def _make_memory(**overrides) -> Memory:
    defaults = {
        "id": "mem-1",
        "title": "test memory",
        "description": "a description",
        "content": "lorem ipsum dolor sit amet",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
    }
    defaults.update(overrides)
    return Memory(**defaults)


def _make_link(**overrides) -> MemoryLink:
    defaults = {
        "id": "link-1",
        "source_memory_id": "mem-1",
        "target_memory_id": "mem-2",
        "relation_type": "references",
        "reason": "they share context",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
    }
    defaults.update(overrides)
    return MemoryLink(**defaults)


def _make_search_result(**overrides) -> SearchResult:
    defaults = {
        "memory": _make_memory(),
        "combined_score": 0.8567,
        "semantic_score": 0.1234,
        "keyword_score": 0.5678,
        "links": [],
        "decay_factor": 0.95,
    }
    defaults.update(overrides)
    return SearchResult(**defaults)


# --- serialize_memory ---


def test_serialize_memory_all_fields():
    mem = _make_memory()
    result = serialize_memory(mem)
    assert result["id"] == "mem-1"
    assert result["title"] == "test memory"
    assert result["content"] == "lorem ipsum dolor sit amet"
    assert result["created_at"] == "2026-01-01T00:00:00+00:00"
    assert result["score"] == 1.0


def test_serialize_memory_truncate_content():
    mem = _make_memory(content="a" * 100)
    result = serialize_memory(mem, truncate_content=10)
    assert result["content"] == "a" * 10
    assert len(result["content"]) == 10


def test_serialize_memory_truncate_content_none():
    """truncate_content=None emits full content."""
    mem = _make_memory(content="a" * 100)
    result = serialize_memory(mem, truncate_content=None)
    assert result["content"] == "a" * 100


def test_serialize_memory_truncate_content_zero():
    """truncate_content=0 emits empty string (edge case)."""
    mem = _make_memory(content="hello")
    result = serialize_memory(mem, truncate_content=0)
    assert result["content"] == ""


def test_serialize_memory_exclude_fields():
    mem = _make_memory()
    result = serialize_memory(mem, exclude_fields={"created_at", "updated_at"})
    assert "created_at" not in result
    assert "updated_at" not in result
    assert result["id"] == "mem-1"  # other fields still present


def test_serialize_memory_exclude_none():
    """exclude_fields=None omits nothing."""
    mem = _make_memory()
    result = serialize_memory(mem, exclude_fields=None)
    assert "created_at" in result
    assert "updated_at" in result


def test_serialize_memory_exclude_empty_set():
    """Empty exclude set removes nothing."""
    mem = _make_memory()
    result = serialize_memory(mem, exclude_fields=set())
    assert "created_at" in result


def test_serialize_memory_exclude_nonexistent_field():
    """Pop on a missing field is a no-op."""
    mem = _make_memory()
    result = serialize_memory(mem, exclude_fields={"nonexistent"})
    assert "id" in result  # no crash


# --- serialize_memory_link ---


def test_serialize_memory_link_all_fields():
    link = _make_link()
    result = serialize_memory_link(link)
    assert result["id"] == "link-1"
    assert result["relation_type"] == "references"
    assert result["reason"] == "they share context"
    assert result["score"] == 1.0


def test_serialize_memory_link_shape_stable():
    """serialize_memory_link always returns the same keys."""
    link = _make_link()
    result = serialize_memory_link(link)
    expected_keys = {
        "id", "source_memory_id", "target_memory_id", "relation_type",
        "reason", "score", "created_at", "updated_at", "usage_count",
        "confidence", "confidence_count",
    }
    assert set(result) == expected_keys


# --- serialize_search_result ---


def test_serialize_search_result_basic():
    sr = _make_search_result()
    result = serialize_search_result(sr)
    assert result["memory"]["id"] == "mem-1"
    assert result["relevance"]["combined_score"] == 0.8567
    assert result["relevance"]["decay_factor"] == 0.95
    assert "links" in result


def test_serialize_search_result_round_relevance():
    sr = _make_search_result(combined_score=0.8567, semantic_score=0.1234)
    result = serialize_search_result(sr, round_relevance=2)
    assert result["relevance"]["combined_score"] == 0.86
    assert result["relevance"]["semantic_score"] == 0.12


def test_serialize_search_result_round_none():
    """round_relevance=None leaves floats unrounded."""
    sr = _make_search_result(combined_score=0.8567)
    result = serialize_search_result(sr, round_relevance=None)
    assert result["relevance"]["combined_score"] == 0.8567


def test_serialize_search_result_exclude_memory_fields():
    sr = _make_search_result()
    result = serialize_search_result(sr, exclude_memory_fields={"created_at"})
    assert "created_at" not in result["memory"]
    assert result["memory"]["id"] == "mem-1"


def test_serialize_search_result_exclude_relevance_fields():
    sr = _make_search_result()
    result = serialize_search_result(sr, exclude_relevance_fields={"decay_factor"})
    assert "decay_factor" not in result["relevance"]
    assert "combined_score" in result["relevance"]


def test_serialize_search_result_exclude_then_round_order():
    """Exclude happens before round: excluded fields are never rounded."""
    sr = _make_search_result(combined_score=0.8567, decay_factor=0.9512)
    result = serialize_search_result(
        sr,
        exclude_relevance_fields={"decay_factor"},
        round_relevance=2,
    )
    assert "decay_factor" not in result["relevance"]
    assert result["relevance"]["combined_score"] == 0.86  # rounded


def test_serialize_search_result_include_links_true():
    sr = _make_search_result(links=[_make_link()])
    result = serialize_search_result(sr, include_links=True)
    assert len(result["links"]) == 1


def test_serialize_search_result_include_links_false():
    sr = _make_search_result(links=[_make_link()])
    result = serialize_search_result(sr, include_links=False)
    assert "links" not in result


def test_serialize_search_result_no_links():
    """Empty links list emits empty array when include_links=True."""
    sr = _make_search_result(links=[])
    result = serialize_search_result(sr, include_links=True)
    assert result["links"] == []


def test_serialize_search_result_truncate_content_with_exclude_memory():
    """Truncation + exclusion work together."""
    sr = _make_search_result(memory=_make_memory(content="a" * 200))
    result = serialize_search_result(
        sr,
        truncate_content=5,
        exclude_memory_fields={"usage_count"},
    )
    assert result["memory"]["content"] == "a" * 5
    assert "usage_count" not in result["memory"]


# --- serialize_search_result_title ---


def test_serialize_search_result_title_returns_compact_shape():
    """Title mode returns flat {id, title, score} — no memory/relevance nesting."""
    sr = _make_search_result(memory=_make_memory(id="abc", title="my memory"))
    result = serialize_search_result_title(sr)
    assert result == {"id": "abc", "title": "my memory", "score": 0.8567}


def test_serialize_search_result_title_no_content_field():
    """Title mode must not leak content or full memory dict."""
    sr = _make_search_result(memory=_make_memory(content="secret content"))
    result = serialize_search_result_title(sr)
    assert "content" not in result
    assert "memory" not in result
    assert "relevance" not in result


def test_serialize_search_result_title_zero_score():
    """Title mode handles zero-score search result (e.g. from ids lookup)."""
    sr = _make_search_result(combined_score=0.0)
    result = serialize_search_result_title(sr)
    assert result["score"] == 0.0


def test_serialize_search_result_title_rounds_score():
    """Title mode score is rounded to 4 decimal places."""
    sr = _make_search_result(combined_score=0.1234567)
    result = serialize_search_result_title(sr)
    assert result["score"] == 0.1235
