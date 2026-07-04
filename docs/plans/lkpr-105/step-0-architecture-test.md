# Step 0 — Architecture test with shrinking exception list

**Branch:** `chore/lkpr-105-step0-arch-test`
**Files:** 1 new (`tests/test_architecture.py`)

## Goal

Enforce the FINAL layer rules from day one, with today's known violations
whitelisted in an explicit `TEMPORARY_ALLOWED` set. Any NEW violation fails
CI immediately; each later step's done-condition is deleting its entries.

## Design

Pure stdlib `ast`. Walk every `*.py` under `src/lorekeeper/`, collect
`import lorekeeper.*` / `from lorekeeper.* import ...` edges — including
inside `if TYPE_CHECKING:` blocks (source-level edges count).

Module → layer classification by path prefix:

```python
LAYER = {  # ordered top → bottom
    "api": 6, "dashboard": 6, "cli": 6, "server": 6, "__main__": 6,
    "shared": 5,
    "processors": 4,          # empty until Step 4x — rule still declared
    "domains": 3,
    "platform": 2,
    "infra": 1,
}
```

Final rules asserted:

1. A module may import only from strictly lower layers (same-layer imports
   allowed only within the same top-level package, e.g. infra→infra).
2. Exception: layer 6 (presentation) may import `lorekeeper.server`
   (composition-root getters), `shared`, `processors`, and `domains.*.models`
   ONLY — not domain `service`/`repository`/`ranking` modules, not
   `platform`, not `infra` (except `infra.settings` for type hints — decide
   at implementation; if allowed, encode explicitly).
3. Cross-domain DAG: `suggestion→{memory,link}`, `reflection→{memory}`,
   `memory→{link}` only.
4. No `processors.X` imports `processors.Y` (X≠Y).
5. `lorekeeper.services` must not be imported by anything NOT in
   `TEMPORARY_ALLOWED` — and once the list is empty, must not exist at all.
6. `server.py` is exempt from rule 1 (composition root imports everything).

`TEMPORARY_ALLOWED: set[tuple[str, str]]` — (importer module, imported
module) pairs. Seed with the audited current violations:

```python
TEMPORARY_ALLOWED = {
    # Step 1 removes:
    ("lorekeeper.infra.database", "lorekeeper.domains.link.models"),
    ("lorekeeper.infra.keyword_index", "lorekeeper.domains.memory.models"),
    ("lorekeeper.infra.scheduler", "lorekeeper.platform.config.repository"),
    # Steps 3a/3b remove (domain → facade, TYPE_CHECKING):
    ("lorekeeper.domains.memory.service", "lorekeeper.services.orchestrator"),
    ("lorekeeper.domains.memory.import_service", "lorekeeper.services.orchestrator"),
    ("lorekeeper.domains.link.service", "lorekeeper.services.orchestrator"),
    ("lorekeeper.domains.reflection.service", "lorekeeper.services.orchestrator"),
    ("lorekeeper.domains.suggestion.service", "lorekeeper.services.orchestrator"),
    # Steps 4a-4d / 5 remove (presentation → facade / deep domain / infra):
    ("lorekeeper.api.mcp.handlers.memory_handlers", "lorekeeper.services.orchestrator"),
    ("lorekeeper.api.mcp.handlers.memory_handlers", "lorekeeper.domains.memory.ranking"),
    ("lorekeeper.api.mcp.handlers.suggestion_handlers", "lorekeeper.services.orchestrator"),
    ("lorekeeper.server", "lorekeeper.services.orchestrator"),  # composition root, dies in Step 5
    # ... complete this seed by running the collector and dumping current
    # violations verbatim at implementation time — the seed MUST be exactly
    # the audit output, no hand-curation.
}
```

(The `# Step N removes` comments are load-bearing — they make the tracker
readable in review.)

Failure message must name importer, imported, and the violated rule, e.g.:
`domains.memory.service -> shared.serializers: domains may not import shared (layer 3 -> 5)`.

## Implementation notes

- Collector: `ast.walk`, handle `Import` and `ImportFrom` (absolute only —
  repo has no relative imports; assert that too, cheap).
- One test per rule (6 tests) so failures are legible, plus
  `test_temporary_allowed_entries_are_still_real` — every entry in
  `TEMPORARY_ALLOWED` must still be an actual edge; stale entries fail. This
  forces each step to delete its entries in the same PR that fixes them.

## Verification

```
uv run pytest tests/test_architecture.py -v      # all pass on main
uv run pytest -q --ignore=tests/e2e              # full suite green
uv run ruff check src tests scripts/ && uv run mypy src
```

Negative check: temporarily add `from lorekeeper.shared.serializers import
serialize_search_result` to `domains/memory/service.py` → test must fail
naming that edge. Revert before commit (do this locally, note it in PR).

## AC

- [ ] Test passes on current main with the seeded exception list
- [ ] Seed list generated from collector output, not hand-typed
- [ ] Stale-entry guard test present
- [ ] Negative check performed and noted in PR description
