# Sprint: Token-Efficient Search, Reflect Auto-Create, lore_forget, MCP Server Card

**Sprint Goal:** Ship auto-reflect and token-efficient search, deliver lore_forget + MCP Server Card as quick wins.

**Sequence:** LKPR-49 → LKPR-30 → LKPR-54 → LKPR-48

## Sprint Items

| # | Issue | Pri | Effort | What |
|---|---|---|---|---|
| 1 | LKPR-49 — Token-efficient search | P1 | S | `format='title'` mode + `ids` bulk retrieval. No deps. |
| 2 | LKPR-30 — Reflect auto-create memories | P2 | S | Auto-insert discoveries/lessons as memories during reflection. Depends on LKPR-29 (done). |
| 3 | LKPR-54 — lore_forget | P2 | S | Soft-delete MCP tool + reason logging. Mostly plumbing. |
| 4 | LKPR-48 — MCP Server Card | P1 | S | Static metadata resource for agent self-configuration. |

**Buffer:** ~20% for production fixes discovered while touching handlers/server.

**Left out of this sprint:** LKPR-18 (provenance — let LKPR-50/51 settle), LKPR-20 (lore_related — link density too low).

## Execution Plan

### 1. LKPR-49 Token-Efficient Search

Part A — `format` param: `lore_search` accepts `format='title' | 'full'` (default 'full'). Title mode returns `id`, `title`, `score` only.

Part B — `ids` param: When `ids=[uuid, ...]` provided, skip vector/BM25, SQL lookup only.

**Files:**
- `src/lorekeeper/schemas.py` — add `format` and `ids` to `LoreSearchInput`
- `src/lorekeeper/services/search.py` — branch on format; add SQL ids-lookup path
- `src/lorekeeper/services/orchestrator.py` — pass params through
- `tests/test_search.py` — tests for format + ids modes

### 2. LKPR-30 Reflect Auto-Create

When `lore_reflect(auto_insert=True, default)` is called, each `factual_discoveries` and `lessons_learnt` item gets auto-inserted as a memory via `lore_remember` logic and linked back to the reflection.

**Files:**
- `src/lorekeeper/schemas.py` — add `auto_insert: bool` param
- `src/lorekeeper/services/orchestrator.py` — auto-insert loop + link creation
- `src/lorekeeper/handlers.py` — extend return with `memories_created`
- `tests/test_orchestrator.py` — assert memories created from discoveries

### 3. LKPR-54 lore_forget

New MCP tool: `lore_forget(memory_ids=[...], reason)` — soft-delete with audit logging.

**Files:**
- `src/lorekeeper/handlers.py` — new handler
- `src/lorekeeper/schemas.py` — `LoreForgetParams`
- `src/lorekeeper/services/memory_engine.py` — thin wrapper for soft-delete by ID
- `tests/test_handlers.py` — tests for the new tool

### 4. LKPR-48 MCP Server Card

Static capabilities resource accessible via MCP `resources/list` — embedding model, vector store, tools, usage hints.

**Files:**
- `src/lorekeeper/server.py` — add resources/list handler
- `src/lorekeeper/capabilities.py` — capabilities dict builder

## Risk

LKPR-49 and LKPR-48 both touch `server.py`/`handlers.py` — potential conflicts if done in parallel. Executed sequentially so no issue.
