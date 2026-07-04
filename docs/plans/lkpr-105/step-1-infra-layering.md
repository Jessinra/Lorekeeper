# Step 1 — Infra layering fixes (infra imports nothing upward)

**Branch:** `chore/lkpr-105-step1-infra-layering`
**Files:** 3 modified + `tests/test_architecture.py` (delete 3 exception entries)
**Behavior change:** none (byte-identical runtime behavior)

## Changes

### 1. `src/lorekeeper/infra/database.py`

Remove `from lorekeeper.domains.link.models import RELATION_TYPES` (line 31).
In `_migration_4_revise_link_relation_types`, replace the derived set with the
frozen literal — migrations are historical snapshots and must not read live
constants:

```python
_ALL_12: list[str] = sorted([
    "causes", "contradicts", "derived_from", "explains", "part_of",
    "references", "supersedes",                       # new 7
    "blocked_by", "duplicates", "relates_to",         # transitional 3 — VERIFY
    "related_to", "used_in", "used_for", "used_by", "used_as",  # old 5 — VERIFY
])
```

IMPORTANT: do NOT trust the names above — derive the exact 12 strings by
evaluating `sorted(set(RELATION_TYPES) | {"related_to","used_in","used_for","used_by","used_as"})`
on main BEFORE editing, and paste that output. Add a comment:
`# Frozen snapshot of RELATION_TYPES as of migration 4 (LKPR-67). Do not sync with models.py.`

Regression guard: add a test (in existing `tests/test_database.py`) asserting
the migrated CHECK constraint accepts exactly the 12 frozen strings —
`sqlite3` insert of each type succeeds, a 13th random string fails.

### 2. `src/lorekeeper/infra/keyword_index.py`

Remove `from lorekeeper.domains.memory.models import Memory`. Add:

```python
class IndexableDoc(Protocol):
    id: str
    title: str
    description: str
    content: str
```

`rebuild(self, memories: list[IndexableDoc])` — call sites unchanged
(`Memory` satisfies the protocol structurally).

### 3. `src/lorekeeper/infra/scheduler.py`

Remove the TYPE_CHECKING import of `ConfigStore`. Add:

```python
class OverrideStore(Protocol):
    def get_overrides(self) -> dict[str, str]: ...
    def set_override(self, key: str, value: str) -> None: ...
```

VERIFY exact method signatures against `platform/config/repository.py` before
writing the protocol — mypy will catch drift but check first.

### 4. `tests/test_architecture.py`

Delete the 3 `# Step 1 removes:` entries. (Stale-entry guard forces this.)

## Verification

```
uv run pytest tests/test_architecture.py -v   # passes with 3 fewer exceptions
uv run pytest tests/test_database.py -v       # incl. new frozen-constraint test
uv run pytest -q --ignore=tests/e2e
uv run ruff check src tests scripts/ && uv run mypy src
grep -rn "from lorekeeper" src/lorekeeper/infra/ --include='*.py' | grep -v "lorekeeper.infra"   # → empty
```

## AC

- [ ] `infra/` has zero lorekeeper imports outside `infra/`
- [ ] Migration 4 constant frozen with provenance comment + regression test
- [ ] Both Protocols mypy-clean against real call sites
- [ ] 3 exception entries deleted
