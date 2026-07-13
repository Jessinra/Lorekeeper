---
name: lorekeeper-code-reviewer
description: "Lorekeeper-specific BLOCKER patterns, severity tiers, and review checklist — used when reviewing any PR touching src/lorekeeper/"
version: 1.20.0
author: Diana
---

# Lorekeeper Code Review Patterns

Use this skill when reviewing any PR that changes `src/lorekeeper/` runtime code, services, handlers, or MCP server. These are project-specific patterns that general-purpose review prompts miss.

**Incident-driven:** BLOCKER patterns 16-19 added after P0 Incident 2026-06-21 (Lorekeeper SQLite lock contention + infinite retry storm). See `docs/incidents/IR-002-lorekeeper-sqlite-lock-contention.md`. Patterns 20-24 added after LKPR-100 (server wiring, metrics, partial commits) and LKPR-67 (type migration, backup compatibility).

Load alongside `github-code-review` for a complete review session.

## Severity Tiers

Every review comment **must** carry a severity label.

| Label         | Tier       | Merge impact                      |
| ------------- | ---------- | --------------------------------- |
| `blocker:`    | 🔴 BLOCKER | **Must fix before merge**         |
| `issue:`      | 🟠 MAJOR   | Fix before merge or create ticket |
| `suggestion:` | 🟡 MINOR   | Fix encouraged, deferrable        |
| `nit:`        | 🔵 NIT     | Optional, never blocks            |
| `praise:`     | ✅         | Acknowledge good work             |

**Merge contract:** PR is mergeable when all BLOCKERs resolved, all MAJORs resolved OR tracked, CI green, ≥1 human approval.

## How to Use This Skill

1. **Holistic review** — Before checking the diff, read every changed file in full, read adjacent files, and read the ticket/plan. Load `references/holistic-review.md` for the full framework.
2. **Pre-check** — `git diff main...HEAD --name-only | grep -q "^src/lorekeeper/"` → RUNTIME or NON-CODE
3. **Deleted-file check** — `git diff main --name-status --diff-filter=D | grep -q "^D"` — any deleted test file is BLOCKER unless replaced.
4. **API divergence check** — compare MCP tool signatures in `server.py` against the ticket ACs. Also scan the ticket's Required Updates section for checklist items.
5. **RUNTIME PR** → load `references/blocker-patterns.md` for the 24 BLOCKER patterns
6. **NON-CODE PR** → load `references/non-code-pr-checklist.md`
7. **All PRs** → check Maintainability (`references/maintainability-simplicity.md`)
8. **Migration PRs** → check Backward Compatibility (`references/backward-compatibility.md`)
9. **README / user-facing docs** — spot-check for duplicate sections, stale dates, merge artifacts
10. **Pre-merge** → run `references/pre-deployment-checklist.md`

## 🟠 MAJOR & BLOCKER: Key Patterns

### Architecture & Holistic Fit (BLOCKER if wrong)

- **Read every changed file in full**, not just the diff. Read adjacent files (server.py wiring, caller modules).
- **Does it belong here?** — is the code placed in the correct architectural layer? A new method on a god class that could be a standalone module is a BLOCKER.
- **Is it the simplest version?** — premature abstraction (configurable weights never tuned, ABCs with one subclass) is complexity debt.
- **Read the ticket/plan** — does the implementation match the ticket description?
- **Trace every constructor parameter** — unused `self.X = x` parameter is dead code.

### BLOCKER — Test file deleted with no replacement

Run `git diff main --name-only --diff-filter=D | grep "tests/"`. Any deleted test file is a presumptive BLOCKER. Deleted count >> replacement count = BLOCKER.

### Correctness & Performance

- Missing `None` checks before attribute access on Optional values
- Multi-step DB writes not wrapped in a transaction
- N+1 queries / unbounded `.all()` without pagination
- Non-atomic write ordering (vector-store operation before DB commit)
- Logging authoring data on error paths (exposes factual discoveries in stderr)
- Transaction boundary in route/handler layer instead of domain services

### Deferred imports inside loops

Any `from X import Y` inside a `for` loop body is a smell. Move to module-level.

### Facade delegation methods must preserve exact type signatures

When a refactoring PR extracts logic into domain services and leaves an orchestrator facade that delegates via `*args: Any, **kwargs: Any`, this destroys mypy/introspection coverage and risks MCP schema drift. Mirror the exact signature.

### Migration idempotency — safe to run twice

Every migration script must be idempotent: running it twice produces the same result as running it once.

### Dashboard V2 (Svelte 5) — Hardcoded Value Check

For `src/dashboard_v2/` changes, extract a value into `primitives.ts` or `@theme` only when shared across 2+ components, a consistency anchor, or configurable at runtime.

### Evaluating a New / Unfamiliar Reviewer Tool

When a new reviewer is added to an already-active PR with multiple fix commits, assess its output before acting. The key signal: a reviewer without visibility into prior fix commits will surface many stale comments. Tally signal/noise — if ≥50% are stale, scan once but don't gate on it.

## 🔵 NIT — Never Block

- Import order, line length → ruff
- Type errors → mypy (CI)
- Coverage → pytest-cov (CI)
- Markdown formatting → prettier (CI)

## Lorekeeper Architecture: MemoryService vs SweepService Boundary

`MemoryService` (orchestrator) owns user-facing MCP operations. `SweepService` owns background batch operations. `LinkSuggestionStore` belongs on `SweepService`, not `MemoryService`.

## Repo-Specific Red Flags

- Any `print(` in `src/lorekeeper/` not inside a CLI tool
- `mem0.add(...)` without `infer=False`
- Direct `conn.execute()` in handler or server code
- Changes to `MIGRATIONS[0]`
- Importing from `dashboard/` in server code (wrong dep direction)
- Adding `import requests` to `server.py` — use `httpx` async
- Gitlink entry (mode 160000) without `.gitmodules`
- Passing `MemoryService` where a specific store type is expected
- Background thread performing writes on same DB connection as main thread
- Background process writing to same `.db` file as MCP server — split DBs
- Module-level variable assignment inside `init_*()` without `global` declaration
- Batch handler with per-item try/except and single post-loop commit (partial writes persist)
- Backup/dump restore path that doesn't normalize legacy data types

## Review Style Rules

- Reference exact file:line (`server.py:112`)
- Show the fix, not just the problem
- Bullet points, not paragraphs
- **Comment only on the diff** — don't flag pre-existing issues
- Use `praise:` when something is done well
- Verify local file state before reviewing

## Related Skills

- **[lorekeeper-qa-verification]** — Pre-deployment QA
- **[github-code-review]** — General code review process
- **[requesting-code-review]** — Pre-commit quality gates
- **[lorekeeper-dev]** — Engineering workflows and pitfalls
