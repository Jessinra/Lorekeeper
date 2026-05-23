---
id: LKPR-12
title: Implement session end hook for automatic capture (lore_extract_session)
type: feature
status: proposal
priority: high
sprint: 2
rice_score: 36.0  # R:9 I:8 C:50% E:2w
filed_by: Hermes
filed_date: 2026-05-22
---

# [LKPR-12] Implement session end hook for automatic capture (lore_extract_session)

## Problem
Agents must manually remember to call `lore_insert` and `lore_reflect` at session end. In practice this gets skipped or done inconsistently. Valuable learnings are lost. The `loop/hooks/post_session.sh` stub already exists but is not wired up end-to-end.

## Solution
Agent-driven approach (zero extra LLM cost):

1. At session end, agent calls `lore_extract_session(transcript)` 
2. Platform returns a structured prompt scaffold (not LLM output) — just a template to fill in
3. Agent uses its own already-warm LLM to fill in the template and decide what to insert
4. Agent calls `lore_insert` + `lore_reflect` with the results

Alternatively: the protocol skill (LKPR-3) encodes the right prompt pattern — no new MCP tool needed at all.

Key principle: agent's LLM is already warm at session end. Zero marginal cost.

## Acceptance Criteria
- [ ] `loop/hooks/post_session.sh` is implemented and can be triggered at session end
- [ ] Either `lore_extract_session` MCP tool exists OR protocol skill covers this with a prompt pattern
- [ ] Duplicate risk handled: existing dedup should catch most cases; document expected behavior
- [ ] End-to-end test: session transcript in → memories inserted + reflect recorded

## Affected Files
- `loop/hooks/post_session.sh` — implement extraction logic
- `src/lorekeeper/handlers.py` — optional: `lore_extract_session` handler
- New: `src/lorekeeper/services/extractor.py` — extraction service

## Dependencies
_None_ (but most useful after LKPR-8 `lore_wrap_session` is live)

## Open Questions
- Which LLM to use for extraction? (should be cheap — DeepSeek Flash)
- Human review queue: where does it live? Dashboard tab?
- How to get session transcript into the hook reliably?

## Notes
Highest friction point in daily use. Confidence 50% — extraction quality is the hard part. CLAUDE.md already references this as Phase 2 intent.

## Required Updates

- **CLAUDE.md**: [ ] N/A — legacy ticket, filed before convention
- **README.md**: [ ] N/A — legacy ticket, filed before convention
- **Skills**: [ ] N/A — legacy ticket, filed before convention
- **Backlog**: [ ] N/A — legacy ticket, filed before convention
