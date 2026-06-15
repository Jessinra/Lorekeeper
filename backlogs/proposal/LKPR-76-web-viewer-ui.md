---
id: LKPR-76
title: Web viewer UI for browsing and debugging Lorekeeper memory
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-08
github_issue: 170
---

# [LKPR-76] Web viewer UI for browsing and debugging Lorekeeper memory

## Problem

Lorekeeper memory is only accessible through MCP tool calls. There's no way for a human to browse, inspect, or debug what's stored — no way to answer questions like "what does the agent see when it searches my memories?", "is my data clean?", or "what's the most-used memory?". This makes debugging and trust-building harder.

claude-mem has a web viewer UI at localhost:37777 with real-time memory stream, infinite scroll pagination, project filtering, settings panel, and health/stats endpoints. It's used for both debugging and daily inspection.

## Solution

Build a lightweight static web viewer that connects to Lorekeeper's MCP server. Options:

**Option A: FastAPI/Flask dashboard** (recommended)

- Expose a few HTTP endpoints from Lorekeeper's MCP server: `GET /health`, `GET /stats`, `GET /memories?limit=&offset=`
- Serve a static HTML page with search, browse, and detail views
- Minimal JS, no framework — just fetch() + DOM

**Option B: Streamlit dashboard** (fastest to build)

- Streamlit app that calls lore_search and displays results
- Works immediately, minimal code
- But adds Streamlit as a dependency

**Option C: Static HTML + embedded MCP client**

- A pure HTML page that connects to the MCP server via a bridge script
- No backend changes needed
- More complex, less reliable

Recommend Option A (FastAPI) — it's lightweight, the existing server can host the endpoints, and it doesn't add heavy dependencies.

## Minimum Viable Scope

- [ ] Recent memories list (pagination, newest first)
- [ ] Search bar with query input
- [ ] Memory detail view (full content, metadata, links)
- [ ] Health/stats endpoint: total memories, daily insert rate, top-used memories
- [ ] Filter by memory_type (when LKPR-74 is done)
- [ ] Auto-launch on `lorekeeper start`

## Future Enhancements (out of scope for MVP)

- Real-time SSE stream of new memories as they're inserted
- Timeline view (chronological narrative)
- Graph view (memory links visualization)
- Settings panel
- Edit/delete from UI

## Acceptance Criteria

- [ ] `GET /health` returns server status + DB stats
- [ ] Recent memories list loads within 500ms for 1000 memories
- [ ] Search returns results matching `lore_search` behavior
- [ ] Detail view shows full content, metadata, and linked memories
- [ ] Static HTML page served from Lorekeeper's port
- [ ] Does not require authentication (localhost only)
- [ ] Documented at `docs/viewer.md`

## Affected Files

**Backend**: New module `services/viewer.py` or `web/`, new endpoints in `server.py`
**Dashboard**: New static files at `src/lorekeeper/web/`

## Dependencies

- LKPR-74 (type system) — useful for search filters and icon display in UI

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — protocol unchanged
- **README.md**: [ ] Yes — document web viewer URL and usage
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Notes

A web viewer is not just a nice-to-have — it's a debugging and trust tool. Being able to visually inspect what the agent sees helps catch quality issues early and gives users confidence in the system. Priority: P2:medium.
