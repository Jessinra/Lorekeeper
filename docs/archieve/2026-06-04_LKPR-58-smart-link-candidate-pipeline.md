# [LKPR-58] Smart link candidate pipeline — lore_recommend_links MCP tool + agent skill

**Status:** Plan  
**Ticket:** [LKPR-58](backlogs/proposal/LKPR-58-smart-link-candidate-pipeline.md)  
**Date:** 2026-06-04  
**Branch:** `feature/LKPR-58-smart-link-candidate-pipeline` (to be created)

---

## Goal

Ship `lore_recommend_links` — a two-stage candidate pipeline that surfaces high-confidence memory link candidates for the agent to review and confirm via `lore_insert(links=[...])`. No auto-write, no bulk backfill.

---

## Current State

Backend plumbing is **already implemented** but hasn't been on a feature branch:

| Area                                              | Status                                                                           |
| ------------------------------------------------- | -------------------------------------------------------------------------------- |
| `services/link_candidate.py`                      | ✅ Complete — 4 scorers + generator                                              |
| `services/relation_classifier.py`                 | ✅ Complete — batched LLM classifier                                             |
| `services/orchestrator.py`                        | ✅ `recommend_links()` method                                                    |
| `server.py`                                       | ✅ MCP tool + handler registered                                                 |
| `serializers.py`                                  | ✅ `serialize_link_candidate()`                                                  |
| `config.py`                                       | ✅ All `LORE_LINK_*` env vars (syntax bug fixed)                                 |
| `models.py`                                       | ✅ RelationType literal extended to 8 types                                      |
| **`database.py`**                                 | ❌ **CHECK constraint out of sync** — only has 5 original types, models.py has 8 |
| Test `test_lkpr58_link_candidate.py`              | ⚠️ Partial — 2 tests failing, needs cleanup                                      |
| `test_lkpr58_relation_classifier.py`              | ❌ Missing                                                                       |
| `assets/skills/lorekeeper-link-memories/SKILL.md` | ❌ Missing                                                                       |
| CLAUDE.md update                                  | ❌ Missing                                                                       |
| README.md update                                  | ❌ Missing                                                                       |

---

## Step-by-Step Plan

### Step 0 — Branch

Create feature branch from current state:

```bash
git checkout -b feature/LKPR-58-smart-link-candidate-pipeline
```

### Step 1 — Fix DB CHECK constraint (schema migration)

The `memory_links` table's CHECK constraint (`relation_type IN ('related_to','used_in','used_for','used_by','used_as')`) needs to include the 3 new types added to `models.py`:

- `contradicts`
- `supersedes`
- `depends_on`

**Approach:** Add migration v2 in `database.py` that drops and re-creates the CHECK constraint. SQLite doesn't support `ALTER TABLE ... ALTER CONSTRAINT`, so this needs:

1. `ALTER TABLE memory_links RENAME TO memory_links_old`
2. `CREATE TABLE memory_links ...` with updated CHECK
3. `INSERT INTO memory_links SELECT ... FROM memory_links_old`
4. `DROP TABLE memory_links_old`

This is an in-place schema migration — wrapped in a `MIGRATIONS` entry.

### Step 2 — Fix test failures in `test_lkpr58_link_candidate.py`

**BM25Scorer test:** The BM25 corpus needs to demonstrate a clear ranking difference. The current test texts are too short for meaningful BM25 differentiation. Fix by using longer, clearly different texts or relaxing the assertion.

**`test_linked_ids_excluded`:** Uses `depends_on` type which will fail FK CHECK until Step 1 is done. Fix by using `used_in` instead, or gate on Step 1.

**Other fixture issues:** `Memory(id=..., created_at=..., updated_at=...)` fields already handled in prior edits.

### Step 3 — Write `test_lkpr58_relation_classifier.py`

- Mock `httpx.post` responses for LLM classifier
- Test: valid relation returned, `"none"` filtered, error handling, classifier skipped when base_url empty
- Import same FakeEngine from `test_orchestrator.py` or `test_lkpr58_link_candidate.py`

### Step 4 — Create `assets/skills/lorekeeper-link-memories/SKILL.md`

Agent skill distributed via `setup.sh`. Covers:

- When to call `lore_recommend_links` (post-session, after inserting a batch, manually)
- How to read the candidate output (scorer_breakdown, proposed_relation)
- What makes a good link (thematic connection, shared entities, temporal proximity)
- What to skip (weak scores, classifier=noise)
- Calling `lore_insert(links=[...])` to confirm

### Step 5 — Update CLAUDE.md

- Add `lore_recommend_links` to MCP API surface
- Add `LORE_LINK_*` env vars to the env var table

### Step 6 — Update README.md

- Document `lore_recommend_links` tool
- Brief description of the link candidate pipeline

### Step 7 — Verify everything passes

```bash
uv run pytest tests/test_lkpr58_link_candidate.py tests/test_lkpr58_relation_classifier.py -v
uv run ruff check src/lorekeeper/services/link_candidate.py src/lorekeeper/services/relation_classifier.py
```

---

## Files to Change

| File                                              | Action                                             |
| ------------------------------------------------- | -------------------------------------------------- |
| `src/lorekeeper/services/database.py`             | **UPDATE** — migration v2 for CHECK constraint     |
| `tests/test_lkpr58_link_candidate.py`             | **FIX** — 2 failing tests                          |
| `tests/test_lkpr58_relation_classifier.py`        | **CREATE** — relation classifier tests             |
| `assets/skills/lorekeeper-link-memories/SKILL.md` | **CREATE** — agent skill                           |
| `CLAUDE.md`                                       | **UPDATE** — doc `lore_recommend_links` + env vars |
| `README.md`                                       | **UPDATE** — doc `lore_recommend_links` tool       |

---

## Risks & Open Questions

1. **DB migration v2 is irreversible if data exists.** SQLite CHECK constraint replacement requires a table rebuild. At current scale (<5k memories, minimal links) this is fast and safe.
2. **The 3 new relation types (`contradicts`, `supersedes`, `depends_on`) have no link count yet** — they're forward-looking. The CHECK constraint fix opens the door; actual usage depends on agents choosing to create these link types.
3. **spaCy dependency** — `EntityOverlapScorer` gracefully degrades when spaCy isn't installed. The skill should document this.

---

## AC Checklist

- [ ] Feature branch created from correct state
- [ ] DB migration v2: CHECK constraint includes all 8 relation types
- [ ] `test_lkpr58_link_candidate.py` all tests green
- [ ] `test_lkpr58_relation_classifier.py` created and green
- [ ] `assets/skills/lorekeeper-link-memories/SKILL.md` created
- [ ] CLAUDE.md updated
- [ ] README.md updated
- [ ] Ruff lint clean
- [ ] Full test suite green (`uv run pytest -x`)
