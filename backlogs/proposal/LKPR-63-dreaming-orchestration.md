---
id: LKPR-63
title: Dreaming orchestration — master cron pipeline for autonomous memory health
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 140
filed_date: 2026-06-05
---

# [LKPR-63] Dreaming orchestration — master cron pipeline for autonomous memory health

## Problem

The Dreaming capabilities (memory splitting LKPR-62, consolidation LKPR-13, contradiction detection LKPR-17, link candidate generation LKPR-58) are individually useful, but without orchestration they never fire automatically. Agents won't remember to run them. The store gradually degrades instead of getting healthier over time.

## Solution

A **master dreaming cron** (`dreaming.sh`) that runs a configurable schedule (default: nightly at 2am) and chains memory health phases in sequence. Each phase is optional — the orchestrator detects which MCP tools are available and skips missing phases gracefully.

**Phases (in order):**

```
1. Batch reflect      — process unreflected sessions (via `lore_processed_sessions` + agent loop)
2. Split compounds    — detect and propose atomic splits (via LKPR-62 `lore_split_candidates`)
3. Find near-dupes    — surface similar pairs for merge consideration (via LKPR-13 `lore_find_nearest_pairs`)
4. Detect conflicts   — find contradictory memories (via LKPR-17 `lore_reconcile`)
5. Generate links     — surface candidate edges (via LKPR-58 `lore_recommend_links`)
6. Decay sweep        — lower scores of old unused memories (built-in)
7. Dream diary        — produce narrative summary (built-in)
```

**Graceful degradation:**

- Phase 2 (split): only runs if `lore_split_candidates` tool exists in the MCP registry
- Phase 3 (consolidation): only runs if `lore_find_nearest_pairs` tool exists
- Phase 4 (reconcile): only runs if `lore_reconcile` tool exists
- Phase 5 (links): only runs if `lore_recommend_links` tool exists
- Phase 1 (reflect), Phase 6 (decay), Phase 7 (diary): always run

**Decay sweep** (Phase 6):

- Scan all memories for: `last_used > 90 days AND usage_count < 3 AND score > 5.0`
- Lower score by `current_score * 0.5` per sweep (diminishing, never below 1.0)
- If score drops below 1.0 AND unused for 180 days → soft-delete with `reason="decayed"`
- Uses existing `lore_update` / `lore_forget` infra
- Configurable via `LORE_DECAY_SWEEP_UNUSED_DAYS` (default: 90) and `LORE_DECAY_SWEEP_CULL_DAYS` (default: 180)

**Dream diary** (Phase 7):

- Write a structured narrative to `data_dir/dreams/YYYY-MM-DD.md`:
  - Date + duration of dreaming cycle
  - Memories reflected, split, merged, decayed, linked
  - Stats: before/after memory count, link count, average score
  - Summary of what the agent should know changed
- Delivered via cron output (stdout → delivery channel) for user visibility
- If the report is empty (nothing changed), output is suppressed

**Cron setup:**

- Default: nightly at 2am via `hermes cron create`
- Agent profile: `default` (uses `lore_reflect`, `lore_search`, etc.)
- Script: `scripts/dreaming.sh` — entry point that calls `hermes sessions export` and runs each phase
- Output: dream diary written to disk + delivered as cron output (compact summary for humans)

## Acceptance Criteria

- [ ] `scripts/dreaming.sh` — shell entry point, detects available tools, runs phases in order
- [ ] Graceful degradation: each phase detects if its tool exists; skips cleanly with log if not
- [ ] Phase 1: batch reflects all unreflected sessions (via agent loop calling `lore_reflect`)
- [ ] Phase 2: calls `lore_split_candidates(n=20, min_length=250)` — outputs breakpoints to diary, agent reviews and applies splits
- [ ] Phase 3: calls `lore_find_nearest_pairs(top_k=20, min_similarity=0.70)` — outputs to diary
- [ ] Phase 4: calls `lore_reconcile(dry_run=True)` — outputs to diary
- [ ] Phase 5: calls `lore_recommend_links(n=10, run_classifier=True)` — outputs to diary
- [ ] Phase 6 (decay sweep): built-in scan, score reduction, optional soft-delete
- [ ] `LORE_DECAY_SWEEP_UNUSED_DAYS` env var (default: 90)
- [ ] `LORE_DECAY_SWEEP_CULL_DAYS` env var (default: 180)
- [ ] Phase 7 (dream diary): written to `data_dir/dreams/YYYY-MM-DD.md` — structured markdown
- [ ] Empty diary suppressed (no changes = no output/no delivery to user)
- [ ] Non-empty diary delivered via cron output to the configured delivery channel
- [ ] Cron job registered: `hermes cron create --schedule "0 2 * * *" --script dreaming.sh`
- [ ] Config env vars registered in `src/lorekeeper/config.py`

## Affected Files

**Scripts:**

- `scripts/dreaming.sh` — new: shell entry point
- `scripts/dream_diary.py` — new: dream diary writer

**Backend:**

- `src/lorekeeper/services/decay_sweep.py` — new: decay sweep logic (Phase 6)
- `src/lorekeeper/config.py` — add `LORE_DECAY_SWEEP_*` env vars
- `src/lorekeeper/server.py` — may need a health-check endpoint for tool discovery

**CLAUDE.md / README:**

- Document dreaming pipeline, schedule, and configuration

## Required Updates

- **CLAUDE.md**: [ ] Document dreaming pipeline, schedule, and configuration
- **README.md**: [ ] Document dreaming cron setup
- **Skills**: [ ] Add `lorekeeper-memory-split` as dreaming phase 2 reference
- **Backlog**: [ ] Link LKPR-62 and LKPR-63 to dreaming orchestration

## Dependencies

- **LKPR-79**: Dreaming session hook + background reflection engine — provides the autonomous reflection that this pipeline orchestrates into a multi-phase cron job.
- **LKPR-9**: Memory decay model — provides the decay state that the pipeline iterates on.

| Phase              | Depends On                                              | Status                   |
| ------------------ | ------------------------------------------------------- | ------------------------ |
| 1. Batch reflect   | `lore_reflect` (done), `lore_processed_sessions` (done) | ✅ All available         |
| 2. Split compounds | LKPR-62 `lore_split_candidates`                         | 📄 Filed with this batch |
| 3. Near-dupes      | LKPR-13 `lore_find_nearest_pairs`                       | 📄 Existing proposal     |
| 4. Conflicts       | LKPR-17 `lore_reconcile`                                | 📄 Existing proposal     |
| 5. Links           | LKPR-58 `lore_recommend_links`                          | 📄 Existing proposal     |
| 6. Decay sweep     | Built-in (this ticket)                                  | 🆕 In scope              |
| 7. Dream diary     | Built-in (this ticket)                                  | 🆕 In scope              |

**This ticket can ship with only Phases 1, 6, and 7 working.** Phases 2-5 are additive — the orchestra degrades gracefully.

## Open Questions

- Should the dreaming cron run in the `default` Hermes profile or a dedicated `dreamer` profile? Default is simpler but means the cron's model credits come from the same pool.
- Should the dream diary be a separate file per cycle or append to a rolling log? Separate files (`dreams/YYYY-MM-DD.md`) with a link from latest to previous.
- What happens if a dreaming cycle takes > 30 minutes? Should the cron have a timeout or checkpoint mechanism? Start with no hard timeout — if it's slow, the next cycle is just delayed. Add timeout after first real-world experience.

## Notes

**Naming:** "Dreaming" is the industry term (OpenClaw, Anthropic, OpenAI all use it). The pipeline is explicitly modeled after OpenClaw's three-phase approach (Light → sort/stage, Deep → score/promote, REM → reflect on themes), adapted to Lorekeeper's MCP architecture.

**Inspiration from OpenClaw:**

- **Light phase** → batch reflect (Phase 1) + decay sweep (Phase 6): sort and stage recent material, clear out what's stale
- **Deep phase** → split compounds (Phase 2) + consolidation (Phase 3) + link candidates (Phase 5): score and promote durable structures
- **REM phase** → conflict detection (Phase 4) + dream diary (Phase 7): reflect on themes, produce narrative

**Design principle:** The orchestrator never auto-writes (except decay sweep, which is deterministic math). All LLM-driven phases return candidates for human/agent review. The dream diary is the review surface.

**Not in scope:**

- The individual MCP tools called by phases 2-5 are separate tickets
- Batch session reflection (Phase 1) reuses existing `lore_reflect` + agent loop — no new platform code needed
- Dream diary is human-readable only — no structured machine input from it
