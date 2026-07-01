import pytest

from lorekeeper.domains.memory.models import Memory
from lorekeeper.infra.keyword_index import KeywordIndex


def _mem(id: str, title: str, description: str = "", content: str = "") -> Memory:
    return Memory(
        id=id, title=title, description=description, content=content,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


@pytest.fixture
def idx():
    return KeywordIndex()


def test_top_hit_is_1(idx):
    # Need 3+ docs: BM25 IDF = log(N-df+0.5) - log(df+0.5); with N=2 df=1 → IDF=0
    idx.rebuild([
        _mem("a", "payment flow checkout"),
        _mem("b", "unrelated topic"),
        _mem("c", "something else entirely"),
    ])
    scores = idx.search_normalized("payment checkout")
    assert scores.get("a") == pytest.approx(1.0)


def test_empty_query_returns_empty(idx):
    idx.rebuild([_mem("a", "something")])
    assert idx.search_normalized("") == {}
    assert idx.search_normalized("   ") == {}


def test_empty_corpus_returns_empty(idx):
    idx.rebuild([])
    assert idx.search_normalized("anything") == {}


def test_title_boost_outranks_content(idx):
    # "checkout" in title should outrank "checkout" buried in content only
    idx.rebuild([
        _mem("title_match", title="checkout flow", description="", content="other words here"),
        _mem("content_only", title="unrelated", description="", content="checkout payment thing"),
        _mem("noise", title="completely different", description="", content="nothing relevant"),
    ])
    scores = idx.search_normalized("checkout")
    assert scores.get("title_match", 0) > scores.get("content_only", 0)


def test_unrelated_query_returns_empty(idx):
    idx.rebuild([_mem("a", "payment checkout")])
    scores = idx.search_normalized("zzzzunknownword")
    assert scores == {}
