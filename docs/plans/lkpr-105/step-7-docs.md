# Step 7 — Docs: bake the architecture into CLAUDE.md + ARCHITECTURE.md

**Branch:** `chore/lkpr-105-step7-docs`
**Depends on:** Step 5 (can run parallel to Step 6)
**Files:** 2 modified, docs only
**Source material:** `docs/plans/lkpr-105/step-7-architecture-reference.md` — full architecture text to copy into both files.

## Changes

### 1. `CLAUDE.md`

Replace the "Domain service decomposition (LKPR-104/105)" section with content from `step-7-architecture-reference.md`:

- Six-layer diagram (presentation → shared → processors → domains → platform → infra)
- Import rules list
- Domain DAG (`suggestion→memory→link`, `reflection→memory`)
- Responsibility table (transport/serialization = presentation; validation/metrics/batch/commit = processors; single-aggregate rules = domain services; I/O = repos/infra)
- Note: layering is enforced by `tests/test_architecture.py` — if you need a new edge, add it to the test's allowed table with a comment, in the same PR.
- Remove MemoryService/orchestrator references
- Update the Build Order list (step 8 currently references `services/orchestrator.py`)

### 2. `docs/ARCHITECTURE.md`

Replace the entire file with content from `step-7-architecture-reference.md`:

- Remove `services/orchestrator.py` from diagrams
- Add: 6-layer diagram, `processors/` section (one per slice, constructor DI, never import each other, own commit boundaries), `domains/memory/cache.py`, composition-root description of `server.init_service()` + getters
- Document the two deliberate exceptions: `increment_metric_safe` inline commit (metric contract) and shared single `MemoryCache` instance
- Add "What Was Removed" and "What Was Added" sections for LKPR-105 Phase 7
- Add "Architecture Enforcement" section pointing at `tests/test_architecture.py`

## Verification

```
uv run mkdocs build --strict
while IFS= read -r -d '' f; do [ -f "$f" ] && printf '%s\0' "$f"; done < <(git ls-files -z '*.md') | xargs -0 npx --yes prettier@3.5.3 --check --prose-wrap preserve
grep -rn "orchestrator\|MemoryService" CLAUDE.md docs/ARCHITECTURE.md   # → empty (except historical/changelog mentions)
```

## AC

- [ ] No stale MemoryService/orchestrator references
- [ ] Layer diagram + rules + responsibility table present in both files
- [ ] mkdocs strict build green
