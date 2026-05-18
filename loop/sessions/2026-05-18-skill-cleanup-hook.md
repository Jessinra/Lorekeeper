---
date: 2026-05-18
session_id: b74889c9-6f06-4ebd-bd1c-17a85d8b8a56
transcript: /Users/jessin.donnyson/.claude/projects/-Users-jessin-donnyson-Code-Shopee-lorekeeper/b74889c9-6f06-4ebd-bd1c-17a85d8b8a56.jsonl
topic: skill-cleanup-hook
task_type: build
---

## What was done
Explained Mem0's role (embedding store + ANN search via HuggingFace `all-MiniLM-L6-v2`). Explained `.skill` file format (ZIP archive bundling `SKILL.md` + scripts). Added a `Stop` hook to `.claude/settings.json` that auto-deletes `*.skill` files on session exit using `find` with dynamic `git rev-parse --show-toplevel` path.

## Decisions made
- Use `Stop` hook rather than `.gitignore` alone — prevents stale `.skill` files accumulating even locally, not just in commits
- Dynamic path via `git rev-parse --show-toplevel` so hook works for any contributor, not just the original developer

## Corrections / discoveries
- Initially the hook used a hardcoded absolute path; user asked to make it portable — switched to `git rev-parse --show-toplevel`

## Lessons learnt
- **When writing hooks, use dynamic repo-root discovery** → use `git rev-parse --show-toplevel` rather than hardcoding paths, so hooks work for anyone who clones the repo

## Proposed updates
- [ ] CLAUDE.md: none
- [ ] memory: none
- [ ] feedback: store lesson about dynamic paths in hooks
