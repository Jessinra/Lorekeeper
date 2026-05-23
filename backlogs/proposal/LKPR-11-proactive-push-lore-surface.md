---
id: LKPR-11
title: Add lore_surface for proactive memory push
type: feature
status: proposal
priority: medium
sprint: 2
rice_score: 24.0  # R:8 I:6 C:50% E:2w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-11] Add lore_surface for proactive memory push

## Problem
Lorekeeper is purely reactive — you ask, it answers. The agent must know what to search for. But the most valuable memory is often the one you didn't know to ask about.

## Solution
New MCP tool: `lore_surface(context_hint: str)` — agent passes a brief description of what it's about to do; lorekeeper returns 2–3 memories the agent *didn't explicitly ask for* but are likely relevant.

Scoring pass prioritizes:
- Semantically adjacent (not direct match)
- Recently not-surfaced (high novelty value)
- Highly linked (many connections = probably important)

Example:
```
Agent: lore_surface("building lorekeeper hybrid search improvements")
→ "Last session you flagged the semantic scale probe as #1 risk"
→ "Open decision: whether to expose decay_factor in search output"
→ "Warning: dedup threshold was set to 0.85 but never load-tested"
```

## Acceptance Criteria
- [ ] `lore_surface(context_hint)` returns 2–3 memories not directly queried by the agent
- [ ] Results are distinct from a plain `lore_search` on the same hint (different scoring pass)
- [ ] Registered as MCP tool in `server.py`
- [ ] Protocol skill (LKPR-3) updated to include `lore_surface` at session start

## Affected Files
- `src/lorekeeper/handlers.py` — new handler
- `src/lorekeeper/server.py` — register tool
- `src/lorekeeper/services/search.py` — proactive scoring variant

## Dependencies
- LKPR-4 (novelty ranking) — `lore_surface` reuses the novelty scoring logic; build after

## Open Questions
- How does "adjacency without direct match" differ concretely from current search? Needs careful tuning.
- How many results max? 2–3 to avoid noise.

## Notes
Confidence 50% — the value is clear but "proactive relevance" scoring needs design work. Do not build before LKPR-4 (novelty ranking) is live.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
