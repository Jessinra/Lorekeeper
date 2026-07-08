# Holistic Code Review — Beyond the Diff

**The diff shows what changed. Holistic review asks whether it should have changed at all — and whether the result is a better system.**

Do not start with line-by-line diff reading. Start by zooming out.

## Phase 1 — Before the Diff

### Read every changed file in full

```bash
# Changed files
git diff main...HEAD --name-only

# Read each one — not just the diff, the whole file
read_file src/lorekeeper/services/sweep_service.py
```

The diff hides context. A 5-line addition could be the most fragile code in the file. A deletion of 200 lines could be deleting a function that's still called from an import path you haven't checked. **You cannot judge a change without knowing the file it lives in.**

### Read adjacent files

If the PR adds a new store (`suggestion_store.py`), also read:

- How it's wired into `server.py`
- How it's used by its service (`sweep_service.py`)
- How the orchestrator exposes it (or doesn't)
- The existing store it resembles (`link_store.py`)

A change that looks clean in isolation often reveals duplication, layering violations, or dead code when read alongside its neighbours.

### Read the plan / ticket

Does the implementation match the design? Common discrepancies:

- Ticket says "standalone service" → code puts it on the orchestrator
- Ticket says "auto-accept" → code uses confidence tagging only
- Ticket says 3 files → actual PR touches 12 files (scope creep)

## Phase 2 — High-Level Architecture

### Does this belong here?

The most important question for every PR. New code has a natural tendency to attach itself to the largest, most convenient object (the orchestrator, the god class). Ask:

- Could this be a standalone service with explicit dependencies?
- Is this a user-facing operation (belongs on MemoryService) or a background task (belongs on a standalone service)?
- Does it introduce a new dependency direction? (e.g. `dashboard/` importing from `server.py`)

**Rule of thumb:** If the feature could function without the rest of the system (given its dependencies), it should be a separate class or module — not a method on an orchestrator.

### Is the simplest thing that works?

Complexity compounds. Every generalization done "for future use" is debt until that future arrives:

- Configurable weights that are never changed
- Abstract base classes with one implementation
- Factory patterns with one product
- Hooks/plugins with no registrants

**The test:** Delete the abstraction. If the code still works and is _simpler_, the abstraction was premature.

### Are the boundaries right?

Read the imports of every new file. Then read every import of the changed files. Questions:

- Does `services/sweep_service.py` import from `services/orchestrator.py`? (wrong direction — orchestration layer sits above services)
- Does `server.py` import from `services/orchestrator.py` directly? (correct — server wires services)
- Is there a circular import that doesn't exist yet but will on the next PR?

### What does this change about the next change?

Every PR makes the next PR either easier or harder. A clean modular addition makes the next similar addition a cookie-cutter. A tangled addition makes the next change require touching 12 files again.

**The test:** "If someone needs to add a similar feature next sprint, how many files do they change?" If the answer is the same number as this PR, the architecture didn't improve. If it's fewer, the PR is a good design.

## Phase 3 — Low-Level Patterns

Only after the holistic picture is clear should you read the diff line by line.

### Walk the call graph

For every new public method, trace where it's called from:

```
new_method() → called_by_A() → called_by_B() → server.py line 142
```

If the only callers are tests, the method is either:

- Dead code (the production path does something different)
- Test-only infrastructure (should be annotated as such)

**This is how `svc.sweep_links()` in the PR description — a method that never existed — would have been caught:** the description claimed it, but a call-graph trace would show zero call sites in production code.

### Verify every constructor parameter is used

A parameter added to `__init__` that's only stored and never read is dead code. Collect every `self.X =` in the constructor, then search for `self.X` in method bodies.

**This is how `db: Database` on MemoryService — added solely to create a store that was never read — would have been caught.**

### Check for drift between docs and code

The PR body, the plan file, and CLAUDE.md each describe the system. They should agree with each other and with the actual code. If the PR says "MemoryService.sweep_links()" but the code defines "SweepService.run()", the description is stale — and stale descriptions cause future confusion.

## The Holistic Review Checklist

```
[ ] Read every changed file in full (not just the diff)
[ ] Read adjacent / wired files (server.py wiring, caller modules)
[ ] Read the ticket / plan — does implementation match?
[ ] Does the new code belong where it was placed? (standalone vs orchestrator)
[ ] Is it the simplest version that works? (no premature abstraction)
[ ] Are import boundaries correct? (no circular deps, no wrong-direction imports)
[ ] Verify every constructor parameter is actually used
[ ] Trace the call graph — does production code reach every new method?
[ ] Spot-check README, CLAUDE.md, docs for staleness against code
[ ] Cross-reference PR description claims against actual diffs
```

## References

- **Blocking overly-clever patterns** → `blocker-patterns.md` (15 BLOCKER patterns)
- **Maintainability & simplicity** → `maintainability-simplicity.md` (complexity review)
- **Backward compatibility** → `backward-compatibility.md` (data + API contracts)
- **PR #237 review** → `pr-237-review-patterns.md` (real example: script crash, dead store, README drift)
