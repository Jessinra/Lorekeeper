---
id: LKPR-40
title: Organization / team namespaces with multi-namespace RBAC
type: feature
status: S:proposal
priority: P3:low
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-05-27
depends_on: LKPR-39
---

# [LKPR-40] Organization / team namespaces with multi-namespace RBAC

## Problem

LKPR-38/39 enforce 1 agent = 1 namespace. But real setups need an agent to access multiple namespaces — e.g. Diana needs access to `diana`, `shared`, and `team-secure`. Or you want a "read-only observer" agent that can see all namespaces but write to none. Multi-namespace access and team-level organization don't exist.

## Solution

Organization/team concept with per-namespace permissions per agent:

**Organization model:**
- An **organization** (or "team") is a group of agents
- Each agent can have access to **multiple namespaces**
- Each namespace has permissions per agent: `read`, `write`, or both
- e.g. Diana on `diana` → read+write, Diana on `team-secure` → read-only, Diana on `audit` → read-only

**RBAC extension to auth server (from LKPR-39):**

| API | Purpose |
|-----|---------|
| `POST /org/create(name)` | Create an organization |
| `POST /org/invite(org_id, agent_name, namespaces, permissions)` | Add agent with per-namespace perms |
| `POST /org/grant(token, namespace, permissions)` | Modify existing permissions |
| `POST /org/revoke(token, namespace)` | Remove namespace access |

**Enforcement at query time:**
- `lore_search` — checks token has `read` permission on each requested namespace
- `lore_insert` / `lore_remember` — checks token has `write` on target namespace
- Permissions checked against auth server on each call (or cached, same as LKPR-39)
- Agent can now set `namespace` on insert/search (no longer invisible) — but only to namespaces they have access to
- Rejected calls return clear permission error

**Still no MCP tools for auth management.** The auth server API is the only way to manage permissions. Agents cannot call it.

## Acceptance Criteria

- [ ] Organization concept: `POST /org/create`, `POST /org/invite`
- [ ] Multi-namespace per agent: token resolves to `{namespace: [read/write], ...}`
- [ ] `lore_search` accepts `namespace` param (agent-controlled now)
- [ ] `lore_search` enforces read permission per namespace
- [ ] `lore_insert` / `lore_remember` enforce write permission
- [ ] `lore_search(namespaces=["diana", "shared"])` returns union filtered by perms
- [ ] `lore_insert(namespace="shared")` on read-only → error
- [ ] Fallback: no permission set for a namespace = denied (default deny)
- [ ] Auth server persists org, agent-namespace mapping, permissions
- [ ] Agent's default namespace (from token) still used when no explicit param given

## Affected Files

- `auth_server/` — extend with org/permissions tables
  - `auth_server/models.py` — org, agent-namespace mappings
  - `auth_server/store.py` — permissions SQLite tables
  - `auth_server/main.py` — new endpoints
- `src/lorekeeper/services/orchestrator.py` — multi-namespace resolution, permission check
- `src/lorekeeper/services/memory_engine.py` — namespace param on insert
- `src/lorekeeper/services/search.py` — per-namespace permission filter

## Dependencies

LKPR-39 (auth server must exist first)

## Open Questions

- Default namespace on insert when agent controls multiple namespaces? (Use token's primary namespace, or require explicit param)
- Should `lore_update` / `lore_reflect` also be permission-checked? (Yes — write operations need write perms)
- What about shared-within-org namespaces vs global shared? (Org-level `shared` that only org members see)

## Notes

**This ticket is deliberately P3.** LKPR-38 + LKPR-39 cover the real production needs. Build this only when someone actually asks "Can I have an agent that reads both project A and project B but only writes to A?" The schema design should leave enough room (the `namespace` column on memories is already TEXT — flexible for future multi-org) so this doesn't require a re-migration.

Key design constraint: the auth server should not need to be rewritten. LKPR-39's auth server schema should already support multiple namespace-per-token even if LKPR-39 doesn't use it. Future-proofing matters here.

## Required Updates

- **CLAUDE.md**: [ ] document org/RBAC when built
- **README.md**: [ ] document when built
- **Skills**: [ ] N/A until built
- **Backlog**: [ ] N/A