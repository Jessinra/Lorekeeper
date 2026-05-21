---
name: lorekeeper-search
description: Search the Lorekeeper knowledge base and provide relevance feedback with confidence ratings. Use when the agent needs to recall domain knowledge or query the memory store. Ensures every search ends with a lore_update feedback call (including confidence) to improve knowledge quality over time.
version: 1.0.0
---

# Lorekeeper Search with Feedback

Lorekeeper is a persistent memory store exposed via MCP tools (`lore_search`, `lore_update`, `lore_insert`). It uses hybrid semantic + keyword search to surface relevant knowledge.

**Critical rule**: Every `lore_search` MUST be followed by a `lore_update` feedback call once the task is complete. This feedback loop — including **confidence ratings** — keeps the knowledge base accurate and self-correcting.

## Workflow

### Step 1: Search

Call `lore_search` with a specific natural language query.

```
lore_search({ query: "voucher stacking rules in checkout", min_score: 0.1 })
```

- Use natural language questions, not single keywords
- Raise `min_score` (e.g. 0.3) if results are noisy
- Omit `limit` to use the server's default (set via `LORE_SEARCH_LIMIT` env var or dashboard Config tab)
- Soft-deleted memories (flagged as unreliable) are excluded by default.

### Step 2: Use the results and verify

Each result contains `memory.id`, `memory.title`, `memory.content`, `relevance.combined_score`, and `links`. Use the content for your task and track which memories were helpful.

**Verification step (important)**: While using the results, actively assess whether each memory's content appears factually correct. Cross-reference against the codebase, documentation, or your own knowledge. This verification informs the confidence rating in Step 3.

### Step 3: Provide feedback with confidence (MANDATORY)

**After completing your task**, call `lore_update` with feedback on **every** returned memory, including a **confidence** rating:

```
lore_update({
  memory_feedback: [
    { id: "<memory-uuid-1>", useful: true, confidence: 9 },
    { id: "<memory-uuid-2>", useful: false, confidence: 4 },
    { id: "<memory-uuid-3>", useful: false, confidence: 1 }
  ],
  link_feedback: [
    { id: "<link-uuid-1>", useful: true, confidence: 8 }
  ]
})
```

**Fields**:

- `useful` — whether the memory was relevant to the task
- `confidence` (1–10) — how likely the memory's content is **factually correct**:
  - **1–2**: Definitely or almost certainly wrong. Memory will be **soft-deleted** (excluded from future searches).
  - **3–4**: Likely incorrect or highly suspect.
  - **5–6**: Uncertain — cannot confirm or deny.
  - **7–8**: Likely correct based on available evidence.
  - **9–10**: Confirmed correct (verified against code, docs, or authoritative source).

**Note**: `useful` and `confidence` are independent. A memory can be irrelevant to your task (`useful: false`) but still factually correct (`confidence: 8`). Always rate both honestly.

## Decision Guide

```
Need domain knowledge or facts?
  ├─ YES → lore_search → use results → verify content → lore_update (always, with confidence)
  └─ NO  → skip Lorekeeper
```

If search returns zero results, there is nothing to provide feedback on — proceed normally.

## Example

1. `lore_search({ query: "payment channel integration" })`
2. Results: memory `aaa-111` (payment channels) was relevant and verified correct; memory `bbb-222` (voucher flow) was irrelevant but content looks correct; memory `ccc-333` (old API endpoint) contains outdated info.

3. ```
   lore_update({
     memory_feedback: [
       { id: "aaa-111", useful: true, confidence: 9 },
       { id: "bbb-222", useful: false, confidence: 7 },
       { id: "ccc-333", useful: false, confidence: 2 }
     ]
   })
   ```

   Result: `ccc-333` is soft-deleted because confidence ≤ 2 and useful=false.

## Rules

- **Never skip feedback** — even if no results were useful, mark them all `useful: false` with a confidence rating
- **Always include confidence** — this is how the knowledge base self-corrects over time
- **Verify before rating** — cross-reference memory content against code, docs, or your own knowledge
- **Feedback after task completion** — wait until you have used the results before judging usefulness
- **Batch into one call** — send all feedback in a single `lore_update`, not one per memory
- **Be honest about uncertainty** — if you cannot verify, use confidence 5–6 rather than guessing high
