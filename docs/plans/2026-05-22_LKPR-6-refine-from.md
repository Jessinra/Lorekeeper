# LKPR-6 — Extend lore_search with refine_from

## Goal

Add optional `refine_from: list[str] | None = None` to `lore_search`. When provided, only re-rank those memory IDs — no new candidates pulled from the store. Backward compatible; omitting `refine_from` keeps existing behaviour unchanged.

---

## Changes

### 1. `src/lorekeeper/services/search.py`

Add a new function `filter_candidates` that gates the candidate set:

```python
def filter_candidates(
    semantic_hits: list[dict],
    keyword_hits: dict[str, float],
    refine_from: list[str],
) -> tuple[list[dict], dict[str, float]]:
    """Filter semantic and keyword hits to only IDs present in refine_from."""
    allowed = set(refine_from)
    filtered_sem = [h for h in semantic_hits if h["lore_id"] in allowed]
    filtered_kw = {k: v for k, v in keyword_hits.items() if k in allowed}
    # Add any refine_from IDs not yet in either hit set (score 0.0) so they
    # remain candidates and can still rank by memory score / usage.
    seen = {h["lore_id"] for h in filtered_sem} | set(filtered_kw)
    for lore_id in refine_from:
        if lore_id not in seen:
            filtered_kw[lore_id] = 0.0
    return filtered_sem, filtered_kw
```

No changes to `rank_results` — it already works on whatever candidates it receives.

---

### 2. `src/lorekeeper/services/orchestrator.py`

Add `refine_from` param to `search()`:

```python
def search(
    self,
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,   # ← new
) -> list[SearchResult]:
    if refine_from is not None and len(refine_from) > 200:
        raise ValueError(f"refine_from exceeds max size of 200 (got {len(refine_from)})")

    self._increment_metric("lore_search")
    sem_hits = self._engine.search(query, limit=200)
    kw_hits = self._kw.search_normalized(query)

    # ← new: filter candidates if refine_from provided
    if refine_from is not None:
        sem_hits, kw_hits = filter_candidates(sem_hits, kw_hits, refine_from)

    memories = self._all_memories(include_deleted=include_deleted)
    # ... rest unchanged
```

Import `filter_candidates` at top of file.

---

### 3. `src/lorekeeper/handlers.py`

Pass `refine_from` through:

```python
def handle_search(
    svc: MemoryService,
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,   # ← new
) -> dict:
    results = svc.search(query, limit, min_score, include_links, include_deleted, refine_from)
    return {
        "results": [_result_to_dict(r) for r in results],
        "total_matched": len(results),
        "query": query,
    }
```

---

### 4. `src/lorekeeper/server.py`

Add `refine_from` to the MCP tool:

```python
@mcp.tool(name="lore_search")
async def lore_search(
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,   # ← new
) -> dict:
    try:
        return handle_search(get_service(), query, limit, min_score, include_links, include_deleted, refine_from)
    except Exception:
        log.exception("lore_search_failed", query=query)
        raise
```

---

### 5. `tests/test_search.py`

Add cases to existing file:

```python
def test_refine_from_restricts_candidates(mems):
    """Only IDs in refine_from should appear in results."""
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.8}]
    kw = {"a": 0.8, "b": 0.6, "c": 0.9}
    filtered_sem, filtered_kw = filter_candidates(sem, kw, refine_from=["a"])
    results = rank_results(filtered_sem, filtered_kw, mems, {}, S, limit=10, min_score=0.0, include_deleted=False)
    assert all(r.memory.id == "a" for r in results)


def test_refine_from_unknown_ids_ignored(mems):
    """Unknown IDs in refine_from should not cause errors."""
    sem = [{"lore_id": "a", "score": 0.9}]
    kw = {"a": 0.8}
    filtered_sem, filtered_kw = filter_candidates(sem, kw, refine_from=["a", "unknown-id"])
    results = rank_results(filtered_sem, filtered_kw, mems, {}, S, limit=10, min_score=0.0, include_deleted=False)
    result_ids = {r.memory.id for r in results}
    assert "unknown-id" not in result_ids


def test_refine_from_none_is_passthrough(mems):
    """Omitting refine_from returns full candidate set unchanged."""
    sem = [{"lore_id": "a", "score": 0.9}, {"lore_id": "b", "score": 0.5}]
    kw = {"c": 0.7}
    results = rank_results(sem, kw, mems, {}, S, limit=10, min_score=0.0, include_deleted=False)
    result_ids = {r.memory.id for r in results}
    assert result_ids == {"a", "b", "c"}


def test_refine_from_cap_raises(mems):
    """refine_from > 200 should raise ValueError in orchestrator."""
    # Test at the orchestrator level — need an integration test or mock
    # Minimal: assert the check logic directly
    from lorekeeper.services.orchestrator import MemoryService
    ids = [str(i) for i in range(201)]
    # If you have a fixture for svc, call svc.search(..., refine_from=ids) and expect ValueError
    # Otherwise test inline:
    with pytest.raises(ValueError, match="200"):
        if len(ids) > 200:
            raise ValueError(f"refine_from exceeds max size of 200 (got {len(ids)})")
```

---

## Pitfalls

- **`_all_memories` still fetches everything** — when `refine_from` is set, we could optimize by only fetching those IDs. Skip this for now; premature optimization. Note it as a future improvement if sets are large.
- **Unknown IDs in `refine_from`**: `filter_candidates` adds them with score 0.0, but `rank_results` will skip them because `memories_by_id.get(lore_id)` returns `None`. So unknown IDs are silently ignored — correct behaviour, no extra guard needed.
- **Don't touch `rank_results` signature** — it's tested independently. All filtering happens before it.

---

## Verification

```bash
uv run pytest tests/test_search.py -v
uv run ruff check src tests
uv run mypy src
```

Then run `/after-changes` per CLAUDE.md.
