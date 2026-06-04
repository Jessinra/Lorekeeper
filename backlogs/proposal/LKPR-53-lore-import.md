---
id: LKPR-53
title: lore_import — bulk file-to-memory seeding
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 105
filed_date: 2026-05-31
---

# [LKPR-53] lore_import — bulk file-to-memory seeding

## Problem

Every new agent onboards to an empty KB. First `lore_search` returns zero results — kills the habit loop before it forms. Project docs (READMEs, ARCHITECTURE.md, ADRs, on-call runbooks, CLAUDE.md) already contain structured knowledge, but there's no pipeline to ingest them.

Agents on existing projects also miss out: all that project knowledge sits in files while the KB stays empty.

## Solution

New MCP tool `lore_import` for bulk ingestion:

- `lore_import(path="/path/to/file.md" or dir, glob="*.md", dry_run=True)`
- Chunks by Markdown headers → memory titles
- Code comments → technical notes
- Auto-generates descriptions
- Dedup guard prevents re-importing duplicates
- Dry-run shows what it'd create before committing

Minimal — one call turns an empty KB into a project-aware one. No complex config, no pipeline setup.

## Acceptance Criteria

- [ ] `lore_import(file="path/to/file.md")` ingests a single file, chunking by headers
- [ ] `lore_import(dir="path/to/dir", glob="*.md")` recursively ingests matching files
- [ ] `dry_run=True` shows what would be imported without committing
- [ ] Dedup guard: re-importing the same file (or same content chunks) skips duplicates
- [ ] Auto-generates title + description for each memory from header text
- [ ] Existing `lore_search` and all other tools work unchanged

## Affected Files

**Backend:**

- `src/lorekeeper/handlers.py` — new `handle_lore_import` handler
- `src/lorekeeper/services/orchestrator.py` — optional: add orchestration for multi-file import
- `src/lorekeeper/config.py` — optional: `LORE_IMPORT_MAX_FILES`, `LORE_IMPORT_MAX_CHUNK_SIZE`

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_ — standalone tool, no existing functionality depends on it.

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] Add `lore_import` to tool reference
- **Skills**: [ ] `lorekeeper-memorize` — may need minor update to mention import as alternative
- **Backlog**: [ ] N/A

## Open Questions

- Should we support non-Markdown file types initially? (No — start with .md only)
- How to handle very large repos? (Limit by file count and chunk size, configurable)
- Should imported memories be tagged with a source origin? (Yes — add `source` metadata)

## Notes

Filed from daily product ideas cron. Addresses the cold-start onboarding problem. P2 — high onboarding value, but active sprint has critical friction items (LKPR-29/30).
