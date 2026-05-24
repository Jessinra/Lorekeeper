---
id: LKPR-31
title: Switch vector store from Chroma to LanceDB for concurrent multi-process access
type: enhancement
status: done
resolution: merged_via_pr7
merged_at: 2026-05-24
merged_by: Jason
pr_url: https://github.com/Jessinra/Lorekeeper/pull/7
resolved_date: 2026-05-24
closed_reason: verified_live_via_mcp
closed_by: Akane
priority: high
sprint: ~
rice_score: 72
filed_by: Jason
filed_date: 2026-05-24
---

# [LKPR-31] Switch vector store from Chroma to LanceDB for concurrent multi-process access

## Problem

Chroma's embedded `PersistentClient` uses file-level locks on `LORE_DATA_DIR`. Only one Lorekeeper process can hold the DB open at a time — running Lorekeeper on multiple Hermes profiles simultaneously (e.g. Akane + Bella) causes one to crash or silently fail.

Current workaround: only enable Lorekeeper on one profile. This is a hard blocker for distribution — anyone installing Lorekeeper with two agents or two terminals hits the problem immediately.

## Solution

Replace Chroma with LanceDB as the vector store backend in `memory_engine.py`. LanceDB (Apache Arrow/Lance format) supports concurrent multi-process access natively — no server, no lock files. Mem0 supports it via `vector_store.provider = "lancedb"`. User install stays `uvx lorekeeper` → works. No extra processes, no ports, no config.

## Acceptance Criteria

- [ ] `memory_engine.py` switches `vector_store.provider` from `"chroma"` to `"lancedb"`
- [ ] `lancedb` and `pyarrow` added to `pyproject.toml` dependencies
- [ ] `config.py` updated: replace `LORE_CHROMA_*` env vars with `LORE_LANCEDB_PATH` (default: `~/.lorekeeper/lancedb`)
- [ ] Semantic scale probe at startup verified for LanceDB score direction (similarity vs distance)
- [ ] All existing tests pass: `uv run pytest`
- [ ] Concurrent smoke test: two `lorekeeper` stdio processes open simultaneously, both insert and search without error
- [ ] Existing Chroma data NOT migrated (embeddings regenerate from SQLite text) — documented clearly in README
- [ ] `CLAUDE.md` "Single-instance only" constraint removed
- [ ] `scripts/migrate_from_json.py` updated if it references Chroma directly
- [ ] README and `PLAN.md` updated to reflect LanceDB

## Affected Files

**Backend:**
- `src/lorekeeper/services/memory_engine.py` — swap Chroma config for LanceDB
- `src/lorekeeper/config.py` — replace `LORE_CHROMA_*` env vars
- `pyproject.toml` — add `lancedb`, `pyarrow`
- `scripts/migrate_from_json.py` — update if Chroma-specific
- `tests/` — update any Chroma-specific fixtures

**Dashboard (if applicable):**
- _none_

## Dependencies

_None_

## Required Updates

- **CLAUDE.md**: [ ] Remove "Single-instance only" constraint; update data dir description to mention LanceDB
- **README.md**: [ ] Remove Chroma references; add LanceDB; note that existing Chroma semantic index is not migrated (memories survive via SQLite)
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- Does Mem0's LanceDB integration support metadata filtering the same way Chroma does? (Used in namespace isolation — LKPR-10). Confirm before implementing.
- Does LanceDB score direction differ from Chroma? Must re-verify the startup probe logic.

## Notes

Workarounds considered and rejected:
- **SSE singleton**: Lorekeeper runs once as HTTP server. Requires persistent process, launchd plist, URL config on every client. Breaks stdio.
- **Chroma HTTP server**: Pushes singleton to `chroma run`. Same operational burden.

Both are wrong — concurrency must be solved at the data layer, not the process layer. LanceDB is the architectural fix. North star: `uvx lorekeeper` with zero operational dependencies.

RICE estimate: Reach=3 (every multi-agent user), Impact=8 (unblocks distribution), Confidence=9, Effort=2. Kept at 72 until Mem0/LanceDB compatibility is confirmed via spike.
