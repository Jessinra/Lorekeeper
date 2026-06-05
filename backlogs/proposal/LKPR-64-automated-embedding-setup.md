---
id: LKPR-64
title: Automated model embedding installation in setup.sh
type: research
sprint: ~
rice_score: ~
filed_by: ~
filed_date: 2026-06-05
---

# [LKPR-64] Automated model embedding installation in setup.sh

## Problem

Every agent/workspace that wants to adopt Lorekeeper needs Chroma or LanceDB + a 384-dim embedding model (`all-MiniLM-L6-v2`). Installing these ML dependencies is a manual step that adds friction to first-time setup — the model has to be downloaded, the vector store configured, and the user must remember to do it.

**Status: Pain point is NOT confirmed.** This was filed from a brainstorm — we don't yet know if this is a real blocker for users. The hypothesis is that embedding model download should be fully automated in `setup.sh`, transparent to the user.

## Solution

Investigate and prototype integrating the embedding model download/install into `scripts/setup.sh` so that:

- Model is auto-downloaded during setup (if user opts into vector features)
- No manual pip install or model download step needed
- User never has to think about the embedding model

## Acceptance Criteria

- [ ] Research completed: confirm whether automated embedding install is a real pain point or not
- [ ] If validated: prototype the automation in setup.sh
- [ ] Document findings in this ticket

## Affected Files

**Backend:**

- `scripts/setup.sh` — potential changes
- Possibly `pyproject.toml` — if dependencies change

**Dashboard (if applicable):**

- `_none_`

## Dependencies

_None_

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — update if setup flow changes
- **README.md**: [ ] N/A — update if setup flow changes
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Open Questions

1. Is manual embedding model install an actual friction point for current users?
2. How many users currently hit this during setup?
3. What's the simplest way to auto-download the model? (huggingface_hub CLI? pip extras?)

## Notes

Filed from lorekeeper-daily-ideas (2026-06-05). Original idea suggested a BM25-only mode (`LORE_VECTOR_STORE=none`) — but Jason noted the pain point isn't confirmed. The real problem may just be that setup.sh should handle the model download automatically. Set to P3 — revisit if evidence emerges.