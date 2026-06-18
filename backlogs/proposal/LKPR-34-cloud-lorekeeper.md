---
id: LKPR-34
title: Cloud Lorekeeper — shared memory across agent machines
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Hermes
github_issue: 67
filed_date: 2026-05-27
updated_date: 2026-06-18
---

# [LKPR-34] Cloud Lorekeeper — shared memory across agent machines

## Problem

Multiple Hermes personas on separate machines each have their own isolated Lorekeeper DB. No shared space means no cross-agent awareness — Agent A can't surface a finding to Agent B unless the human relays it manually.

## Solution

Lightweight hosted Lorekeeper that agents explicitly push/pull from. Add a `source` field to identify which agent wrote what. Keep local DBs fully private.

Primary initial workload: **dreaming (LKPR-79)** — the cloud worker pulls unprocessed sessions from local Lorekeeper instances, runs reflection + link discovery, and syncs results back. This is the concrete trigger that justifies the cloud infra: local server captures sessions, cloud server does the LLM work.

Implementation details (hosting, transport, auth) scoped as needed to support the sync-dream-sync loop.

## Acceptance Criteria

- [ ] Cloud Lorekeeper exists and can be deployed (Docker / simple server)
- [ ] `source` field on memories, filterable on search
- [ ] Agents explicitly push/pull — no auto-sync

## Required Updates

- **CLAUDE.md**: [ ] add `source` field docs
- **README.md**: [ ] cloud deployment instructions
- **Skills**: [ ] N/A
- **Backlog**: [x] Update when dreaming (LKPR-79) lands — LKPR-79's cloud dreaming worker will be the first major workload running on Cloud Lorekeeper. Add sync endpoints for unprocessed sessions + dreaming results.

## Notes

Moved from `done/` to `proposal/` on 2026-06-18 per Jason decision — cloud is deprioritized in current strategy. Local-first is the cost moat. Revisit when team tier validates shared namespace thesis.
