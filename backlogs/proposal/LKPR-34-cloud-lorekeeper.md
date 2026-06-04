---
id: LKPR-34
title: Cloud Lorekeeper — shared memory across agent machines
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
github_issue: 67
filed_date: 2026-05-27
---

# [LKPR-34] Cloud Lorekeeper — shared memory across agent machines

## Problem

Multiple Hermes personas on separate machines each have their own isolated Lorekeeper DB. No shared space means no cross-agent awareness — Agent A can't surface a finding to Agent B unless the human relays it manually.

## Solution

Lightweight hosted Lorekeeper that agents explicitly push/pull from. Add a `source` field to identify which agent wrote what. Keep local DBs fully private. Implementation details (hosting, transport, auth) deferred until there's a concrete trigger — e.g. dev persona hits a moment of "I wish I could show Akane this".

## Acceptance Criteria

- [ ] Cloud Lorekeeper exists and can be deployed (Docker / simple server)
- [ ] `source` field on memories, filterable on search
- [ ] Agents explicitly push/pull — no auto-sync

## Required Updates

- **CLAUDE.md**: [ ] add `source` field docs
- **README.md**: [ ] cloud deployment instructions
- **Skills**: [ ] N/A
- **Backlog**: [x] Remove proposal note
