---
name: commit-convention
description: Git commit convention for Lorekeeper — enforced by commit-msg hook. Covers author identity, ticket tags, and message format for both PM (Akane) and Dev roles.
version: v1.0.0
tags: [git, commit, convention, lorekeeper]
related_skills: [lorekeeper-dev, lorekeeper-pm, backlog-management]
---

# Commit Convention

All commits to the Lorekeeper repo are enforced by `.git/hooks/commit-msg` (installed via `scripts/lorekeeper-setup.sh`).

---

## Author Identity

| Role             | `user.name`  | `user.email`             |
| ---------------- | ------------ | ------------------------ |
| PM (Akane)       | `Akane (PM)` | `jessinra.kai@gmail.com` |
| Dev              | `Dev`        | `jessinra.kai@gmail.com` |
| Engineer (Diana) | `Diana`      | `jessinra.kai@gmail.com` |

Set locally in the repo (not globally, to avoid polluting other projects):

```bash
# PM
git config --local user.name "Akane (PM)"
git config --local user.email "jessinra.kai@gmail.com"

# Dev
git config --local user.name "Dev"
git config --local user.email "jessinra.kai@gmail.com"

# Diana
git config --local user.name "Diana"
git config --local user.email "jessinra.kai@gmail.com"
```

---

## Commit Title Format

```
[LKPR-N] type: short imperative title
```

### Ticket Tags

| Tag        | When to use                                                                                                     |
| ---------- | --------------------------------------------------------------------------------------------------------------- |
| `[LKPR-N]` | Work tied to a specific ticket (feature, fix, refactor, test)                                                   |
| `[LKPR-0]` | Housekeeping with no ticket — chore, backlog edits, moving tickets, changing status, updating skills, docs-only |

### Types

`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

---

## Examples

```
[LKPR-6] feat: add iterative search with relevance cutoff
[LKPR-19] fix: enable FK constraints via PRAGMA foreign_keys=ON
[LKPR-0] chore: add LKPR-21 entity-resolution backlog ticket
[LKPR-0] docs: update README scoring formula
[LKPR-0] chore: move LKPR-15 to done/
```

---

## Merge Commits

Merge commits (branch → main) are **exempt** from the hook — detected by the presence of `MERGE_HEAD` or a title starting with `Merge branch`.

---

## Bypassing (emergency only)

Do not bypass. No excuse.

---

## Installing / Reinstalling the Hook

The hook lives at `scripts/hooks/commit-msg` and is installed by setup:

```bash
./scripts/setup.sh
```

Re-run this after cloning the repo on a new machine.
