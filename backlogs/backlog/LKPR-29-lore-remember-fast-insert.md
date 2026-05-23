---
id: LKPR-29
title: Add lore_remember for one-shot fast memory insert (friction-killer)
type: feature
status: backlog
priority: critical
sprint: 1
rice_score: ~  # TBD: R:10 I:10 C:90% E:0.5w
filed_by: Akane (PM)
filed_date: 2026-05-24
---

# [LKPR-29] Add lore_remember for one-shot fast memory insert

## Problem

`lore_insert` requires 4 fields: `title`, `content`, `description`, `score`. That's 3 more than the agent's `memory()` tool. Every extra field is a tax paid per memory. The result: I batch-dump at session end into big compound memories instead of writing small atomic ones as insights occur.

**Insert count**: ~50 memories in 3 days. Each required hand-crafting 4 fields. That's 200 field decisions.

## Solution

New MCP tool: `lore_remember(thought: str)` — one argument, one call, zero friction.

```
# Before (4 fields, hand-crafted)
lore_insert(title="Hybrid search formula", content="0.45 semantic...", description="Search scoring", score=7)

# After (1 string, fire and forget)
lore_remember("Hybrid search formula: 0.45 semantic + 0.30 keyword + 0.15 score + 0.10 usage")
```

**Auto-extraction rules:**
- Title = first 80 chars (whitespace-trimmed, ends at sentence boundary if possible)
- Description = first 60 chars of title (or empty if title is short enough)
- Content = the full `thought` string verbatim
- Score = 7 (default for auto-scored). No manual scoring.

**Auto-link:** After insert, query Chroma for top-1 nearest neighbor above 0.75 threshold. If found, auto-link as `related_to` with reason `"auto-linked from lore_remember: {score:.2f}"`. This gives every quick memory at least one connection — reduces orphan count.

## Acceptance Criteria

- [ ] `lore_remember(thought)` inserts a memory with auto-extracted title/desc/score
- [ ] Auto-link to nearest neighbor above 0.75 (single link, not batch)
- [ ] Returns `{id, title, linked_to: {id, score} | null}` — agent sees the link
- [ ] No duplicate check bypass — still uses existing dedup logic
- [ ] No field is required beyond `thought` — zero configuration
- [ ] MCP tool description: "Fast one-shot memory insert. Pass a thought, get a memory with auto-title."

## Affected Files

**Backend:**
- `src/lorekeeper/server.py` — register new tool
- `src/lorekeeper/schemas.py` — LoreRememberInput (just thought: str)
- `src/lorekeeper/handlers.py` — handle_remember handler
- `src/lorekeeper/services/orchestrator.py` — remember service (extract + insert + auto-link)
- `tests/test_orchestrator.py` — test auto-extract, test auto-link

**Dashboard:**
_none_

## Dependencies

_None_ — standalone. Uses existing `memory_engine.insert()` and `link_store.link()`.

## Required Updates

- **CLAUDE.md**: [ ] Update agentic loop section to mention `lore_remember` as the preferred quick-capture path
- **README.md**: [ ] Document `lore_remember` in the MCP tools list
- **Skills**: [ ] Update `memory-splitter` and `memory-reorganizer` skills to use `lore_remember` for creating atomic memories
- **Backlog**: [ ] N/A — no dependency changes

## Open Questions

- Should `lore_remember` accept markdown? Yes — content is stored verbatim, markdown is fine.
- Should it accept a list of thoughts? No — that's what `lore_insert` with batch is for. Keep this single-shot.

## Notes

**This is the highest-impact friction fix.** It removes the biggest barrier to eager memory insertion. Pair with a protocol skill update: "At the moment you learn something interesting, call `lore_remember` immediately — not at session end."

Estimated effort: 0.5 week. Mostly handler + service wiring.