---
id: LKPR-42
title: Context Weaving (lore_weave) — Synthesized Knowledge Briefs from Search Results
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 77
filed_date: 2026-05-27
---

# [LKPR-42] Context Weaving — Synthesized Knowledge Briefs

## Problem

`lore_search` returns a flat list of individual memories — fragments, not a coherent picture. An agent starting a session on "deployment pipeline" gets 5 separate memories about Docker config, CI script, test setup, etc. It has to mentally stitch them together, reconcile contradictions, figure out what's important. This is friction — the agent is thinking about memory *after* retrieval.

## Solution (Requires Research)

`lore_weave(topic, max_memories=8)` — grabs top relevant memories, then uses an LLM call to weave them into a coherent "context block":

- Standalone summary of what's known about the topic
- Explicit contradictions flagged (with confidence details)
- Knowledge gaps called out
- Temporal ordering (recency information)
- Returns structured dict: `{summary, contradictions, gaps, raw_sources}`

Could be an MCP tool or a utility the agent calls after search. The key insight: this bridges "search" and "injection" — makes retrieval actionable without the agent doing cognitive synthesis.

## Acceptance Criteria (Draft — to refine after research)

- [ ] Research: what's the right granularity / cost trade-off for the LLM call?
- [ ] `lore_weave` returns a structured context block with summary, contradictions, gaps
- [ ] Contradictions flagged with confidence details
- [ ] Dashboard can use this for "weave a topic" knowledge briefs

## Affected Files

**Backend:**

- TBD — needs architecture research first

**Dashboard:**

- Potential "explore topic" feature using weave output

## Dependencies

_None_ — but may depend on LKPR-41 (version history makes contradiction detection more meaningful)

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

- LLM call inside an MCP tool? Or separate utility?
- Cost trade-off — an LLM call per weave vs. cheaper summarization approaches
- Should weave be lazy (called by agent after search) or automatic (returned with search results)?

## Notes

Originated from daily-ideas cron (2026-05-27). Idea 2 — needs more research. Keeping as P3 for now.