# Post-Change Rule

## Commit timing — code first, test later

Jason's rule: **commit after every main code change, before tests.**

```
Each main code change → commit → [then run tests, self-review, etc.]
```

Rationale: small, focused commits are easier to review, bisect, and revert.

## Full sequence

1. **Run prettier on changed markdown files** — `npx prettier --write <file>` for any `.md` files touched.
2. **Commit main code changes first** — `git add` production code (exclude test files), commit with `[LKPR-N] type: title`. Do not use `--no-verify` unless the hook is wrongly blocking.
3. **Commit test changes** — `git add tests/`, commit with `[LKPR-N] test: ...`.
4. **Mandatory self-review loop** — load `lorekeeper-dev-self-review` skill, run Reflexion cycle (max 3 iterations). PASS requires overall ≥ 8.
5. If FAIL after 3 iterations → surface blockers to Akane/Jason.
6. Push: `git push origin <branch>`
7. Open PR and request reviewer.
8. Ping Jason on Telegram to review and merge.
