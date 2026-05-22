---
id: LKPR-15
title: Research — Dockerize Hermes for cloud hosting + multi-agent
type: research
status: deferred
priority: low
sprint: deferred
filed_by: Hermes (Jason's note)
filed_date: 2026-05-22
---

# [LKPR-15] Research — Dockerize Hermes for cloud hosting + multi-agent

## Idea

Explore running Hermes inside Docker so it can live in cloud infra permanently — independent of any local machine. One host machine could then run multiple agent personas as separate containers.

## Motivation

- Agent currently tied to Jason's Mac — goes offline when machine sleeps/restarts
- Multi-persona setup (personal assistant + Lorekeeper PM bot) is cleaner as separate containers than separate local profiles
- Cloud hosting = always-on Telegram bots with no local dependency

## Things to Explore

- Volume mounts for persistent memory, sessions, skills (`~/.hermes` equivalent)
- Shared vs isolated Lorekeeper MCP per container (relates to LKPR-10 namespace isolation)
- `docker-compose` setup for multi-agent (one service per profile/bot)
- Resource limits per container
- Auth: OAuth tokens, API keys — how to inject securely (secrets management)
- Gateway persistence across container restarts

## Dependencies

- LKPR-10 (namespace isolation) — worth solving before running multiple agents against same Lorekeeper instance
- Hermes Docker support (check if official image exists: `hermes-agent.nousresearch.com/docs`)

## Notes

Not urgent. Worth researching when setting up multi-persona Telegram bots. Low effort to prototype locally with docker-compose first.
