---
id: LKPR-17
title: Memory Conflict Resolution (lore_reconcile)
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-17] Memory Conflict Resolution (lore_reconcile)

## Problem

Agents accumulate contradictory memories over time — e.g. "user prefers dark mode" stored alongside "user switched to light mode." Neither gets resolved, so retrieval becomes noisy or misleading. Contradictions silently degrade agent reasoning.

## Solution

`lore_reconcile` — a background job or on-demand MCP tool that detects semantically conflicting memories on the same topic, scores them by recency + confidence, and either auto-merges or flags for consolidation. Similar to Git conflict resolution but driven by temporal weight and source trust.

## Acceptance Criteria

- [ ] Tool detects memories with semantically conflicting claims on the same entity/topic
- [ ] Scoring uses recency + confidence to rank which memory to keep or prefer
- [ ] Auto-merges clear cases (one memory clearly supersedes another)
- [ ] Flags ambiguous conflicts for human or agent review
- [ ] Resolved conflicts are auditable (soft-delete or archive losing memory with reason)

## Affected Files

- `src/lorekeeper/services/reconcile.py` — new service
- `src/lorekeeper/handlers.py` — expose as MCP tool
- `src/lorekeeper/server.py` — register tool

## Dependencies

_None_

## Open Questions

- What threshold defines "semantic conflict" vs. "related but not contradictory"?
- Should auto-merge be opt-in (safe default) or opt-out?

## Notes

Pairs well with LKPR-13 (sleep cycle consolidation) but solves a different problem — conflict vs. compression. Filed from daily ideas cron output (2026-05-22).

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
