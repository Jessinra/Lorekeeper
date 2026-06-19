---
id: LKPR-97
title: Deprecate and remove ChromaDB backend — LanceDB-only vector store
type: chore
status: S:done
priority: P1:high
sprint: ~
rice_score: ~
filed_by: Diana
filed_date: 2026-06-18
github_issue: 225
---

# [LKPR-97] Deprecate and Remove ChromaDB Backend

## Problem

Lorekeeper supported two vector backends (LanceDB + ChromaDB) via `engine_factory.py`, but ChromaDB was never the active backend after LKPR-31 switched the default to LanceDB. The multi-backend code path was dead weight:

- `chromadb_engine.py` (205 lines) and its tests (148 lines) had zero live callers
- `mem0ai` + `chromadb` were heavy deps installed for nothing
- `LORE_VECTOR_STORE` config field implied a choice that didn't exist in practice
- Docs, README, CLAUDE.md still described a two-backend architecture

## Solution

Remove everything ChromaDB/mem0ai-related: code, tests, deps, config fields, and all documentation references. Simplify `engine_factory.py` from 18 → 9 lines (Chroma branch gone).

## Scope

### Code removed

- `src/lorekeeper/services/chromadb_engine.py` (205 lines, deleted)
- `tests/test_chromadb_engine.py` (148 lines, deleted)
- `scripts/seed_lancedb.py` (one-time migration script, 61 lines, deleted)
- `mem0ai` + `chromadb` deps from `pyproject.toml`
- `vector_store` field + `chroma_path` property from `config.py`
- `chromadb`/`mem0` log noise suppressors from `logging_setup.py`
- Chroma branch from `engine_factory.py` (18 → 9 lines)

### Docs cleaned

- `docs/ARCHITECTURE.md`: removed `chromadb_engine.py` from MODULE LAYER diagram
- `docs/api-reference.md`: LanceDB-only truth; deleted `LORE_VECTOR_STORE` env var row
- `docs/linter-decisions.md`: updated mypy `ignore_missing_imports` example
- `README.md`: LanceDB-only references
- `CLAUDE.md`: replaced all 5 stale Chroma/Mem0 references

### Tests / E2E

- `tests/e2e/conftest.py`: removed stale `LORE_VECTOR_STORE` save/restore in `seed_db` and `live_server` fixtures

## Acceptance Criteria

- [x] No `chromadb`/`mem0ai` imports anywhere in codebase
- [x] `chromadb_engine.py` and its tests deleted
- [x] `pyproject.toml` deps cleaned
- [x] All docs updated to LanceDB-only truth
- [x] Full test suite passes — 342 unit + 10 E2E ✅
- [x] `mkdocs build --strict` clean ✅

## Net change: −1,478 lines, +15 lines

## Required Updates

- **CLAUDE.md**: [x] Updated — 5 stale Chroma/Mem0 refs replaced
- **README.md**: [x] Updated — LanceDB-only wording
- **Skills**: [x] `lorekeeper-dev` updated with post-removal state
- **Backlog**: [x] This ticket (LKPR-97)
