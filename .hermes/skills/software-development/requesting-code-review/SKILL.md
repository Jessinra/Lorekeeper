---
name: requesting-code-review
description: "Pre-commit review: security scan, quality gates, auto-fix."
version: v2.0.0
author: Hermes Agent (adapted from obra/superpowers + MorAlekss)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, security, verification, quality, pre-commit, auto-fix]
    related_skills:
      [subagent-driven-development, writing-plans, test-driven-development, github-code-review]
---

# Pre-Commit Code Verification

Automated verification pipeline before code lands. Static scans, baseline-aware quality gates, an independent reviewer subagent, and an auto-fix loop.

**Core principle:** No agent should verify its own work. Fresh context finds what you miss.

## When to Use

- After implementing a feature or bug fix, before `git commit` or `git push`
- When user says "commit", "push", "ship", "done", "verify", or "review before merge"
- After completing a task with 2+ file edits in a git repo
- After each task in subagent-driven-development

**Skip for:** documentation-only changes, pure config tweaks, or when user says "skip verification".

**This skill vs github-code-review:** This skill verifies YOUR changes before committing. `github-code-review` reviews OTHER people's PRs on GitHub.

## Step 1 — Get the diff

```bash
git diff --cached
```

If empty, try `git diff` then `git diff HEAD~1 HEAD`. If still empty, run `git status`.

If the diff exceeds 15,000 characters, split by file:

```bash
git diff --name-only
git diff HEAD -- specific_file.py
```

## Step 2 — Static security scan

See `references/scan-and-patterns.md` for the full scan commands (hardcoded secrets, shell injection, eval/exec, unsafe deserialization, SQL injection).

## Step 3 — Baseline tests and linting

See `references/scan-and-patterns.md` for test framework detection and linting commands (Python, Node, Rust, Go).

Baseline comparison: stash changes, run baseline, pop. Only NEW failures introduced by your changes block the commit.

## Step 4 — Self-review checklist

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation on user-provided data
- [ ] SQL queries use parameterized statements
- [ ] File operations validate paths (no traversal)
- [ ] External calls have error handling (try/catch)
- [ ] No debug print/console.log left behind
- [ ] No commented-out code
- [ ] New code has tests (if test suite exists)

### Lorekeeper pre-flight (run before `gh pr create`)

- [ ] **Hardcoded numeric limits** — any `len(x) > 200` or similar? Move to `Settings` with `LORE_*` env var.
- [ ] **Parameter forwarding** — trace every new param through all code paths.
- [ ] **N+1 transaction loops** — any `for item in items: store.update_something(item.id, ...)` with per-call `commit()`? Replace with bulk SQL.
- [ ] **Doc/code field name consistency** — do docs use exact field names (`id` vs `lore_id`)?
- [ ] **Configurable defaults in docs** — must say `(configurable, default N via LORE_X)`.
- [ ] **Test dead code** — any `links=[{...None IDs...}]` passed to `svc.insert()`? Remove it.
- [ ] **Git author** — `git config --local user.name` = correct agent identity.
- [ ] **Branch base** — `git log --oneline origin/main..HEAD` shows only this PR's commits.

## Step 5 — Independent reviewer subagent

See `references/delegate-patterns.md` for the full delegate_task code. The reviewer gets ONLY the diff and static scan results. Fail-closed: unparseable response = fail.

## Step 6 — Evaluate results

**All passed:** Proceed to Step 8 (commit).

**Any failures:** Report what failed, then proceed to Step 7 (auto-fix).

```
VERIFICATION FAILED
Security issues: [list]
Logic errors: [list]
Regressions: [new test failures vs baseline]
New lint errors: [details]
Suggestions: [list]
```

## Step 7 — Auto-fix loop

**Maximum 2 fix-and-reverify cycles.** See `references/delegate-patterns.md` for the fix agent delegate_task code.

- Passed: proceed to Step 8
- Failed and attempts < 2: repeat Step 7
- Failed after 2 attempts: escalate to user

## Step 8 — Commit

```bash
git add -A && git commit -m "[verified] <description>"
```

The `[verified]` prefix indicates an independent reviewer approved this change.

## Integration with Other Skills

- **subagent-driven-development:** Run after EACH task as the quality gate.
- **test-driven-development:** Verifies TDD discipline was followed.
- **writing-plans:** Validates implementation matches plan requirements.

## Pitfalls

- **Empty diff** — check `git status`, tell user nothing to verify
- **Not a git repo** — skip and tell user
- **Large diff (>15k chars)** — split by file, review each separately
- **delegate_task returns non-JSON** — retry once, then treat as FAIL
- **False positives** — if reviewer flags something intentional, note it in fix prompt
- **No test framework found** — skip regression check, reviewer verdict still runs
- **Lint tools not installed** — skip that check silently
- **Auto-fix introduces new issues** — counts as a new failure, cycle continues
