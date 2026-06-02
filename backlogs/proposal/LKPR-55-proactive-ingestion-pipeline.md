---
id: LKPR-55
title: Proactive ingestion pipeline — auto-fetch from connected sources
type: research # feature | bug | enhancement | research | chore
status: S:proposal # S:proposal | S:ready | S:in-progress | S:review | S:done | S:deferred | S:cancelled
priority: P3:low # P0:critical | P1:high | P2:medium | P3:low
sprint: deferred # 1 | 2 | 3 | unplanned | deferred
rice_score: ~ # XX.X  (R:X I:X C:XX% E:Xw)  — omit if not scored
filed_by: Akane # Jason | Akane | Diana
filed_date: 2026-06-02
---

# [LKPR-55] Proactive ingestion pipeline — auto-fetch from connected sources

## Problem

Lorekeeper is purely passive: facts only get saved when explicitly told. OpenHuman (tinyhumansai/openhuman — 30.3k GitHub stars) has a "Memory Tree" pipeline that proactively ingests from connected sources (email, docs, chats) on a 20-min loop, canonicalizes to Markdown, chunks, scores entities, and builds hierarchical summary trees. This means their agent has context about your world without being fed — ours starts cold every time unless prompted.

Our north star ("thin and easy plug-and-play") intentionally avoids this complexity. But if we ever want Lorekeeper to discover context without being told, this is the path. Filed for future reference.

## Solution

A cron-driven ingestion path that pulls from connected platforms (Telegram history, GitHub issues/PRs, Google Docs) and auto-saves distilled facts into Lorekeeper:

1. **Ingest scheduler** — cron job (reuse existing Hermes cron infra) walks active source connections
2. **Canonicalize layer** — normalize platform-specific data to Markdown with provenance metadata (source, timestamp, URL)
3. **Chunker** — split into bounded segments (≤3k tokens, content-addressed IDs to prevent duplicates)
4. **Fact extractor** — lightweight LLM call to extract salient facts from each chunk
5. **Store** — persist facts via existing `lore_insert` API

OpenHuman uses 3 tree scopes (per-source, per-entity hotness-gated, global daily digest) — overkill for us. Start minimal: just per-source → flat facts.

TokenJuice-style compression (LKPR-56) is a prerequisite — auto-fetch from firehoses like Gmail/Telegram is economically unviable without it.

## Acceptance Criteria

- [ ] Cron job triggers on configured sources at a configurable interval
- [ ] Platform sources yield canonicalized Markdown + provenance metadata
- [ ] Non-duplicate facts are extracted and stored via `lore_insert`
- [ ] All data stays local (no raw data sent to external services beyond LLM calls)

## Affected Files

**Backend:**

- `src/lorekeeper/ingestion/` — new module: scheduler, canonicalize, chunk, extract

**Dashboard (if applicable):**

- Ingestion status page — sources, last sync, fact count

## Dependencies

- LKPR-56: TokenJuice-style compression — needed for economic viability on high-volume sources

## Required Updates

What else needs to change when this ticket ships:

- **CLAUDE.md**: [ ] N/A — update if new module is added
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A — potentially new skill for running ingestion
- **Backlog**: [ ] N/A

## Open Questions

- Is this even aligned with our north star? Jason explicitly said no, filed for future reference only.
- Which sources first? Telegram history seems most immediately available.

## Notes

Inspired by OpenHuman (tinyhumansai/openhuman) Memory Tree pipeline. Their implementation: deterministic chunking with content-addressed IDs, SQLite store, hierarchical summary trees (source/topic/global), background worker queue for embeddings/extraction, auto-fetch every 20 minutes on active integrations. We'd want something far simpler — flat facts from a cron job, no tree hierarchy, no embedding layer prerequisite.

Filed for future reference. Not actionable until/unless strategic direction shifts toward proactive memory discovery.
