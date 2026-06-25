---
name: lorekeeper-reconcile
description: Reconcile and fact-check Lorekeeper memories against source materials, existing documentation, and internal consistency. Use when (1) the user provides reference materials to verify against, (2) the user requests a general knowledge audit, or (3) the user wants to verify specific topics. Updates memory scores and soft-deletes incorrect facts.
version: v1.0.0
---

# Lorekeeper Reconciliation Agent

Verify stored memories against authoritative sources to identify incorrect, outdated, or inconsistent facts. Update confidence scores, correct the knowledge base, and fill knowledge gaps with new memories when reference materials contain information not yet captured.

## Verification Methods

Choose whichever method(s) suit the memory being verified. Combine multiple methods when a single one is insufficient.

| Method                  | Tools                  | Use When                                                |
| ----------------------- | ---------------------- | ------------------------------------------------------- |
| Source verification     | web_extract, read_file | User provided URLs/files/docs to check against          |
| Documentation cross-ref | web_search, read_file  | Corroborating against existing documentation            |
| Codebase verification   | search_files, terminal | Technical facts (APIs, error codes, service flows)      |
| Internal consistency    | `lore_search`          | Checking for contradictions/divergence between memories |
| Inference               | Agent reasoning        | No authoritative source available                       |

## Workflow

### Step 1: Gather and Scope

| Input Type           | Action                                                            |
| -------------------- | ----------------------------------------------------------------- |
| URL(s)               | `web_extract` → save content to `.docs-cache/reconcile-{slug}.md` |
| Local files          | Read directly via read_file                                       |
| Topic/domain request | Skip to Step 2                                                    |

### Step 2: Search Lorekeeper

Extract key terms from the reference materials or topic request — domain terms, entity names, process names — and run multiple `lore_search` queries to build a verification queue of unique memories.

```
lore_search({ query: "<natural language query>", min_score: 0.1 })
```

Use `include_deleted: true` when auditing previously soft-deleted memories.

**Track coverage gaps**: note topics or facts from the reference materials that return zero or very low relevance matches — these are candidates for new memories in Step 4.

### Step 3: Verify and Score Each Memory

For each memory, use suitable verification methods (see table above) to reach a verdict. Map the verdict to a confidence score:

| Verdict           | Meaning                                      | Confidence | Action                                   |
| ----------------- | -------------------------------------------- | ---------- | ---------------------------------------- |
| Confirmed         | Source/docs/code validates the claims        | 9-10       | `useful: true`                           |
| Corroborated      | Multiple indirect sources agree              | 7-8        | `useful: true`                           |
| Plausible         | Cannot verify, but no contradicting evidence | 5-6        | `useful: true` or `false` (by relevance) |
| Partially correct | Some claims right, others wrong or outdated  | 3-4        | `useful: false`                          |
| Outdated          | Source describes a newer state               | 2-3        | `useful: false` (2 → soft-deleted)       |
| Contradicted      | Source directly conflicts with the claims    | 1-2        | `useful: false` → **soft-deleted**       |

### Step 4: Update and Correct

Batch all feedback into a single `lore_update` call:

```
lore_update({
  memory_feedback: [
    { id: "<id-1>", useful: true, confidence: 9 },
    { id: "<id-2>", useful: false, confidence: 2 }
  ]
})
```

**When correcting** a soft-deleted memory (confidence ≤ 2) and the correct information is known from an authoritative source:

1. Insert the corrected fact via `lore_insert`.
2. Link the new memory to related existing memories with reason `"Corrected version of soft-deleted memory <old-id>"`.

If the soft-deleted memory contained multiple facts where only some were wrong, split into separate corrected memories.

**When filling gaps** — for topics identified in Step 2 that have no matching memory:

1. Only insert when the information comes from an authoritative source (not inference).
2. Write standalone facts following the memorize skill conventions (one fact per memory, max 250 words).
3. Search for and link to related existing memories.

### Step 5: Report

Present a reconciliation report to the user:

```markdown
## Reconciliation Report

### Scope

- **Sources**: {list of reference materials used}
- **Memories examined**: {count}

### Summary

| Status                                       | Count |
| -------------------------------------------- | ----- |
| Confirmed correct (9-10)                     | N     |
| Likely correct (7-8)                         | N     |
| Uncertain (5-6)                              | N     |
| Corrected (old → soft-deleted, new inserted) | N     |
| New memories (gaps filled)                   | N     |
| Soft-deleted (1-2)                           | N     |

### Findings

- **{memory title}** — confidence: {N}, verdict: {verdict}. {Brief reason}.

### Recommendations

- {Follow-up actions or topics needing further verification.}
```

## Rules

- **Never skip feedback** — every examined memory must receive a `lore_update`, even if uncertain (confidence 5-6).
- **Conservative deletions** — only soft-delete (confidence ≤ 2) with clear evidence. When in doubt, rate 3-4.
- **Conservative insertions** — only insert corrected or new facts from authoritative sources (PRD, TD, docs, code). Never from inference alone.
- **Preserve the graph** — always link corrected memories to related existing ones.
- **Batch processing** — for large audits, process in batches of 10-15. Report progress between batches.

## Example

**User**: "Verify Lorekeeper facts about the authentication module against this doc: <https://docs.example.com/auth>"

1. Extract doc via `web_extract`, save to `.docs-cache/reconcile-auth.md`.
2. Identify topics: token expiry, refresh flow, session handling.
3. Search: `lore_search({ query: "authentication token expiry and refresh" })`, etc.
4. Compare each memory against the doc; for technical claims, also verify via codebase.
5. `lore_update` with confidence ratings; insert corrections for wrong facts and new memories for uncovered topics.
6. Present reconciliation report.

## Link Suggestion Review

The background sweep engine continuously generates pending link candidates. Use these tools as part of a reconciliation pass to promote high-confidence links:

1. **`lore_get_suggestions`** — list pending candidates, sorted by `weighted_score` DESC.
   - Filter by `min_score` (e.g. `0.7`) to surface only high-confidence pairs.
   - `total_pending` shows total workload without a separate count call.
2. **`lore_review_suggestion`** — accept or reject in a single batch call.
   - `action: "accept"` — creates a real `memory_links` row; suggestion retained for audit.
   - `action: "reject"` — marks the pair as rejected; future sweeps skip it.
   - Idempotent per item; returns per-ID `status` (`accepted` / `rejected` / `skipped` / `error`).

**Typical flow during a reconciliation session:**

```json
// 1. Retrieve top candidates
lore_get_suggestions({ "limit": 20, "min_score": 0.6 })

// 2. Review results; accept clearly correct pairs, reject wrong ones
lore_review_suggestion({ "suggestion_ids": ["uuid1", "uuid2"], "action": "accept" })
lore_review_suggestion({ "suggestion_ids": ["uuid3"], "action": "reject" })
```

Accept suggestions that are contextually correct. Reject suggestions that are coincidental or misleading — this trains the sweep engine to skip bad pairs in future runs.

## Related Skills

- **[lorekeeper-protocol]** — Orchestrates when to trigger reconciliation.
- **[lorekeeper-search]** — Use search to surface candidate memories before reconciling.
- **[lorekeeper-memorize]** — After reconciling, re-insert corrected facts.
