from rank_bm25 import BM25Okapi

from lorekeeper.domains.memory.models import Memory


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class KeywordIndex:
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._bm25: BM25Okapi | None = None

    def rebuild(self, memories: list[Memory]) -> None:
        if not memories:
            self._ids = []
            self._bm25 = None
            return
        # Replicate Lunr field boosts: title×3, description×2, content×1
        corpus = [
            _tokenize(m.title) * 3 + _tokenize(m.description) * 2 + _tokenize(m.content)
            for m in memories
        ]
        self._ids = [m.id for m in memories]
        self._bm25 = BM25Okapi(corpus)

    def search_normalized(self, query: str) -> dict[str, float]:
        if self._bm25 is None or not query.strip():
            return {}
        tokens = _tokenize(query)
        scores = self._bm25.get_scores(tokens)
        max_score = max(scores) if len(scores) else 0.0
        if max_score <= 0:
            return {}
        # Top hit normalized to 1.0 (replicates Lunr quirk from v1)
        return {
            self._ids[i]: float(scores[i]) / max_score
            for i in range(len(self._ids))
            if scores[i] > 0
        }
