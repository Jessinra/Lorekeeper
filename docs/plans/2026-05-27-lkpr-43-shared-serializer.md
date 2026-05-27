# LKPR-43 Shared Serializer Implementation Plan

> **For implementer:** Use TDD where applicable. Keep existing behavior identical — this is a pure refactor, no new capability.

**Goal:** Eliminate duplicate serialization between `handlers.py` (MCP) and `dashboard/app.py` (REST API) by moving it into a shared `src/lorekeeper/serializers.py`.

**Architecture:** Three serializer functions in `serializers.py`. `serialize_search_result()` composes `serialize_memory()` + `serialize_memory_link()`. Each function accepts optional kwargs for endpoint-specific overrides (content truncation, field exclusion). Callers in `handlers.py` and `dashboard/app.py` call the shared functions instead of building dicts inline.

**Tech Stack:** Python 3.12+, no new dependencies.

---

### Task 1: Create `serializers.py` with `serialize_memory()` and `serialize_memory_link()`

**Objective:** Two functions that serialize `Memory` and `MemoryLink` Pydantic models into dicts, with overrides for truncation and field exclusion.

**Files:**
- Create: `src/lorekeeper/serializers.py`

**Implementation:**

```python
"""Shared serializers for MCP and dashboard response models."""

from lorekeeper.models import Memory, MemoryLink
from lorekeeper.services.search import SearchResult


def serialize_memory(
    memory: Memory,
    *,
    truncate_content: int | None = None,
    exclude_fields: set[str] | None = None,
) -> dict:
    """Serialize a Memory model to a dict.

    Args:
        memory: The Memory instance to serialize.
        truncate_content: If set, truncate ``content`` to this many characters.
        exclude_fields: Set of field names to omit from the output.

    Returns:
        Dict with all Memory fields (minus exclusions, with optional truncation).
    """
    exclude = exclude_fields or set()
    data = {
        "id": memory.id,
        "title": memory.title,
        "description": memory.description,
        "content": memory.content[:truncate_content] if truncate_content else memory.content,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
        "usage_count": memory.usage_count,
        "score": memory.score,
        "soft_deleted": memory.soft_deleted,
        "confidence": memory.confidence,
        "confidence_count": memory.confidence_count,
    }
    if exclude:
        data = {k: v for k, v in data.items() if k not in exclude}
    return data


def serialize_memory_link(link: MemoryLink) -> dict:
    """Serialize a MemoryLink model to a dict."""
    return {
        "id": link.id,
        "source_memory_id": link.source_memory_id,
        "target_memory_id": link.target_memory_id,
        "relation_type": link.relation_type,
        "reason": link.reason,
        "score": link.score,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
        "usage_count": link.usage_count,
        "confidence": link.confidence,
        "confidence_count": link.confidence_count,
    }
```

**Verification:**

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
uv run python -c "from lorekeeper.serializers import serialize_memory, serialize_memory_link; print('OK')"
```

Expected: `OK`

**Commit:**
```bash
git add src/lorekeeper/serializers.py
git commit -m "refactor(lkpr-43): add shared serializers for Memory and MemoryLink"
```

---

### Task 2: Add `serialize_search_result()` to `serializers.py`

**Objective:** Compose `serialize_memory()` + `serialize_memory_link()` into a single `serialize_search_result()` with relevance scoring fields, supporting all the overrides the dashboard needs.

**Files:**
- Modify: `src/lorekeeper/serializers.py`

**Add to the end of `serializers.py`:**

```python
def serialize_search_result(
    result: SearchResult,
    *,
    truncate_content: int | None = None,
    exclude_memory_fields: set[str] | None = None,
    exclude_relevance_fields: set[str] | None = None,
    round_relevance: int | None = None,
    include_links: bool = True,
) -> dict:
    """Serialize a SearchResult to a dict.

    Args:
        result: The SearchResult instance.
        truncate_content: If set, truncate memory ``content`` to this many chars.
        exclude_memory_fields: Field names to omit from the memory dict.
        exclude_relevance_fields: Field names to omit from the relevance dict.
        round_relevance: If set, round relevance scores to this many decimal places.
        include_links: If True, include the ``links`` array.

    Returns:
        Dict with ``memory``, ``relevance``, and optionally ``links`` keys.
    """
    relevance = {
        "combined_score": result.combined_score,
        "semantic_score": result.semantic_score,
        "keyword_score": result.keyword_score,
        "decay_factor": result.decay_factor,
    }
    if exclude_relevance_fields:
        relevance = {k: v for k, v in relevance.items() if k not in exclude_relevance_fields}
    if round_relevance is not None:
        relevance = {k: round(v, round_relevance) for k, v in relevance.items()}

    memory = serialize_memory(
        result.memory,
        truncate_content=truncate_content,
        exclude_fields=exclude_memory_fields,
    )

    data: dict = {
        "memory": memory,
        "relevance": relevance,
    }
    if include_links:
        data["links"] = [serialize_memory_link(lnk) for lnk in result.links]

    return data
```

**Verification — both MCP and dashboard shape produce correct output:**

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
uv run python -c "
from lorekeeper.serializers import serialize_search_result
from lorekeeper.models import Memory
from lorekeeper.services.search import SearchResult

m = Memory(
    id='test', title='Test', description='desc', content='some content here',
    created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:00:00Z'
)
r = SearchResult(memory=m, combined_score=0.85, semantic_score=0.9, keyword_score=0.5, links=[])

# Default (MCP shape)
d = serialize_search_result(r)
assert 'decay_factor' in d['relevance']
assert d['memory']['content'] == 'some content here'
assert 'links' in d

# Dashboard shape
d2 = serialize_search_result(r, truncate_content=5,
    exclude_memory_fields={'created_at','updated_at','confidence','confidence_count'},
    exclude_relevance_fields={'decay_factor'}, round_relevance=4, include_links=False)
assert d2['memory']['content'] == 'some c'
assert 'decay_factor' not in d2['relevance']
assert 'links' not in d2
assert 'created_at' not in d2['memory']
print('All assertions passed')
"
```

Expected: `All assertions passed`

**Commit:**
```bash
git add src/lorekeeper/serializers.py
git commit -m "refactor(lkpr-43): add serialize_search_result composable serializer"
```

---

### Task 3: Refactor `handlers.py` to use shared serializers

**Objective:** Replace inline `_result_to_dict()` with a call to `serialize_search_result()`.

**Files:**
- Modify: `src/lorekeeper/handlers.py`

**Changes:**

1. Replace the import at the top: remove `from lorekeeper.services.search import SearchResult`, add `from lorekeeper.serializers import serialize_search_result`

2. Delete the entire `_result_to_dict()` function (lines 9-47)

3. In `handle_search()`, replace `[_result_to_dict(r) for r in results]` with `[serialize_search_result(r) for r in results]`

**After the change, `handlers.py` should look like:**

```python
import structlog

from lorekeeper.serializers import serialize_search_result
from lorekeeper.services.orchestrator import MemoryService

log = structlog.get_logger()


def handle_search(
    svc: MemoryService,
    query: str,
    limit: int | None = None,
    min_score: float = 0.1,
    include_links: bool = True,
    include_deleted: bool = False,
    refine_from: list[str] | None = None,
) -> dict:
    results = svc.search(
        query, limit, min_score, include_links, include_deleted,
        refine_from=refine_from,
    )
    return {
        "results": [serialize_search_result(r) for r in results],
        "total_matched": len(results),
        "query": query,
    }


def handle_insert(
    svc: MemoryService,
    memories: list[dict],
    links: list[dict],
    force: bool = False,
) -> dict:
    for i, m in enumerate(memories):
        if "title" not in m:
            raise ValueError(
                f"memory at index {i} is missing required field: 'title'"
            )
    return svc.insert(memories, links, force)


def handle_remember(svc: MemoryService, thought: str) -> dict:
    return svc.remember(thought)
```

**Verification:**

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
uv run pytest tests/test_handlers.py -v
```

Expected: 3 passed

**Commit:**
```bash
git add src/lorekeeper/handlers.py
git commit -m "refactor(lkpr-43): replace inline _result_to_dict with shared serialize_search_result"
```

---

### Task 4: Refactor dashboard `/api/search` to use shared serializers

**Objective:** Replace inline dict construction in `dashboard/app.py:304-322` with a call to `serialize_search_result()` with the dashboard-specific overrides.

**Files:**
- Modify: `src/lorekeeper/dashboard/app.py`

**Changes:**

1. Add import at top of `app.py`:
   ```python
   from lorekeeper.serializers import serialize_search_result
   ```

2. Replace the inline search result loop (lines 304-322) with:
   ```python
   return [
       serialize_search_result(
           r,
           truncate_content=300,
           exclude_memory_fields={"created_at", "updated_at", "confidence", "confidence_count"},
           exclude_relevance_fields={"decay_factor"},
           round_relevance=4,
           include_links=False,
       )
       for r in results
   ]
   ```

This preserves the exact same output shape the dashboard currently produces (content truncated to 300, no decay_factor, no links, rounded scores).

**Verification — dashboard output shape matches:**

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
uv run python -c "
from lorekeeper.models import Memory
from lorekeeper.services.search import SearchResult
from lorekeeper.serializers import serialize_search_result

m = Memory(id='test', title='T', description='D', content='x' * 500,
           created_at='2026-01-01T00:00:00Z', updated_at='2026-01-01T00:00:00Z',
           usage_count=5, score=7.0)
result = SearchResult(memory=m, combined_score=0.85421, semantic_score=0.9, keyword_score=0.5, links=[])

d = serialize_search_result(result, truncate_content=300,
    exclude_memory_fields={'created_at','updated_at','confidence','confidence_count'},
    exclude_relevance_fields={'decay_factor'}, round_relevance=4, include_links=False)

assert len(d['memory']['content']) == 300
assert 'decay_factor' not in d['relevance']
assert 'links' not in d
assert d['relevance']['combined_score'] == 0.8542
assert 'confidence' not in d['memory']
print('Dashboard shape verified')
"
```

**Commit:**
```bash
git add src/lorekeeper/dashboard/app.py
git commit -m "refactor(lkpr-43): dashboard search uses shared serializer with endpoint overrides"
```

---

### Task 5: Run full test suite and verify lint

**Objective:** Confirm the refactor didn't break anything.

**Verification:**

```bash
cd ~/.hermes/profiles/diana/projects/lorekeeper
uv run pytest -v
uv run ruff check src tests
```

Expected: 87/87 tests passing, ruff clean

**Commit:**
```bash
git add -A
git commit -m "refactor(lkpr-43): post-refactor cleanup — lint + test pass"
```

---

### Rollback Plan

If any test fails or output shape changes:
1. `git checkout -- src/lorekeeper/serializers.py src/lorekeeper/handlers.py src/lorekeeper/dashboard/app.py` to revert all files
2. Re-run tests to confirm they pass on original code
3. Debug the serializer override mismatch, fix, and retry from Task 3