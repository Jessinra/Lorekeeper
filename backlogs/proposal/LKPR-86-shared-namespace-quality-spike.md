---
id: LKPR-86
title: Shared namespace quality spike — multi-agent stress test
type: research
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-11
depends_on: LKPR-31
github_issue: 197
---

# [LKPR-86] Shared namespace quality spike — multi-agent stress test

## Problem

The quality feedback loop (score adjustment → decay → soft-delete) was designed for single-agent personal use. The team tier thesis assumes it still works in a shared namespace with multiple agents inserting, updating, and rating memories about overlapping topics. This is **the most dangerous unvalidated assumption in the roadmap**.

Diana's risk analysis flags it explicitly: conflicting memories, stale-but-fresh-looking data (low usage prevents decay), private-polluting-shared misroutes, and adversarial dynamics where one noisy agent degrades scores for everyone. The fundamental question: _Is the quality loop still an advantage in shared namespace, or does it become a liability?_

LKPR-31 (LanceDB) enables concurrent multi-agent writes. We can now spike this without building any team-tier infrastructure (no auth, no RBAC, no multi-namespace).

## Solution

A single **stress-test script** (`scripts/spike_shared_quality.py`) that simulates shared-namespace usage and measures quality degradation:

**Simulation scenarios (run sequentially, one script):**

1. **Harmonious** — 3 agents insert non-overlapping topics (API design, frontend, infra), query each other's territory. Expected: quality loop helps cross-pollinate.
2. **Conflicting facts** — 2 agents store contradictory versions of the same team decision (before/after pivot). Measure whether score/decay resolves the stalemate or gets stuck.
3. **Noisy agent** — 1 agent bulk-inserts 200 low-quality memories about topic X. Measure whether the feedback loop suppresses them, or if they pollute search results for all agents.
4. **Stale signal** — Insert a fact, let it age with no usage for 7 simulated days. Insert a contradictory update. Does the stale memory remain high-score because it was never rated, or does decay handle it?

**Measured outputs:**

- Search precision@5 before vs after each scenario
- Score variance across conflicting memories
- Percentage of low-quality memories in top-20 search results
- Time to suppress a noisy agent's garbage (how many explicit `useful=False` flags needed)

**Duration:** Run overnight. Report results to `backlogs/research/`.

## Acceptance Criteria

- [ ] Script runs against existing Lorekeeper (LKPR-31+), no new infrastructure needed
- [ ] Each scenario produces before/after metrics
- [ ] Results documented in `backlogs/research/` with recommendation: "proceed to team tier" or "requires [X] changes to shared namespace quality loop"
- [ ] If quality loop fails in any scenario, document the specific failure mode and propose fix scope

## Affected Files

**New:**

- `scripts/spike_shared_quality.py` — stress test script (single file, ~200 lines)
- `backlogs/research/lkpr79-results.md` — output report

**Modified:**

- `pyproject.toml` — add `faker` to dev dependencies (optional, for realistic memory content)

## Dependencies

- LKPR-31: done — LanceDB enables concurrent writes, needed for multi-agent simulation

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A — results may inform `lorekeeper-pm` skill risk section
- **Backlog**: [ ] If quality loop passes → unblock team tier (LKPR-38/39/40). If fails → new follow-up tickets for shared namespace quality fixes
