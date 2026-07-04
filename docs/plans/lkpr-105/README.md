# LKPR-105 Phase 7 — Delivery Plan (step index)

Master spec: `../2026-07-03_134138-lkpr-105-phase7-delete-orchestrator.md` (v3).
Strangler pattern: the `MemoryService` facade stays alive until Step 5.
Every step = one PR, independently green, independently revertable.

Scope discipline per PR: exactly the files listed in the step plan. If a step
uncovers work outside its scope, it goes into a later step or a new ticket —
not into the current diff.

| Step | PR branch                                          | Plan                                                  | Size       | Depends on |
| ---- | -------------------------------------------------- | ----------------------------------------------------- | ---------- | ---------- |
| 0    | `chore/lkpr-105-step0-arch-test`                   | `step-0-architecture-test.md`                         | ~110 lines | —          |
| 1    | `chore/lkpr-105-step1-infra-layering`              | `step-1-infra-layering.md`                            | ~40 lines  | 0          |
| 2    | `chore/lkpr-105-step2-shared-collaborators`        | `step-2-shared-collaborators.md`                      | ~180 lines | 0          |
| 3a   | `chore/lkpr-105-step3a-di-narrow`                  | `step-3a-explicit-di-narrow.md`                       | ~150 lines | 2          |
| 3b   | `chore/lkpr-105-step3b-di-wide`                    | `step-3b-explicit-di-wide.md`                         | ~200 lines | 3a         |
| 4a   | `chore/lkpr-105-step4a-suggestion-processor`       | `step-4a-suggestion-processor.md`                     | ~220 lines | 2 (not 3)  |
| 4b   | `chore/lkpr-105-step4b-memory-processor`           | `step-4b-memory-processor.md`                         | ~260 lines | 3b         |
| 4c   | `chore/lkpr-105-step4c-reflection-link-processors` | `step-4c-reflection-link-processors.md`               | ~150 lines | 3b         |
| 4d   | `chore/lkpr-105-step4d-admin-processor`            | `step-4d-admin-processor.md`                          | ~150 lines | 2          |
| 5    | `chore/lkpr-105-step5-delete-facade`               | `step-5-delete-facade.md`                             | net −300   | 4a-4d      |
| 6    | `chore/lkpr-105-step6-test-relocation`             | `step-6-test-relocation.md`                           | moves only | 5          |
| 7    | `chore/lkpr-105-step7-docs`                        | `step-7-docs.md` + `step-7-architecture-reference.md` | docs only  | 5          |

Ordering notes:

- 4a needs only Step 2 (it calls facade-owned services through
  `svc.suggestion_service` until 3b lands, then a 1-line rewire in 5). If the
  duplicated batch loop should die early, 4a can run right after 2.
- 4d likewise only needs stores + `Database.commit()` (Step 2).
- 3a/3b are pure-internal: facade constructors change, no caller changes.
- 6 and 7 can run in parallel after 5.

Standard verification block (every step, in addition to step-specific checks):

```
uv run pytest -q --ignore=tests/e2e
uv run ruff check src tests scripts/
uv run mypy src
```

Progress tracker: each step deletes its entries from `TEMPORARY_ALLOWED` in
`tests/test_architecture.py`. Step 5 deletes the list itself. If the list is
non-empty after Step 5, the refactor is not done — the test will say exactly
which edge remains.
