---
id: LKPR-87
title: Deployment starter kit — Docker Compose + team pilot deployment guide
type: enhancement
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-06-11
depends_on: LKPR-38
github_issue: 198
---

# [LKPR-87] Deployment starter kit — Docker Compose + team pilot deployment guide

## Problem

Two blockers for team pilot:

1. **Local-first is the wrong bet for team tier.** Teams want a shared server they all point at, not self-hosted everything-on-my-laptop. The risk analysis flagged this: most teams will reject operational burden for a shared memory store. Without a cheap deployment path, the team pilot can't start.

2. **LKPR-38 (namespace env var) and LKPR-39 (token auth) are proposals only.** Even when shipped, there's no guide for non-ops-happy teams to set up a shared Lorekeeper instance. The gap between "pip install" and "team-served instance" kills adoption before it starts.

## Solution

A **deployment starter kit** — not a managed service, not a cloud offering. Just enough to unblock a 2-team pilot:

**Deliverable 1: Docker Compose file (`deploy/docker-compose.yml`)**

- Single `docker compose up` brings up: Lorekeeper MCP server, SQLite volume, LanceDB vector store volume, Caddy reverse proxy with optional TLS (Let's Encrypt auto-cert)
- Health check endpoint at `/health`
- `LORE_TOKEN` passed from `.env` file, one-liner to configure
- Target: one cheap VPS ($10-20/mo on any provider)

**Deliverable 2: Deployment guide (`docs/deploy.md`)**

- Three paths: local laptop (for testing), $10 VPS (for team pilot), LAN server (for office)
- Step-by-step: create VPS, `docker compose up -d`, set DNS, configure TLS, distribute tokens to team
- Troubleshooting: most common failures (port conflicts, permissions, DNS propagation)
- <200 lines of markdown. Table of contents, terminal commands only, no fluff.

**Explicitly NOT in scope:** Managed hosting, SOC2, multi-region, backups-as-a-service, monitoring, admin panels. Those are LKPR-34 (cloud lorekeeper) scope.

## Acceptance Criteria

- [ ] `docker-compose.yml` exists and `docker compose up` starts Lorekeeper with token auth
- [ ] Two agents on two different machines can connect to the same Lorekeeper instance with different tokens and get namespace isolation (depends on LKPR-38/39)
- [ ] `docs/deploy.md` covers all three deployment paths
- [ ] The kit is tested on a fresh $10 VPS (any provider)
- [ ] Total setup time for a new team: <15 minutes

## Affected Files

**New:**

- `deploy/docker-compose.yml`
- `deploy/.env.example`
- `deploy/Caddyfile`
- `docs/deploy.md`

**Modified:**

- `README.md` — add "Team deployment" section linking to `docs/deploy.md`

## Dependencies

- LKPR-38: token-based namespace isolation (env var or token → namespace scoping). Without namespace isolation, Docker Compose is just a shared store with no multi-agent safety.

## Required Updates

- **CLAUDE.md**: [ ] add deploy/docker-compose.yml and docs/deploy.md to project map
- **README.md**: [ ] add "Team deployment → docs/deploy.md" section after install
- **Skills**: [ ] N/A
- **Backlog**: [ ] When shipped, unblocks team pilot. If pilot validates shared namespace thesis, promote LKPR-34 (cloud lorekeeper) from proposal to backlog.
