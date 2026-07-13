# Pre-Push Self-Review Checklist

Before opening a PR, run through this:

**Correctness**

- [ ] All acceptance criteria met?
- [ ] Edge cases handled? (null inputs, empty results, missing metadata)
- [ ] Tested manually end-to-end at least once?

**Tests**

- [ ] New logic has tests?
- [ ] Bug fix has a regression test?
- [ ] Full suite passes: `uv run pytest`?

**Code Quality**

- [ ] No debug prints / `breakpoint()` left in
- [ ] No dead code or commented-out blocks
- [ ] Linter clean: `uv run ruff check src tests`

**Documentation**

- [ ] README updated if behavior/config changed?
- [ ] Complex logic has inline comments explaining _why_?

**Git**

- [ ] Commits follow `[LKPR-N] type: title` format?
- [ ] Branch named `<type>/LKPR-N-slug`?
- [ ] Ticket updated: `status: review`, `resolved_date`, root cause written?
- [ ] Pre-PR self-review pass completed:
  - [ ] Cross-cutting features: enumerated ALL data-access paths?
  - [ ] Config/script injections: escaped all injected values?
  - [ ] Frontend stateful UI: state invalidation handled?
  - [ ] Docs written AFTER code is final?
  - [ ] No partial fixes — if Jason commented on area X before, is X fully resolved?
  - [ ] Any `subprocess` with `timeout=N`? → wrapped in `try/except TimeoutExpired`
  - [ ] Any `pytest` hook? → correct signature from pytest docs?
  - [ ] Any E2E tests added? → run locally before pushing
- [ ] Pushed to origin and PR opened?
- [ ] Jason pinged on Telegram to review and merge?
