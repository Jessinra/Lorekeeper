---
name: lorekeeper-search
description: Search the Lorekeeper knowledge base and provide relevance feedback with confidence ratings. Use when the agent needs to recall domain knowledge, look up facts, or query the memory store. Ensures every search ends with a lore_update feedback call (including confidence) to improve knowledge quality over time.
version: v2.0.0
---

# Lorekeeper Search with Feedback

Lorekeeper is a persistent memory store exposed via MCP tools (`lore_search`, `lore_update`, `lore_insert`). It uses hybrid semantic + keyword search to surface relevant knowledge.

**Critical rule**: Every `lore_search` MUST be followed by a `lore_update` feedback call once the task is complete. This feedback loop — including **confidence ratings** — keeps the knowledge base accurate and self-correcting.

## Workflow

### Fresh-news / time-sensitive searches

When the task is about news, releases, or anything that must be recent:

- Search with explicit date anchors and primary-source domains.
- Verify the publish date on every candidate before using it.
- Skip anything older than the requested cutoff or whose date cannot be confirmed.
- Treat aggregators as discovery only; prefer official blogs, docs, GitHub releases, arXiv, and government pages.
- If nothing meets the cutoff, returning nothing is correct.

See `references/news-freshness.md` for a compact checklist.

### Step 1: Search

Call `lore_search` with a specific natural language query.

```
lore_search({ query: "voucher stacking rules in checkout", limit: 10, min_score: 0.1 })
```

- Use natural language questions, not single keywords
- Raise `min_score` (e.g. 0.3) if results are noisy; lower `limit` if you need fewer results
- Soft-deleted memories (flagged as unreliable) are excluded by default.
- **Filter by recency**: `created_after` / `updated_after` accept ISO 8601 UTC strings (naive = UTC; non-UTC offsets raise an error). Use to scope searches to a time window, e.g. `created_after: "2026-06-01T00:00:00"`.
- **Change sort order**: `sort_by` accepts `"relevance"` (default, by hybrid score), `"recent"` (by `updated_at DESC`), or `"frequent"` (by `usage_count DESC`). Composes with timestamp filters and `limit`.

### Step 2: Use the results and verify

Each result contains `memory.id`, `memory.title`, `memory.content`, `relevance.combined_score`, and `links`. Each link has its own `id`, `relation_type`, `reason`, `source_memory_id`, and `target_memory_id`.

While using the results:

- Track which **memories** were helpful and verify their factual accuracy
- Assess each **link**: does the stated relationship (`reason`) make sense? Does it correctly connect the two memories?

This dual verification informs both memory and link confidence ratings in Step 3.

### Step 3: Provide feedback with confidence (MANDATORY)

**After completing your task**, call `lore_update` with feedback on **every** returned memory **and every link** from those results.

```
lore_update({
  memory_feedback: [
    { id: "<memory-uuid-1>", useful: true, confidence: 9 },
    { id: "<memory-uuid-2>", useful: false, confidence: 4 },
    { id: "<memory-uuid-3>", useful: false, confidence: 1 }
  ],
  link_feedback: [
    { id: "<link-uuid-1>", useful: true, confidence: 8 },
    { id: "<link-uuid-2>", useful: false, confidence: 3 }
  ]
})
```

**How to get link IDs**: Each search result has a `links` array. Each element has an `id` field — use that as the link feedback `id`.

**Fields** (same semantics for both memories and links):

- `useful` — whether the memory/link was relevant to the task (for links: whether following the relationship led you to something useful)
- `confidence` (1–10) — how likely the content/relationship is **factually correct**:
  - **1–2**: Definitely or almost certainly wrong. Memory will be **soft-deleted** (excluded from future searches).
  - **3–4**: Likely incorrect or highly suspect.
  - **5–6**: Uncertain — cannot confirm or deny.
  - **7–8**: Likely correct based on available evidence.
  - **9–10**: Confirmed correct (verified against code, docs, or authoritative source).

**Critical: `useful` and `confidence` interact — understand the difference before rating:**

- **False positive** (memory appeared but is about an unrelated topic, content is valid): `useful: false, confidence: 7–9` → ranking penalty only, memory is **NOT deleted**
- **Wrong/stale content** (the memory itself contains incorrect or outdated facts): `useful: false, confidence: 1–2` → memory is **soft-deleted**
- **Correct and on-topic**: `useful: true, confidence: 7–10` → score boosted
- **Uncertain relevance**: `useful: false, confidence: 5–6` → slight penalty, kept

⚠️ Only use `confidence: 1–2` when the **content is factually wrong or stale** — not simply because it was an irrelevant search result. Using low confidence on a valid-but-off-topic memory will delete it permanently.

## Decision Guide

```
Need domain knowledge or facts?
  ├─ YES → lore_search → use results → verify content → lore_update (always, with confidence)
  └─ NO  → skip Lorekeeper
```

If search returns zero results, there is nothing to provide feedback on — proceed normally.

## Example

1. `lore_search({ query: "Python async patterns in service layer" })`
2. Results:

   - Memory `aaa-111` (async patterns) — relevant, verified correct. Has link `lnk-001` → `bbb-222` (`references`, reason: "retry logic depends on async context"). Relationship is valid.
   - Memory `bbb-222` (retry logic) — irrelevant to this task, content looks correct. Has link `lnk-002` → `ccc-333` (`part_of`, reason: "old sync API used in retry flow"). Old API was removed — link is stale.
   - Memory `ccc-333` (old sync API) — outdated info.

3. ```
   lore_update({
     memory_feedback: [
       { id: "aaa-111", useful: true, confidence: 9 },
       { id: "bbb-222", useful: false, confidence: 7 },
       { id: "ccc-333", useful: false, confidence: 2 }
     ],
     link_feedback: [
       { id: "lnk-001", useful: true, confidence: 8 },
       { id: "lnk-002", useful: false, confidence: 2 }
     ]
   })
   ```

   Result: `ccc-333` is soft-deleted (confidence ≤ 2, useful=false). `lnk-002` score drops toward removal.

## Rules

- **Never skip feedback** — even if no results were useful, mark them all `useful: false` with a confidence rating
- **Always include confidence** — this is how the knowledge base self-corrects over time
- **Rate links too** — collect all link IDs from `results[].links[].id` and include them in `link_feedback`
- **Link confidence** = whether the stated relationship is factually correct; **link useful** = whether following it led somewhere valuable
- **Verify before rating** — cross-reference memory content against code, docs, or your own knowledge
- **Feedback after task completion** — wait until you have used the results before judging usefulness
- **Batch into one call** — send all feedback in a single `lore_update`, not one per memory
- **Be honest about uncertainty** — if you cannot verify, use confidence 5–6 rather than guessing high

## Related Skills

- **[lorekeeper-protocol]** — The full session protocol orchestrating when to search.
- **[lorekeeper-memorize]** — Companion: search first, then insert new discoveries.
- **[lorekeeper-reconcile]** — When search returns suspected stale data, run reconcile to fact-check.
