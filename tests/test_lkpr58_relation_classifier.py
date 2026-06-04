"""Stage 2: LLM relation classifier tests (LKPR-58)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from lorekeeper.config import Settings
from lorekeeper.services.link_candidate import LinkCandidate
from lorekeeper.services.relation_classifier import (
    LLMRelationClassifier,
    VALID_RELATION_TYPES,
)


# ── Test helpers ───────────────────────────────────────────────────────────────


def _candidate(target_id: str = "tgt-1", score: float = 0.8) -> LinkCandidate:
    return LinkCandidate(
        source_lore_id="src-1",
        target_lore_id=target_id,
        cosine_score=0.9,
        bm25_score=0.7,
        entity_score=0.5,
        temporal_score=0.3,
        weighted_score=score,
    )


def _settings(base_url: str = "https://api.openai.com/v1") -> Settings:
    return Settings(
        link_classifier_base_url=base_url,
        link_classifier_model="gpt-4o-mini",
        link_classifier_timeout=30.0,
        link_classifier_api_key="sk-test-key",
    )


def _mock_response(relation: str, confidence: float = 0.9, reasoning: str = "test reasoning") -> MagicMock:
    """Build a mock httpx.Response that returns a valid LLM classification."""
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "choices": [{
            "message": {
                "content": json.dumps({"relation": relation, "confidence": confidence, "reasoning": reasoning}),
            }
        }]
    }
    return mock


def _empty_response() -> MagicMock:
    """Simulate a failed HTTP call."""
    mock = MagicMock()
    mock.raise_for_status.side_effect = RuntimeError("connection failed")
    return mock


# ── is_available() ─────────────────────────────────────────────────────────────


def test_classifier_not_available_when_base_url_empty():
    clf = LLMRelationClassifier(_settings(base_url=""))
    assert not clf._is_available()


def test_classifier_available_when_base_url_set():
    clf = LLMRelationClassifier(_settings())
    assert clf._is_available()


# ── classify_batch — available path ────────────────────────────────────────────


@patch("httpx.post")
def test_classifier_calls_llm_for_each_candidate(mock_post):
    mock_post.return_value = _mock_response("related_to")
    clf = LLMRelationClassifier(_settings())
    c1 = _candidate("a")
    c2 = _candidate("b")
    clf.classify_batch("source text", [c1, c2], {"a": "target text a", "b": "target text b"})
    assert mock_post.call_count == 2


@patch("httpx.post")
def test_classifier_skips_empty_target_text(mock_post):
    """Candidates with no target text are silently skipped (no LLM call)."""
    mock_post.return_value = _mock_response("related_to")
    clf = LLMRelationClassifier(_settings())
    c = _candidate("a")
    clf.classify_batch("source text", [c], {"a": ""})
    assert mock_post.call_count == 0


@patch("httpx.post")
def test_classifier_sets_proposed_relation(mock_post):
    mock_post.return_value = _mock_response("supersedes", 0.85, "newer version")
    clf = LLMRelationClassifier(_settings())
    c1 = _candidate("a")
    clf.classify_batch("old source", [c1], {"a": "new target"})
    assert c1.proposed_relation == "supersedes"
    assert c1.classifier_confidence == pytest.approx(0.85)
    assert c1.classifier_reasoning == "newer version"


@patch("httpx.post")
def test_classifier_none_discards_candidate(mock_post):
    """Relation 'none' sets weighted_score to -1.0 for discard."""
    mock_post.return_value = _mock_response("none")
    clf = LLMRelationClassifier(_settings())
    c = _candidate(score=0.8)
    clf.classify_batch("source", [c], {"tgt-1": "target"})
    assert c.weighted_score == -1.0
    assert c.proposed_relation == "none"


@patch("httpx.post")
def test_classifier_all_valid_relation_types(mock_post):
    """Each valid relation type should be accepted."""
    for rtype in sorted(VALID_RELATION_TYPES):
        mock_post.return_value = _mock_response(rtype)
        clf = LLMRelationClassifier(_settings())
        c = _candidate(f"tgt-{rtype}")
        clf.classify_batch("src", [c], {c.target_lore_id: "target"})
        assert c.proposed_relation == rtype, f"failed for {rtype}"


@patch("httpx.post")
def test_classifier_invalid_relation_falls_back_to_related_to(mock_post):
    mock_post.return_value = _mock_response("bogus_relation")
    clf = LLMRelationClassifier(_settings())
    c = _candidate()
    clf.classify_batch("src", [c], {"tgt-1": "target"})
    assert c.proposed_relation == "related_to"


@patch("httpx.post")
def test_classifier_malformed_json_does_not_crash(mock_post):
    """If the LLM returns invalid JSON, the candidate is untouched."""
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "choices": [{"message": {"content": "not valid json at all"}}]
    }
    mock_post.return_value = mock
    clf = LLMRelationClassifier(_settings())
    c = _candidate(score=0.8)
    clf.classify_batch("src", [c], {"tgt-1": "target"})
    # No change — JSON parse failure is silently caught
    assert c.proposed_relation == "related_to"
    assert c.classifier_confidence == 0.0


# ── classify_batch — unavailable path ──────────────────────────────────────────


def test_classifier_batch_noop_when_unavailable():
    clf = LLMRelationClassifier(_settings(base_url=""))
    c = _candidate()
    clf.classify_batch("src", [c], {"tgt-1": "target"})
    # No classifier fields touched
    assert c.proposed_relation == "related_to"
    assert c.classifier_confidence == 0.0


# ── error handling ─────────────────────────────────────────────────────────────


@patch("httpx.post")
def test_classifier_http_failure_does_not_cascade(mock_post):
    """One failing call doesn't affect subsequent candidates."""
    mock_post.side_effect = [
        _empty_response(),   # first call fails
        _mock_response("depends_on", 0.95, "builds upon"),  # second succeeds
    ]
    clf = LLMRelationClassifier(_settings())
    c1 = _candidate("failing")
    c2 = _candidate("succeeding")
    clf.classify_batch("src", [c1, c2], {"failing": "text", "succeeding": "text"})
    # Failing candidate unaffected
    assert c1.proposed_relation == "related_to"
    assert c1.classifier_confidence == 0.0
    # Succeeding candidate classified
    assert c2.proposed_relation == "depends_on"
    assert c2.classifier_confidence == pytest.approx(0.95)


@patch("httpx.post")
def test_classifier_uses_correct_url_and_headers(mock_post):
    mock_post.return_value = _mock_response("related_to")
    clf = LLMRelationClassifier(_settings())
    clf.classify_batch("src", [_candidate("a")], {"a": "tgt"})
    call_kwargs = mock_post.call_args
    assert "chat/completions" in call_kwargs[0][0]
    headers = call_kwargs[1].get("headers", {})
    assert headers.get("Authorization") == "Bearer sk-test-key"
    assert "Content-Type" in headers


@patch("httpx.post")
def test_classifier_no_auth_header_when_no_api_key(mock_post):
    mock_post.return_value = _mock_response("related_to")
    settings = _settings()
    settings.link_classifier_api_key = ""
    clf = LLMRelationClassifier(settings)
    clf.classify_batch("src", [_candidate("a")], {"a": "tgt"})
    call_kwargs = mock_post.call_args
    headers = call_kwargs[1].get("headers", {})
    assert "Authorization" not in headers


@patch("httpx.post")
def test_classifier_uses_temperature_zero(mock_post):
    mock_post.return_value = _mock_response("related_to")
    clf = LLMRelationClassifier(_settings())
    clf.classify_batch("src", [_candidate("a")], {"a": "tgt"})
    payload = mock_post.call_args[1]["json"]
    assert payload["temperature"] == 0.0


@patch("httpx.post")
def test_classifier_max_tokens_is_150(mock_post):
    mock_post.return_value = _mock_response("related_to")
    clf = LLMRelationClassifier(_settings())
    clf.classify_batch("src", [_candidate("a")], {"a": "tgt"})
    payload = mock_post.call_args[1]["json"]
    assert payload["max_tokens"] == 150