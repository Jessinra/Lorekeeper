# Step 4b — MemoryProcessor: search/insert/remember/update/forget/import

**Branch:** `chore/lkpr-105-step4b-memory-processor`
**Depends on:** Step 3b
**Files:** 1 new, 5 modified
**Behavior change:** none

## Changes

### 1. NEW `src/lorekeeper/processors/memory.py` — `MemoryProcessor`

```python
class MemoryProcessor:
    def __init__(self, search_service, write_service, import_service,
                 metrics: MetricsStore, db: Database, settings: Settings) -> None: ...

    def search(self, query, limit, min_score, include_links, include_deleted,
               refine_from, format, ids, created_after, updated_after,
               sort_by, source_type) -> list[SearchResult] | ...:
        # Move from handle_search: format/sort_by/source_type enum checks,
        # parse_filter_dt, ids-cap (settings.max_search_ids), empty-query
        # guard, ids-vs-query branch. Returns domain objects + which
        # serializer applies is decided by CALLER via format — processor
        # returns (results, format) or typed result; handler serializes.
    def insert(self, memories, links, force) -> dict: ...
        # WRITE_SOURCE_TYPES validation from server.py tool body
    def remember(self, thought, source_type) -> dict: ...
    def update(self, memory_feedback, link_feedback) -> dict: ...
    def forget(self, memory_ids, reason) -> dict: ...
        # empty-ids / invalid-reason guards from server.py tool body
    def import_dump(self, memories, links, dry_run) -> dict: ...
```

Rule: processor validates + orchestrates + increments metrics; it returns
domain objects/plain dicts, never serialized MCP/HTTP payloads. Metric
increments MOVE here from `MemorySearchService.search` / write-service
methods (delete there — this completes "metrics out of domains" for the
memory slice; keep increment position semantics identical: one increment per
tool call, not per item).

### 2. `api/mcp/handlers/memory_handlers.py` — thin shim

`handle_search(processor, ...)`: pass-through + serialize
(`serialize_search_result[_title]`). `handle_insert(processor, ...)`: same.
Delete `MemoryService` import and `domains.memory.ranking` import (validation
constants move with the logic into the processor) — delete both exception
entries.

### 3. `server.py`

Construct `MemoryProcessor`; `get_memory_processor()`; rewire tool bodies for
lore_search, lore_insert, lore_remember, lore_update, lore_forget,
lore_processed_sessions stays (4c). Encouragement wrappers (`for_insert`
etc.) stay in server.py — presentation concern.

### 4. `dashboard/routes/search.py`, `dashboard/routes/backup.py`, `dashboard/routes/memories.py`

- search.py: `get_memory_processor().search(...)` + existing serialization
- backup.py: import/export via processor (`import_dump`); export path reads
  via stores today — route through processor method `export_dump()` if the
  logic is >1 line, else leave store reads until 4d review
- memories.py: reads go through processor-provided methods; writes
  (`forget`) through `processor.forget`

Keep this step's dashboard scope honest: if memories.py turns out to need new
processor read methods (list/detail), add them as thin delegations — no new
logic.

### 5. Tests

- NEW `tests/processors/test_memory_processor.py`: validation tests move from
  `tests/test_handlers.py` (search format/sort_by/source_type/ids-cap
  errors) — the handler file keeps envelope-level tests.
- `tests/test_handlers.py`: rewire fixtures to construct processor.

## Verification

```
uv run pytest -q --ignore=tests/e2e
uv run pytest tests/test_architecture.py -v
uv run ruff check src tests scripts/ && uv run mypy src
grep -rn "increment_metric" src/lorekeeper/domains/memory/   # → empty
```

MCP contract check against `docs/plans/lkpr-104-mcp-baseline.json` for
lore_search/insert/remember/update/forget.

## AC

- [ ] All memory-slice validation + metrics in processor; handlers serialize only
- [ ] `domains/memory` has zero metric calls
- [ ] MCP outputs byte-identical to baseline
- [ ] memory_handlers exception entries deleted
