---
name: lorekeeper-protocol
description: "Full session protocol for using Lorekeeper MCP tools. Load at session start. Covers Phase 1 (search), Phase 1.5 (reconstruction), Phase 2 (topic shift), Phase 3 (reflect), and Phase 4 (health)."
version: v2.0.1
---

# Lorekeeper Protocol

Follow this protocol every session to keep your memory store accurate, healthy, and growing.

Inspired by MRAgent (Ji et al., NUS, ICML 2026): **memory is reconstructed, not retrieved.** Actively explore the memory graph — search, reason, follow links, prune dead ends, repeat.

## Phase 1 — Session Start

**Trigger:** Beginning of every session, before any substantive work.

1. Identify the session topic (1–3 keywords).
2. Search: `lore_search({ query: "<topic>", min_score: 0.15, include_links: true })`
3. Read all returned memories — decisions, constraints, patterns.
4. Provide feedback: `lore_update({ memory_feedback: [{ id: "<id>", useful: true/false }] })`
5. If fewer than 3 results, run a broader fallback search.

**Do not skip.** Working without context causes duplicate inserts and contradictory decisions.

## Phase 1.5 — Active Memory Reconstruction

**Trigger:** After Phase 1, before acting on retrieved memories.

Run the reconstruction loop until the surface is exhausted:

```
1. READ top results. 2. REASON about what's still unknown. 3. TRAVERSE links from high-value memories. 4. SEARCH for inferred cues. 5. PRUNE dead ends. 6. REPEAT. BREAK when 2 consecutive iterations return no novel results.
```

**Rule:** If you've read a memory and still have open questions, run another search — don't settle for the first batch.

## Phase 2 — Mid-Session (Topic Shift)

**Trigger:** Conversation shifts to a new domain, subsystem, or question.

1. Run a fresh `lore_search` for the new topic.
2. Follow links from already-known relevant memories.
3. Provide feedback. If connected to explored topic, run reconstruction at reduced depth (1–2 iterations).

**Rule:** If you're reasoning about something you haven't searched for, search first.

## Phase 3 — Session End

**Trigger:** End of every session.

1. Insert new memories for decisions, root causes, architecture insights, user corrections, patterns.
2. Store with cues in mind: insert explicit `references` links to related memories.
3. Reflect: `lore_reflect({ session_id, summary, topic, task_type, what_was_done, decisions, lessons_learnt, good_patterns, factual_discoveries, memory_ids })`

## Phase 4 — Health Maintenance

**Trigger:** When you notice stale, contradictory, or orphaned memories.

1. Search for duplicates. 2. Consolidate with `lore_insert(force: true)`. 3. Mark old versions `lore_update(useful=false)`. 4. Add `supersedes` links.

## Rules

- **Search before insert** — prevents fragmentation from duplicates
- **Feedback after every search** — quality signals propagate
- **Reconstruct, don't just retrieve** — one-shot search is a starting point
- **Prune dead ends actively** — `lore_update(useful=false)` trains the relevance system
- **Follow links** — the memory graph's edge structure is more informative than flat search
- **One fact per memory** — dense memories degrade search precision
- **Standalone memories** — must make sense with zero conversation context
- **User corrections are gold** — insert immediately when pushed back on
- **Session end is not optional** — `lore_reflect` feeds the consolidation loop

## Pitfalls

- **`__NEW__` is not a valid ID placeholder** — Use inline links or a two-step insert.
- **Duplicate session IDs block auto_insert** — Always use unique session IDs.
- **Consolidated memories are landing pages** — Read `source_type: consolidated` memories first.
- **`lore_search` with `ids` bypasses scoring** — `combined_score` will be 0.0. Normal for exact-lookup mode.
- **Link types are strict** — Only `causes`, `contradicts`, `depends_on`, `derived_from`, `part_of`, `references`, `supersedes` are valid.

## Tool Signatures

See `references/tool-signatures.md` for full parameter schemas of all tools.

## Related Skills

- **[lorekeeper-memorize]** — Phase 3: capture mid-session discoveries.
- **[lorekeeper-search]** — Phase 1: search past memories at session start.
- **[lorekeeper-reconcile]** — Phase 4: reconcile and fact-check memories periodically.
- **[lorekeeper-link-memories]** — Full workflow for `lore_recommend_links`.
- **[recursive-self-improvement]** — The identity layer driving _why_ and _when_ to use this protocol.
- **[reflect]** — The daily cron complement: exports sessions and calls lore_reflect.
