---
id: LKPR-39
title: Token-based namespace auth (secure namespace control)
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Akane
github_issue: 71
filed_date: 2026-05-27
depends_on: LKPR-38
---

# [LKPR-39] Token-based namespace auth (secure namespace control)

## Problem

LKPR-38 uses a plain `LORE_NAMESPACE` env var for namespace scoping. Anyone who can edit the env var can impersonate any namespace. No security boundary — `LORE_NAMESPACE=bella` gives full access to Bella's memories. Need a proper auth layer, but keep the 1-agent-1-namespace model.

## Solution

Replace the env var with a **token → namespace** mapping stored on a **separate auth server** that agents cannot access directly.

**How it works:**

1. **Auth server** (lightweight, separate from Lorekeeper MCP)
   - Stores: `token → namespace` mapping
   - API: `POST /auth/validate` — takes token, returns namespace (or rejects)
   - Management: `POST /auth/issue` — creates a new token for a namespace
   - Agents never talk to the auth server directly — Lorekeeper does

2. **Lorekeeper server changes:**
   - Agent presents `LORE_TOKEN=<short_secret>` in their MCP config (replaces `LORE_NAMESPACE`)
   - On each MCP call, Lorekeeper validates the token with the auth server and resolves it to a namespace
   - Same auto-scoping as LKPR-38 — insert/search all filtered, agent never touches namespace
   - If token invalid/revoked → auth error on MCP call

3. **Why a separate server:**
   - Agents have MCP tools — if token management was a `lore_*` tool, an agent could call it
   - Separate auth server = agents physically cannot mess with token issuance
   - Clean API boundary: auth is its own concern, manageable by a human (or Diana via a separate channel)

4. **Still 1 agent = 1 namespace.** Multi-namespace comes in ticket 3.

5. **Backward compatibility:**
   - Agents still running `LORE_NAMESPACE` (no token) continue working with LKPR-38 behavior
   - Migration path: issue a token → swap env var → rollout gradually

## Acceptance Criteria

- [ ] Auth server exists (FastAPI / standalone process, port configurable)
- [ ] `POST /auth/validate(token)` returns namespace or 401
- [ ] `POST /auth/issue(name, namespace)` creates and returns a secure token
- [ ] `POST /auth/revoke(token)` invalidates a token
- [ ] Lorekeeper calls auth server on each MCP call to validate token
- [ ] Invalid/revoked tokens get clear auth error on MCP call
- [ ] `LORE_TOKEN` env var replaces `LORE_NAMESPACE` when set
- [ ] `LORE_NAMESPACE` still works as fallback (no token = env var mode)
- [ ] `setup.sh` updated to auto-issue tokens per profile
- [ ] Auth server has its own config (port, token length, persistence)
- [ ] Auth server logs: token issuance, auth failures

## Affected Files

- `auth_server/` — new directory (separate from Lorekeeper main app)
  - `auth_server/main.py` — FastAPI app
  - `auth_server/store.py` — SQLite token store (hashed)
  - `auth_server/config.py` — port, token length
- `src/lorekeeper/config.py` — `LORE_TOKEN`, `AUTH_SERVER_URL`
- `src/lorekeeper/services/orchestrator.py` — validate token on each call
- `src/lorekeeper/services/memory_engine.py` — use resolved namespace
- `scripts/setup.sh` — issue token → inject `LORE_TOKEN`

## Dependencies

LKPR-38 (the namespace auto-scoping plumbing must exist first)

## Open Questions

- Should token validation be cached (TTL cache on Lorekeeper side) to avoid auth server latency on every call?
  - Proposal: yes, 5-min TTL cache. If auth server is unreachable, reject calls (fail closed).
- What format for the token? (Short string, e.g. `diana_xk7m9q` — human-readable prefix + random suffix)
- Auth server port config — fixed or env config?

## Notes

The separate auth server is intentional — agents have MCP tools. If auth management was a `lore_*` tool, a compromised/hallucinating agent could issue itself tokens. A separate process with a bare API (no MCP) keeps the security boundary clean.

## Required Updates

- **CLAUDE.md**: [ ] document auth server + token setup
- **README.md**: [ ] auth server deployment docs
- **Skills**: [ ] update setup skill for token flow
- **Backlog**: [ ] N/A