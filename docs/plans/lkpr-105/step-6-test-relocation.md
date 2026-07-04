# Step 6 — Test relocation (pure moves, zero logic changes)

**Branch:** `chore/lkpr-105-step6-test-relocation`
**Depends on:** Step 5
**Files:** 2 deleted, 6 created, moves only

## Rule

`git mv`-style relocation: test bodies move verbatim; only imports and
fixtures change (fixtures now build via `_helpers.build_app()` and target the
specific service). If a test body needs a logic change to survive the move,
STOP — that's a smell that a previous step changed behavior; investigate
before proceeding.

## Map

Delete `tests/test_orchestrator.py` (1189 lines) →

- `tests/domains/memory/test_write_service.py` (32):
  test_insert_and_search, test_update_bumps_score,
  test_soft_delete_on_low_confidence_not_useful,
  test_insert_one_memory_missing_title_raises_clear_error,
  test_extract_title_short_thought, test_extract_title_sentence_boundary,
  test_extract_title_no_boundary_breaks_at_word,
  test_new_memory_default_score_is_five, test_remember_stores_full_content,
  test_remember_returns_none_linked_to_when_no_neighbor,
  test_remember_auto_link_when_neighbor_above_threshold,
  test_remember_no_auto_link_below_threshold,
  test_remember_detects_duplicate_title,
  test_remember_auto_link_skips_self_match, test_insert_with_inline_links,
  test_insert_inline_link_invalid_target,
  test_insert_inline_link_invalid_relation,
  test_insert_inline_links_invalid_format_string_not_list,
  test_insert_inline_link_missing_target_memory_id,
  test_insert_inline_link_missing_relation_type,
  test_insert_auto_link_creates_link, test_insert_auto_link_respects_disabled,
  test_insert_auto_link_respects_threshold, test_auto_link_duplicate_guard,
  test_auto_link_uses_settings_k,
  test_insert_with_inline_links_and_top_level_links,
  test_insert_tags_with_agent_namespace,
  test_insert_tags_with_shared_when_no_namespace,
  test_same_title_different_namespace_not_duplicate,
  test_same_title_same_namespace_still_detects_duplicate,
  test_same_title_in_shared_still_detects_duplicate,
  test_shared_agent_deduplicates_against_all_namespaces
- `tests/domains/memory/test_search_service.py` (4):
  test_search_excludes_soft_deleted,
  test_ids_sort_by_recent_malformed_updated_at_does_not_crash,
  test_agent_reads_own_and_shared, test_no_namespace_sees_all
- `tests/domains/link/test_service.py` (1): test_insert_link_between_memories
- `tests/domains/reflection/test_service.py` (13): the 3 submit_reflection
  tests + 10 reflect_auto_insert tests (full names in master plan)
- `tests/domains/suggestion/test_sweep.py` (7): class TestSweepLinks
- `tests/_helpers.py`: FakeEngine (module top) — if 4a/4b already moved it,
  skip

Delete `tests/test_memory_service.py` (162 lines) →

- 5 cache tests: DELETE (Step 2 already created direct MemoryCache tests —
  verify equivalence test-by-test before deleting; port any assert the new
  file lacks)
- 5 forget tests → `tests/domains/memory/test_write_service.py`
- 2 validation tests (test_handle_forget_empty_ids_raises,
  test_handle_forget_invalid_reason_raises) → wherever forget validation
  landed in Step 4b (`tests/processors/test_memory_processor.py`)

## Verification

```
# Count invariance (the key check):
git stash && uv run pytest --collect-only -q --ignore=tests/e2e | tail -1 && git stash pop
uv run pytest --collect-only -q --ignore=tests/e2e | tail -1
# totals must match, minus the 5 deliberately-deleted duplicate cache tests
uv run pytest -q --ignore=tests/e2e
uv run ruff check tests/
```

PR description must state: expected before/after collected-test counts and
the 5-test deletion rationale.

## AC

- [ ] test_orchestrator.py, test_memory_service.py gone
- [ ] Collected count = before − 5 (documented)
- [ ] Diff shows moves (bodies unchanged) — reviewer can verify with
      `git diff --color-moved=dimmed-zebra`
