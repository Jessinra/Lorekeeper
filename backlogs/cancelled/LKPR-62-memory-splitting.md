---
id: LKPR-62
title: Memory splitting — lore_split_candidates returns long memories, agent splits
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 139
filed_date: 2026-06-05
---

# [LKPR-62] Memory splitting — lore_split_candidates

## Problem

Agents batch-dump into compound memories (200-500+ chars, multiple facts in one entry). Search precision degrades. Splitting requires manual `lore_insert` + `lore_forget`.

## Solution

Dead simple: `lore_split_candidates(n=20, min_length=250)` returns the longest `n` memories where `content > min_length`.

The agent decides if the memory is compound, how to segment it, and applies via `lore_insert` + `lore_forget`.

**Lorekeeper does nothing but a SQL query.** No embeddings, no breakpoints, no detection algorithm. If memory is over the threshold, it's a candidate.

## MCP Tool

```
lore_split_candidates(n=20, min_length=250)
→ {
    candidates: [
      {
        lore_id, title, content, content_length, score,
        created_at, updated_at, usage_count
      }
    ]
  }
```

- Sorted by `content_length DESC`
- Agent iterates, decides which ones are compound, uses LLM to segment
- Agent calls `lore_insert` for each atomic piece + `lore_forget` the original
- Simple SQL — no new infra needed

## Acceptance Criteria

- [ ] `lore_split_candidates(n=20, min_length=250)` returns N longest memories above threshold
- [ ] Sorted by content_length descending
- [ ] `LORE_SPLIT_MIN_LENGTH` env var (default: 250)
- [ ] Response: `lore_id, title, content, content_length, score, created_at, updated_at, usage_count`
- [ ] Invalid `n` (< 1) defaults to 20
- [ ] No new services or import dependencies — just a SQL query on existing `_all_memories` cache
- [ ] `src/lorekeeper/services/memory_splitter.py` — tiny, < 30 lines
- [ ] Traced in `MetricsStore`
- [ ] `assets/skills/lorekeeper-memory-split/SKILL.md` — agent workflow for reviewing and applying splits

## Agent Skill

`assets/skills/lorekeeper-memory-split/SKILL.md` covers:

- Trigger: call once per dreaming cycle
- For each candidate: read content, use LLM to decide if compound
- If yes: segment with titles, call `lore_insert` for each segment + `lore_forget` for original
- Pitfalls: tightly-coupled facts (don't split), very long single sentences

## Design Principle

**Memory too long → agent tries to split it.** Lorekeeper just returns the data. Zero reasoning, zero detection, zero false positives.

## Affected Files

- `src/lorekeeper/services/memory_splitter.py` — new (< 30 lines, SQL query)
- `src/lorekeeper/config.py` — add `LORE_SPLIT_MIN_LENGTH`
- `src/lorekeeper/handlers.py` — register handler
- `src/lorekeeper/server.py` — register tool
- `src/lorekeeper/schemas.py` — add input/output models
- `assets/skills/lorekeeper-memory-split/SKILL.md` — new

## Required Updates

- **CLAUDE.md**: [ ] Add `lore_split_candidates` to MCP API surface
- **README.md**: [ ] Document `lore_split_candidates` tool
- **Skills**: [ ] Add `lorekeeper-memory-split` skill
- **Backlog**: [ ] Link from LKPR-63 when its issue is created

## Dependencies

- LKPR-28 (inline links on insert) — agent carries forward links ✓ (done)
- LKPR-54 (lore_forget) — agent deletes originals ✓ (done)

---

_Absorbed into LKPR-63 (Dreaming orchestration) as a sub-phase._
