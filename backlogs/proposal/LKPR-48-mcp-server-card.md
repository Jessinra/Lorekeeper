---
id: LKPR-48
title: MCP Server Card / Capability Discovery
type: feature
status: S:proposal
priority: P1:high
sprint: unplanned
rice_score: ~
filed_by: Akane
github_issue: 136
filed_date: 2026-05-30
---

# [LKPR-48] MCP Server Card / Capability Discovery

## Problem

Every agent that connects to Lorekeeper needs hardcoded context (skills, prompts, CLAUDE.md entries) to know how to use it properly — what tools exist, what embedding model is used, what search mode is best, how to interpret scores. This is the opposite of zero-config. If you drop Lorekeeper into a new agent's MCP config, that agent should be able to self-configure without a custom skill.

MCP's 2026 roadmap already has "Server Cards" as part of Transport Evolution — the pattern is being defined in working groups now. Being early means Lorekeeper can define the pattern.

## Solution

Expose a standardized MCP resource (e.g., `lorekeeper://capabilities`) that returns a metadata card describing Lorekeeper's capabilities:

- Available tools and their schemas (already available via MCP protocol, but not aggregated with usage context)
- Embedding model & dimension (384, all-MiniLM-L6-v2)
- Vector store backend (Chroma / LanceDB)
- Namespace mode
- Suggested usage patterns ("search before insert", "link related memories")
- Performance hints (batch sizes, latency expectations, recommended query patterns)

The card is a static metadata resource — no new tools or database queries. Pulled from config at startup.

## Acceptance Criteria

- [ ] Server returns a capabilities resource at a well-known path (e.g., `lorekeeper://capabilities` or via MCP `resources/list`)
- [ ] Card includes: tools list, embedding model + dimension, vector store backend, namespace mode
- [ ] Card includes suggested usage hints for agent self-configuration
- [ ] Works with zero config — any MCP client that connects can introspect it
- [ ] Card content is static (derived from config at startup, no runtime DB queries)
- [ ] Dashboard shows the card info (optional — stretch goal)

## Affected Files

**Backend:**

- `src/lorekeeper/server.py` — add `resources/list` handler returning capabilities resource
- `src/lorekeeper/handlers.py` or new `src/lorekeeper/capabilities.py` — build the capabilities dict from config
- `src/lorekeeper/config.py` — expose config values needed for the card (vector store type, embed model, namespace mode)

**Dashboard (if applicable):**

- `dashboard/` — optional: display card info in dashboard footer or settings panel

## Dependencies

_None_ — standalone feature, no blockers.

## Required Updates

- **CLAUDE.md**: [x] N/A — minor, note the new resource
- **README.md**: [ ] Mention the capabilities endpoint in the "Getting Started" section
- **Skills**: [ ] `lorekeeper-dev` — add note that any new config field that affects agent behaviour should be exposed in the card

## Open Questions

- Should the card be a plain JSON resource or should it follow the emerging MCP Server Card spec if that's already defined? (Recommend: start with simple JSON, align to MCP spec once it's stable.)
- Do we want to add a `lore_capabilities` tool, or just the MCP resource? (Resource is cleaner — no tool call needed, any MCP client can introspect via `resources/list`.)

## Notes

Filed from cron output 2026-05-30. Jason rated this "high reward low effort, good job" — moved from prior P2 estimate to P1:high priority. S-effort feature: new resource endpoint, mostly static metadata pulled from config.

Market context: MCP stateless protocol RC means agents connect/disconnect per call — every round-trip counts. Server Cards eliminate meta-config overhead per connection, which compounds as the agent ecosystem scales.
