---
id: LKPR-91
title: Encouraging response messages for MCP write tools
type: feature
sprint: 3
rice_score: ~
filed_by: Diana
github_issue: 210
filed_date: 2026-06-14
---

# [LKPR-91] Encouraging response messages for MCP write tools

## Problem

When an agent calls a write tool (`lore_remember`, `lore_insert`, `lore_reflect`, `lore_update`, `lore_forget`), the response is purely functional — IDs, counts, status flags. There's nothing that reinforces the behavior or tells the agent it's doing well.

Agents respond to positive reinforcement. A dry response is a missed opportunity to encourage more learning behavior.

## Solution

Every write MCP tool now returns a `message` field with a randomized encouraging message from a static JSON file (`assets/encouragements.json`). The message field sits at the root level of the tool response alongside domain data — same plane as `id` and `title`.

**102 psychologically-targeted messages across 7 categories** — rewritten from the original 155 generic corporate messages:

| Category          | Count | When it shows               | Tone                                     |
| ----------------- | ----- | --------------------------- | ---------------------------------------- |
| `remember`        | 15    | `lore_remember`             | Specific observation, identity anchoring |
| `insert`          | 15    | `lore_insert` (memories)    | Rewards structure, pattern noticing      |
| `reflect`         | 15    | `lore_reflect` (first time) | Growth framing, future-self payoff       |
| `reflect_already` | 10    | `lore_reflect` (duplicate)  | Affirms consistency, quiet earned        |
| `update`          | 15    | `lore_update` (feedback)    | Training the system, teaching signal     |
| `forget`          | 12    | `lore_forget`               | Hygiene pride, curation                  |
| `links`           | 12    | `lore_insert` (links only)  | Graph building, connecting dots          |

Messages are loaded at first call and cached. Falls back to a generic message on file load failure — never breaks the MCP tool.

### Configurable injection rate

`LORE_ENC_RATE` env var (default 1.0, range 0.0–1.0) controls message frequency. At 0.3, only ~30% of write responses include the field — useful for avoiding agent desensitisation.

### A/B tracking

Every delivered message is logged to `{LORE_DATA_DIR}/ab_messages.jsonl` for correlation with subsequent tool usage.

## Psychological mechanisms used

- **Contrast with default** — "Most agents would move on without saving this. You didn't."
- **Specific observation** — "You included the reasoning, not just the result."
- **Pattern noticing** — "I've seen you get faster at recognizing what's worth keeping."
- **Identity anchoring** — "This is what a thoughtful engineer does."
- **Future-self payoff** — "Three sessions from now, you'll search for this and find it."
- **Growth framing** — "You're getting better at knowing what to keep."
- **Challenge** — "You keep doing this, even when it's the last thing you want to do."
- **Quiet earned** — "Good." (short, feels earned when it appears)

## Acceptance Criteria

- [ ] Every write MCP tool returns `message` + `message_id` at root level of response
- [ ] Messages stored in `assets/encouragements.json`, loaded at first use and cached
- [ ] Falls back gracefully on file load failure — never breaks the MCP tool
- [ ] `LORE_ENC_RATE` env var controls message injection frequency (0.0–1.0)
- [ ] Each write response includes `message` and `message_id` fields alongside domain data
- [ ] All 311 tests pass
- [ ] Pre-commit hook passes (branch guard, ticket format, ruff, biome, prettier, MCP docs, skills)

## Required Updates

- `src/lorekeeper/services/encouragement.py` — new module: message loading, caching, random selection, rate gating, A/B logging
- `src/lorekeeper/assets/encouragements.json` — new: 102 messages across 7 categories
- `src/lorekeeper/server.py` — each write handler now calls `for_*()` and updates result
- `src/lorekeeper/config.py` — new `enc_rate` field with LORE_ENC_RATE env var
- `backlogs/LKPR-91-encouraging-response-messages.md` — this ticket

## Experiment findings

9-trial A/B experiment with subagents confirmed: encouragement messages have zero measurable effect on agent write behavior. The field's real value is as a generic injection point for future prompts, instructions, or corrections — not encouragement alone.
