# Dreaming: Background Memory Consolidation for AI Agents

**Researched:** 2026-06-05 | **Source:** Jason asking about "OpenAI Dreaming tech"

---

## What "Dreaming" Is

A scheduled background process that runs between agent sessions to:

1. **Read** past session transcripts + current memory store
2. **Curate** — deduplicate, merge contradictions, surface new patterns, drop stale entries
3. **Write** back a cleaner, more useful memory store

The human-sleep analogy is marketing, but the mechanism is real and the results (6x task completion lifts) are verified.

---

## Three Major Implementations (June 2026)

### 1. OpenClaw Dreaming (open-source)

- **Docs:** docs.openclaw.ai/concepts/dreaming
- **Status:** Stable, opt-in (disabled by default)
- **Phase model** inside `memory-core`:

| Phase     | Purpose                                 | Durable Write                           |
| --------- | --------------------------------------- | --------------------------------------- |
| **Light** | Sort & stage recent short-term material | No (machine state in `memory/.dreams/`) |
| **Deep**  | Score and promote durable candidates    | Yes → `MEMORY.md`                       |
| **REM**   | Reflect on themes and recurring ideas   | No (narrative `DREAMS.md` diary)        |

- Ingest redacted session transcripts into dreaming corpus
- "Dream Diary" is human-readable, NOT a promotion source — only grounded snippets promote
- Backfill lane for historical review/recovery

### 2. Anthropic Claude Dreaming (Research Preview, May 6 2026)

- **For:** Managed Agents only (not consumer Claude)
- **Input:** Up to 100 session transcripts + existing memory store
- **3 steps:** Read → Curate (merge/split/update/replace) → Output new store
- **Key rule:** Original store is NEVER touched — you review the output before applying
- **Result:** Harvey reported **~6x task-completion rate** on legal-drafting workflows
- **Models supported:** Claude Opus 4.5, Claude Sonnet 4.5
- **Billing:** Standard API token rates

### 3. ChatGPT Dreaming V3 (OpenAI, June 4 2026)

- **Status:** Rolling out to Plus/Pro (US first)
- Moves beyond the old "save this" Post-It note memory into ambient pattern detection
- **Evaluated on 3 criteria:**
  - Carrying forward context across sessions
  - Following user preferences automatically
  - Staying current (not stale) over time

---

## Shared Architecture Patterns

All three converge on:

- **Background async process** (not inline during live sessions)
- **Read-session-curate cycle** (not real-time streaming)
- **Human-in-the-loop review** before applying (Anthropic strongest on this)
- **No model weight changes** — it's a maintenance layer on external memory store

---

## Comparison: LKPR-58 vs Dreaming

| Dimension            | LKPR-58 (Smart Link Pipeline)                                             | Dreaming                                          |
| -------------------- | ------------------------------------------------------------------------- | ------------------------------------------------- |
| **What it modifies** | Edges between nodes (memory links)                                        | Node content + metadata                           |
| **Input**            | Existing memories                                                         | Past session transcripts + existing memory store  |
| **Pipeline**         | Cosine + BM25 + NER + Temporal → LLM classifier                           | Light→Deep→REM phases                             |
| **Output**           | Candidate link pairs (related_to / contradicts / supersedes / depends_on) | Cleaned memory store (deduped, merged, refreshed) |
| **Auto-write?**      | No — agent reviews first                                                  | No — human/agent reviews first                    |
| **Dependencies**     | Embedding index, BM25, spaCy                                              | Session store, reflection system                  |
| **Status**           | S:Proposal (not implemented)                                              | Not implemented in Lorekeeper                     |

**They are complementary, not the same.**

- LKPR-58 improves _graph density_ — connecting existing nodes so `lore_related` works
- Dreaming improves _node quality_ — cleaning stale/contradictory/duplicate entries and extracting new facts from raw session data
- They share infra: embeddings, BM25, entity extraction, temporal scoring

---

## How This Could Apply to Lorekeeper

Lorekeeper already has ~60% of the pieces:

- ✅ `lore_reflect` — per-session reflection (sequential)
- ✅ `hermes sessions export` — access to session transcripts
- ✅ Embedding index (Chroma/LanceDB)
- ✅ BM25 keyword index
- ✅ `lore_update` with confidence scoring
- ❌ **No automated memory health sweep** — no cron that batch-checks for contradictions, staleness, or duplicates
- ❌ **No draft-store workflow** — no "preview before apply" like Anthropic does
- ❌ **No batch session ingestion** — 100 transcripts at a time
- ❌ **No temporal decay sweep** — old memories with low usage should naturally sink

### Highest-ROI First Step

A **weekly memory health cron** ("dreaming.sh") that:

1. Reads all sessions since last run
2. Batch-checks for:
   - Contradictions (two facts saying opposite things about same entity)
   - Stale entries (low usage + old timestamp → sink score)
   - Dense compound memories that should be split
   - Related memories missing links
3. Produces a report (not auto-applies)
4. Agent reviews and acts

---

---

## Existing Lorekeeper Tickets — Dreaming Landscape Map

### Already Done

| Ticket      | Capability                 | What it does                                                                                                              |
| ----------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **LKPR-9**  | Query-time time decay      | `e^(-λ · days_since_last_used)` applied at search re-rank. Old memories naturally rank lower without stored score change. |
| **LKPR-54** | `lore_forget`              | Soft-delete stale/bad memories with reason tracking. Reversible at DB level.                                              |
| **LKPR-60** | `_all_memories` cache      | In-process cache of all memory metadata — enables fast batch scans without DB round-trips.                                |
| **LKPR-30** | `lore_reflect` auto-insert | Reflection MCP tool that auto-inserts `factual_discoveries` + `lessons_learnt` as memories.                               |
| **LKPR-27** | Auto-link on insert        | When inserting new memory, automatically find and link up to K most similar existing memories.                            |
| **LKPR-28** | Inline links on insert     | `lore_insert` accepts inline `links[]` array for immediate linking.                                                       |
| **LKPR-16** | False dedup guard          | `is_duplicate` check on insert prevents creating near-identical memories.                                                 |

### Already Proposed (not implemented)

| Ticket      | Capability             | Key Idea                                                                                                            | Path                 |
| ----------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **LKPR-13** | Memory consolidation   | `lore_find_nearest_pairs(top_k, min_similarity)` — pure vector math, agent decides merge/keep/delete. Nightly cron. | `backlogs/proposal/` |
| **LKPR-17** | Conflict resolution    | `lore_reconcile` — detects contradictory memories on same topic, scores by recency+confidence.                      | `backlogs/proposal/` |
| **LKPR-58** | Smart link pipeline    | Two-stage: Cosine+BM25+NER+Temporal → LLM classifier. `lore_recommend_links` MCP tool.                              | `backlogs/proposal/` |
| **LKPR-42** | Context weaving        | `lore_weave` — LLM synthesizes search results into a coherent brief with contradictions and gaps.                   | `backlogs/proposal/` |
| **LKPR-41** | Memory version history | `lore_history / lore_diff / lore_rollback` — versioned memories for audit and rollback.                             | `backlogs/proposal/` |
| **LKPR-8**  | Session wrap tool      | `lore_wrap_session` — reflect + health check in one compound MCP call.                                              | `backlogs/proposal/` |
| **LKPR-5**  | Topic observer         | `lore_get_topic_reflections` — cross-session topic synthesis, agent-driven.                                         | `backlogs/proposal/` |
| **LKPR-46** | Daily digest           | Cron-generated summary of new memories, top hits, low-confidence nudges.                                            | `backlogs/proposal/` |
| **LKPR-2**  | Introspection tools    | `lore_health / lore_stats` — store health metrics for agent decision-making.                                        | `backlogs/proposal/` |
| **LKPR-23** | Spaced repetition      | Active recall scheduling — periodically re-expose important memories to prevent decay.                              | `backlogs/proposal/` |

### Gaps (No Tickets)

| Capability                      | What's Missing                                                                                                                | Why It Matters                                                                                                     |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Memory splitting**            | Detect compound memories with multiple distinct facts, propose atomic split point                                             | Single biggest source of noise — agents batch-dump into big compound entries. Splitting improves search precision. |
| **Dreaming orchestration cron** | Master cron that chains all phases: reflect → split → reconcile → consolidate → link → decay → diary                          | Without orchestration, the individual capabilities (LKPR-13/17/42/58) are useful but never fire automatically.     |
| **Temporal decay sweep**        | Maintenance operation that permanently lowers stored scores of old, unused memories (distinct from LKPR-9's query-time decay) | LKPR-9 only masks stale content at query time, doesn't clean it. Sweep gradually shrinks the active corpus.        |

### Proposed Ticket Split

| Ticket      | Title                                        | Scope                                                                                                  | In Platform?                                                 |
| ----------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| **LKPR-62** | Memory splitting — `lore_split_candidates`   | SQL query + length filter. Returns longest N memories over threshold. Agent segments with its own LLM. | ✅ No LLM — just SQL                                         |
| **LKPR-63** | Dreaming orchestration — master cron + diary | Cron script chains phases. Decay sweep (pure math). Dream diary writer.                                | ✅ No LLM — deterministic math + structured output           |
| LKPR-13     | Consolidation pairs                          | Vector dot-product nearest-pairs                                                                       | ✅ Pure math (existing proposal)                             |
| LKPR-58     | Link candidate pipeline                      | Stage 1: pure math; Stage 2: classifier runs in agent                                                  | ✅ Stage 1 in platform, Stage 2 on agent                     |
| LKPR-17     | Conflict resolution                          | ⚠️ Needs revision — "auto-merge" implies LLM                                                           | ❌ Would need LLM — must be re-scoped to pure detection only |

### Hard Constraint

**No LLM calls on the Lorekeeper platform.** Lorekeeper is a pure-math + SQL MCP server. Any reasoning, classification, segmentation, or synthesis work returns raw data to the agent, which uses its own model to process it.

This means:

- LKPR-62: detection only (embedding self-similarity), agent splits
- LKPR-58 Stage 2: runs on agent side, not as a Lorekeeper LLM call
- LKPR-17: must be re-scoped to pure-math contradiction detection (temporal ordering + embedding overlap), agent resolves
- LKPR-13: already pure vector math ✓
- LKPR-63 already respects this ✓
- LKPR-42 (context weaving): would be an agent-side utility, not a Lorekeeper tool

---

## References

- OpenClaw Dreaming docs: https://docs.openclaw.ai/concepts/dreaming
- Anthropic Claude Dreaming (Ars Technica): https://arstechnica.com/ai/2026/05/anthropics-claude-can-now-dream-sort-of/
- Anthropic Claude Dreaming (Enterprise DNA): https://enterprisedna.co/resources/news/anthropic-claude-dreaming-self-improving-agents-2026/
- ChatGPT Dreaming V3 (MakeUseOf): https://www.makeuseof.com/chatgpt-now-remembers-your-preferences-automatically-and-it-actually-works/
- Claude Dreaming vs ChatGPT Memory (Fello AI): https://felloai.com/what-is-claude-dreaming/
- OpenClaw GitHub issue on memory consolidation: https://github.com/openclaw/openclaw/issues/43002
