# PR #237 (LKPR-99) Review Patterns — Link Suggestion Sweep Engine

## What was reviewed

A periodic sweep engine (LKPR-99) that iterates all active memories, runs the existing `LinkCandidateGenerator` scorers, and records candidates to a new `link_suggestions` DB table. Added `SweepService`, `LinkSuggestionStore`, `PeriodicJob`, database migration v5, standalone entrypoint, and 4 env vars.

## BLOCKER findings

### Script calls non-existent method on orchestrator

`scripts/sweep-links.py:90` called `svc.sweep_links()` but that method was **never defined** on `MemoryService`. The sweep algorithm lived in `SweepService.run()`. The non-dry-run path crashed with `AttributeError`.

**Root cause:** The PR description, plan doc, and a previous pass all claimed `MemoryService.sweep_links()` existed. The actual implementation correctly used a standalone `SweepService` — but the script and docs were never updated to match.

**Fix:** Rewrote the script to build `SweepService` directly from stores (MemoryStore, LinkStore, LinkCandidateGenerator), calling `sweeper.run()`.

**Prevention pattern:** Before shipping a standalone script, run both its dry-run and non-dry-run paths against a temp database. Add a subprocess regression test (see `tests/test_pr237_review_fixes.py::test_sweep_links_script_dry_run`).

## MAJOR findings

### Dead store on orchestrator (unused instance attribute)

`MemoryService.__init__` created `self.suggestions = LinkSuggestionStore(db)` — but no method on `MemoryService` ever read it. The sole consumer was `SweepService`, which created its own instance in `server.py`.

This forced adding `db: Database` as a constructor parameter to `MemoryService` — the only purpose was creating a store nobody used.

**Fix:** Removed `db` param and `self.suggestions` from `MemoryService`. `LinkSuggestionStore` is created only in `server.py` alongside `SweepService`.

**Detection pattern:** For each new `self.X = ...` in `__init__`, cross-reference against ALL method bodies. ruff does NOT flag unused instance attributes.

### PR description drifted from actual implementation

The PR body claimed:

- `MemoryService.sweep_links()` was a change (doesn't exist)
- `SweepScheduler` subclass existed (there's only `PeriodicJob`)
- Test section referenced `sweep_links()` instead of `SweepService.run()`

**Fix:** Updated PR body via REST API to match actual implementation.

**Detection pattern:** For every method/class named in the PR description's "Changes" section, grep the actual diff for its definition. If it doesn't exist in the code, the description is stale.

### README had duplicate Performance sections and broken layout

The first "## Performance" section was a stale placeholder ("benchmarks coming soon") with early internal numbers. A second "## Performance" section later had actual LongMemEval-S results. The "Project Layout" tree was split in two by an orphaned "Configuration" section — the `services/` directory had no entries, then after the config table, a second code block showed orphaned service files under no parent. The env var table only listed the 4 new internal sweep vars (`LORE_SUGGEST_*`), not the variables a user actually needs (`LORE_DATA_DIR`, `LORE_NAMESPACE`, `LORE_SEARCH_LIMIT`).

**Fix:** Removed stale placeholder, consolidated layout into a single "For Developers" section, replaced sweep vars with user-relevant env vars.

## MINOR findings

### CLAUDE.md store count wrong

"The SQLite layer is split into a shared Database class and five focused stores" — but the table showed 6 focused stores (now 7 with LinkSuggestionStore). Fixed to "six focused stores."

### Stale "Last verified" date

README.md footer said "Last verified: 2026-06-16" — was now 4 days stale.

## Lessons for future reviews

1. **Script smoke tests**: Any PR adding/modifying a `scripts/` entrypoint should have a subprocess regression test that runs it against a temp database.
2. **PR description cross-check**: Before declaring a PR ready, grep the diff for every method/class named in the description. Stale text = incomplete review.
3. **Constructor dead-weight**: New instance attributes on `__init__` that are never read by any method are invisible to all automated tools. Always cross-reference.
4. **README as docsite homepage**: The README is included in the docsite. Duplicate sections, broken trees, and irrelevant env var tables become homepage bugs.
