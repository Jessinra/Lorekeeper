# Lorekeeper Nightly Review — 2026-05-21

**Branch:** main @ 59108c4

## Upstream Changes
No new commits since last review. Local HEAD is at origin/main.

## What's New

### `backlogs/` — 13 Feature Proposals (untracked)
A new `backlogs/` directory appeared with 13 markdown files filed by the PM/hermes agent. These are feature proposals for the next phases of lorekeeper development.

**Sprint 1 — Quick Wins (highest RICE, ready now):**
1. **Agent Workflow Protocol Skill** (RICE: 45) — A reusable `skills/lorekeeper-protocol.md` skill file encoding the full usage protocol. Encodes the intelligence layer at zero platform cost.
2. **Memory Decay Model** (RICE: 44.8) — Time-decay multiplier in hybrid scoring via `LORE_DECAY_LAMBDA`. No schema changes needed. Old memories fade, high-usage ones resist.
3. **Iterative Search** (RICE: 42.5) — New `lore_search_refine` tool to narrow results within a prior candidate set. Pure query logic, ~0.5 weeks.
4. **Agent Introspection Tools** (RICE: 32.4) — `lore_health` + `lore_stats` for memory store self-audit. SQL queries over existing schema.

**Sprint 2 — Core Experience (next tier):**
5. `lore_wrap_session` compound tool (RICE: 38.0)
6. Session end hook / auto-extract (RICE: 36.0)
7. `lore_init` onboarding tool (RICE: 35.0)
8. Context budgeting + novelty ranking (RICE: 31.5)
9. Proactive `lore_surface` (RICE: 24.0) — depends on novelty ranking

**Sprint 3 — Intelligence Layer (longer horizon):**
10. Cross-session topic observer (RICE: 12.1)
11. Sleep cycle consolidation (RICE: 11.7)

**Deferred:**
12. Multi-agent tenancy (RICE: 8.4) — don't build yet, no second agent live
13. Optimize reflection dedup — low priority, informational

## No code/session changes

No source code (`src/`), session logs (`loop/sessions/`), or test changes were made since last review.

## Action Items
- Sprint 1 items are independent and can be parallelized — ready for scheduling
- No upstream commits to merge; repo is clean
- `backlogs/` is untracked — needs a `.gitignore` decision (track as proposals or ignore)