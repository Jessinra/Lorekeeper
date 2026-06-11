---
id: LKPR-0
title: 100X code review pipeline — Lorekeeper edition
type: chore
sprint: unplanned
rice_score: ~ # housekeeping, not scored
filed_by: Diana
filed_date: 2026-06-11
github_issue: 187
---

# [LKPR-0] 100X code review pipeline — Lorekeeper edition

## Problem

The existing code review setup in Lorekeeper has two weak points:

1. **Generic Copilot instructions** — `copilot-instructions.md` says "review for security and correctness" with no Lorekeeper-specific constraints. Copilot doesn't know that `print()` in runtime code corrupts the MCP protocol, that `mem0.add()` needs `infer=False`, or that scoring changes are high-risk. It gives the same feedback it would for any Python project.

2. **No PR size enforcement** — there's no guard against oversized PRs. A 1000-line diff gets the same process as a 50-line diff. Research shows review quality collapses above 400 lines (~1.8 meaningful comments vs. ~6 for small PRs).

3. **No severity tiers in review feedback** — feedback is free-form prose. There's no shared vocabulary for "this MUST be fixed before merge" vs. "this is a style preference."

## Solution

Apply the 100X code review pipeline built for backend projects, adapted with Lorekeeper-specific constraints:

- **Upgraded `copilot-instructions.md`** with severity tiers (BLOCKER/MAJOR/MINOR/NIT), Conventional Comments format, and Lorekeeper architecture constraints as explicit BLOCKER patterns.
- **Upgraded `PULL_REQUEST_TEMPLATE.md`** with explicit merge contract, BLOCKER pre-submit checklist, and high-risk change section.
- **New `scripts/pr-size-check.sh`** — enforces PR size: warn at 200, amber at 400, hard-fail at 600. `[large-pr]` override for justified exceptions.
- **New `docs/code-review-guide.md`** — full reference: 100X prompt adapted to Lorekeeper, Conventional Comments guide, BLOCKER pattern code examples, human reviewer focus areas.
- **CI integration** — PR size check wired into `ci.yml` as a required step on every PR.

## Acceptance Criteria

- [ ] `copilot-instructions.md` has severity tiers (BLOCKER/MAJOR/MINOR/NIT) and all Lorekeeper architecture constraints explicitly listed
- [ ] `PULL_REQUEST_TEMPLATE.md` has merge contract and BLOCKER pre-submit checklist
- [ ] `scripts/pr-size-check.sh` exists, is executable, and exits 1 for PRs >600 lines unless `[large-pr]` override present
- [ ] CI `lint-and-test` job includes PR size check step that runs on `pull_request` events
- [ ] `docs/code-review-guide.md` exists with 100X AI prompt, Conventional Comments reference, and Lorekeeper BLOCKER code examples

## Required Updates

- **CLAUDE.md**: [x] N/A — no behavioral changes to development workflow
- **README.md**: [x] N/A — this is internal tooling, not user-facing
- **Skills**: [x] N/A — `code-review-pipeline` skill in Diana's profile already has the generic version; this PR adapts it to Lorekeeper
- **Backlog**: [ ] N/A — no dependency changes

## Notes

This is a housekeeping PR (LKPR-0) filed as part of the broader 100X code review pipeline
initiative. The generic pipeline skill lives at:
`~/.hermes/profiles/diana/skills/software-development/code-review-pipeline/`

The Lorekeeper-specific adaptations are the key delta:

- `print()` in runtime → MCP protocol corruption (project-specific BLOCKER)
- `mem0.add()` without `infer=False` → silent LLM call (project-specific BLOCKER)
- `lore_id` vs Mem0 internal id confusion (project-specific BLOCKER)
- Migration idempotency rules (project-specific constraint)
- Scoring/dedup changes as high-risk category (project-specific)

The AI prompt in `docs/code-review-guide.md` can be used directly as a Hermes agent
delegation goal for independent code review, with `{GIT_DIFF_OUTPUT}` replaced by the
actual diff.
