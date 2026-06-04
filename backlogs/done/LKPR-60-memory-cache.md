---
id: LKPR-60
title: In-process cache for _all_memories() to eliminate redundant DB reads
type: enhancement
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-04
github_issue: 130
resolved_date: 2026-06-04
---

# [LKPR-60] In-process cache for _all_memories() to eliminate redundant DB reads

## Problem

`_all_memories()` was called multiple times per request cycle, performing redundant SQLite reads on every call. Under load or in tight agentic loops this caused measurable latency and unnecessary I/O.

## Solution

Added an in-process TTL cache for `_all_memories()` so repeated calls within the same request window return cached results without hitting SQLite. Cache is invalidated on any write (insert, update, delete).

## Acceptance Criteria

- [x] `_all_memories()` results cached in-process with TTL
- [x] Cache invalidated on write operations
- [x] No change to external API behaviour
- [x] Tests passing

## Affected Files

**Backend:** `services/memory_engine.py` or equivalent cache layer

**Dashboard:** _none_

## Required Updates

- **CLAUDE.md**: N/A
- **README.md**: N/A

## Notes

Shipped as part of PR #131 alongside LKPR-54 (lore_forget).
