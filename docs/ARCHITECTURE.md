# Lorekeeper Architecture (LKPR-105)

> This document describes the current architecture after LKPR-105 Phase 7 (the
> facade deletion / processor layer refactor). See "What Was Removed" below for
> the history.

## Six-Layer Architecture (strictly 1-directional DOWN only)

````text
┌──────────────────────────────────────────────────────────────┐
│  api/mcp/, dashboard/, server.py, cli/                       │ Layer 6 — Interface adapters
├──────────────────────────────────────────────────────────────┤
│  shared/ (serializers, encouragement)                        │ Layer 5 — Presentation helpers
├──────────────────────────────────────────────────────────────┤
│  processors/ (memory, link, reflection, suggestion, admin)   │ Layer 4 — Orchestration
├──────────────────────────────────────────────────────────────┤
│  domains/{memory,link,reflection,suggestion}/                │ Layer 3 — Business logic
├──────────────────────────────────────────────────────────────┤
│  platform/{config,metrics}/                                  │ Layer 2 — Supporting repos
├──────────────────────────────────────────────────────────────┤
│  infra/ (database, search_engine, keyword_index,             │ Layer 1 — Zero business
│         scheduler, logging_setup, settings)                  │           vocabulary
└──────────────────────────────────────────────────────────────┘
```text

### Import rules

- `infra` imports NOTHING from lorekeeper except other `infra` modules
- `platform` imports only `infra`
- `domains` import `platform`, `infra`, and other domains (per DAG below) — never `shared`, `api`, `dashboard`, `server`
- `shared` imports `domains` and below (it serializes domain models for the API layer)
- `processors` import `domains`, `platform`, `infra` — never each other (no `processors.X` imports `processors.Y`)
- `api`/`dashboard`/`server`/`cli` import anything below
- `server.py` is exempt from layer rules (composition root imports everything)

### Cross-domain DAG (acyclic)

```text
suggestion ──→ memory ──→ link
reflection ──→ memory
```text

`link` depends on no other domain. No cycles.

## Layer Responsibilities

| Layer                                          | Owns                                                                                                  | Does NOT own                                           |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Presentation** (api, dashboard, server, cli) | MCP tool routing, HTTP routing, serialization, encouragement wrappers                                 | Validation, metrics, commit, business rules            |
| **shared/**                                    | Serialization format (SearchResult → dict), encouragement text injection                              | Business logic, stores                                 |
| **processors/**                                | Input validation, metric increments, commit boundaries, batch loops                                   | Serialization, single-aggregate business rules         |
| **domains/**                                   | Single-aggregate business rules (dedup, scoring, feedback, search ranking, link candidate generation) | Validation (beyond domain invariants), metrics, commit |
| **platform/**                                  | Supporting subdomain repos (config overrides, metrics storage)                                        | Business logic                                         |
| **infra/**                                     | Database connection + migrations, vector search engine, keyword index, scheduler, settings            | Business vocabulary                                    |

## Key Stores

All stores receive `Database` via constructor injection and share a single connection instance.

| Store                 | Class                 | Location                           |
| --------------------- | --------------------- | ---------------------------------- |
| `Database`            | `Database`            | `infra/database.py`                |
| `MemoryStore`         | `MemoryStore`         | `domains/memory/repository.py`     |
| `LinkStore`           | `LinkStore`           | `domains/link/repository.py`       |
| `ReflectionStore`     | `ReflectionStore`     | `domains/reflection/repository.py` |
| `LinkSuggestionStore` | `LinkSuggestionStore` | `domains/suggestion/repository.py` |
| `MetricsStore`        | `MetricsStore`        | `platform/metrics/repository.py`   |
| `ConfigStore`         | `ConfigStore`         | `platform/config/repository.py`    |

## Domain Service Constructor Signatures

Each service declares exactly the dependencies its methods use — nothing more, nothing less.

| Service               | Constructor params                                                                   |
| --------------------- | ------------------------------------------------------------------------------------ |
| `MemorySearchService` | `(engine, kw, memories, links, cache, settings, db, ns_filter)`                      |
| `MemoryWriteService`  | `(engine, memories, links, cache, settings, db, namespace, ns_filter, link_service)` |
| `LinkService`         | `(links)`                                                                            |
| `ReflectionService`   | `(reflections, db, cache, write_service)`                                            |
| `SuggestionService`   | `(candidate_generator, engine, kw, memories, links, settings, db, ns_filter)`        |
| `ImportService`       | `(engine, memories, links, cache, db, namespace)`                                    |

`MemoryWriteService` is intentionally wide (9 params). The width documents real coupling. Do NOT introduce a bundle object to shorten it. If the constructor becomes unwieldy, split the service — don't re-bundle.

## Shared Collaborators (not services, not bundles)

| Collaborator                           | Location                         | Purpose                                                                                                                                                     |
| -------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `MemoryCache`                          | `domains/memory/cache.py`        | In-process memory cache + BM25 rebuild. MUST be a single shared instance — two instances silently split invalidation.                                       |
| `MetricsStore.increment_metric_safe()` | `platform/metrics/repository.py` | Fire-and-forget metric increment. Swallows sqlite3.Error at WARNING. Documented exception to the no-inline-commit rule — metrics are best-effort by design. |
| `Database.commit()`                    | `infra/database.py`              | `self.conn.commit()`. Commit control belongs to the calling layer, not the store.                                                                           |

## Composition Root (server.py)

`init_service()` is the sole composition root. Wiring order:

1. Settings → engine + probe
2. `Database` + migrate → stores (Memory, Link, Reflection, Metrics, Config, LinkSuggestion)
3. Config overrides applied to settings
4. `KeywordIndex` → `ns_filter` → `MemoryCache`
5. `LinkCandidateGenerator` (constructed once — spaCy model loaded once)
6. Domain services in dependency order: LinkService → MemoryWriteService → MemorySearchService → ReflectionService → SuggestionService → ImportService
7. Processors: Memory, Link, Reflection, Suggestion, Admin
8. BM25 bootstrap via `cache.rebuild_kw()`
9. Encouragement rate
10. Sweep scheduler: OWN `Database` instance (sweep isolation)

**Module singletons:** 5 processors + 3 store/db accessors + settings.

**No `get_service()`.** No `MemoryService` facade.

### Singleton Getters

| Getter                       | Returns               |
| ---------------------------- | --------------------- |
| `get_memory_processor()`     | `MemoryProcessor`     |
| `get_link_processor()`       | `LinkProcessor`       |
| `get_reflection_processor()` | `ReflectionProcessor` |
| `get_suggestion_processor()` | `SuggestionProcessor` |
| `get_admin_processor()`      | `AdminProcessor`      |
| `get_settings()`             | `LorekeeperSettings`  |
| `get_memory_store()`        | `MemoryStore`         |
| `get_link_store()`          | `LinkStore`           |
| `get_db()`                  | `Database`            |

Each raises `RuntimeError("not initialised")` if called before `init_service()`.

## Processor Layer Detail

Each domain slice has one processor. Processors never import each other.

| Processor             | Methods                                                                              | Key responsibilities                                                              |
| --------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `MemoryProcessor`     | `search()`, `insert()`, `remember()`, `update()`, `forget()`, `import_dump()`        | Input validation, metric increments, orchestrates domain services                 |
| `SuggestionProcessor` | `recommend_links()`, `get_pending()`, `review()`                                     | Single batch loop for accept/reject (replaces duplicated loop in MCP + dashboard) |
| `LinkProcessor`       | `list_links()`, `create_link()`, `delete_link()`                                     | Existence validation, relation type check, commit                                 |
| `ReflectionProcessor` | `submit_reflection()`, `processed_session_ids()`                                     | Session ID validation, metric increments                                          |
| `AdminProcessor`      | `get_metrics()`, `get_config()`, `set_config()`, `trigger_sweep()`, `sweep_status()` | Cross-cutting operational use cases                                               |

## Architecture Enforcement

Layering is enforced by `tests/test_architecture.py`, which uses pure stdlib `ast` to walk every module, extract `lorekeeper.*` imports, classify by layer, and assert rules. Any new upward import fails CI with a message naming the offending module and edge.

## What Was Removed (LKPR-105 Phase 7)

- `services/orchestrator.py` — 212-line delegation facade. Replaced by processor layer + explicit DI.
- `services/__init__.py` — empty package. `src/lorekeeper/services/` directory gone.
- `MemoryService` class — the god object/facade. No replacement. Server is the sole composition root.
- `get_service()` — deleted. Callers use `get_memory_processor()`, `get_memory_store()`, etc.

## What Was Added (LKPR-105 Phase 7)

- `processors/` package — 5 processors (memory, link, reflection, suggestion, admin).
- `domains/memory/cache.py` — `MemoryCache` (in-process cache + BM25 rebuild).
- `infra/database.py:commit()` — clean commit method on Database.
- `platform/metrics/repository.py:increment_metric_safe()` — safe fire-and-forget metric.
- `tests/test_architecture.py` — AST-based layer enforcement.
- `domains/*/repository.py` — store classes moved from old `services/` into their domain packages.

## What Changed (LKPR-105 Phase 7)

- All domain services: `__init__(svc: MemoryService)` → explicit constructor deps.
- `infra/*`: zero upward imports. `database.py` migration 4 uses frozen constant; `keyword_index.py` uses `Protocol`; `scheduler.py` uses `Protocol`.
- `server.py`: sole composition root. Explicit getters per processor.
- Dashboard routes: no `commit()` calls. No `get_service()` imports.
- MCP handlers: pass-through + serialize only. No validation, metrics, or batch loops.

## Data Storage

- **LanceDB** — vector embeddings, semantic ANN search (384-dim `all-MiniLM-L6-v2`). Cosine distance (converted to similarity internally). Supports concurrent multi-process access.
- **SQLite sidecar** — memory metadata (score, confidence, soft_deleted, usage_count), all MemoryLink rows, BM25 index rebuild source.

The canonical `lore_id` UUID lives in Mem0's metadata field. All app logic uses `lore_id`.

### Hybrid Scoring Formula

```text
combined = 0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm
```text

Where `log_usage_norm = log2(1 + usage_count) / log2(1 + cap)`. All weights are env-configurable (`LORE_W_*`).

### Feedback / Quality Signals

- **Score delta**: useful=True bumps by `LORE_SCORE_BUMP_UP × (confidence/10)`; False deducts `LORE_SCORE_BUMP_DOWN × ((11-confidence)/10)`
- **Confidence EMA**: sliding window of 20 (`LORE_CONFIDENCE_WINDOW_SIZE`)
- **Soft delete**: triggered when `useful=False AND confidence <= 2`. Once `soft_deleted=True`, it never reverts.
- **Duplicate threshold**: `0.6·semantic + 0.4·keyword >= 0.85` blocks insert unless `force=True`

## Backward Compatibility

- **MCP API surface is identical to v1** — same tool names, same input/output schemas. The three existing skills (`lorekeeper-memorize`, `lorekeeper-search`, `lorekeeper-reconcile`) work with zero changes.
- **No LLM extraction on add** — text is stored verbatim, no inference or rewriting.
- **stdout is reserved for MCP protocol** — all logging goes to stderr via `structlog`.
````
