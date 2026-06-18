# Lorekeeper Architecture

Lorekeeper follows a strict 4-layer architecture. Every file belongs to exactly one layer. Dependencies only flow downward — a layer may call the layer below it, never above.

```
┌─────────────────────────────────────────────────────────┐
│                     HANDLER LAYER                       │
│                                                         │
│  MCP transport          │  HTTP transport               │
│  server.py              │  dashboard/app.py             │
│  (_handle_* helpers)    │  dashboard/routes/            │
│                         │                               │
│  Input validation, output formatting, transport         │
│  concerns (MCP tool signatures, HTTP status codes).     │
│  No business logic here.                                │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                     SERVICE LAYER                       │
│                                                         │
│  services/orchestrator.py                               │
│                                                         │
│  Owns transaction boundaries (conn.commit).             │
│  Orchestrates multi-store operations.                   │
│  Single entry point — both transports call this.        │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                     MODULE LAYER                        │
│                                                         │
│  serializers.py          keyword_index.py               │
│  services/search.py      services/dedup.py              │
│  services/feedback.py    services/engine_factory.py     │
│  services/memory_engine.py                              │
│  services/lancedb_engine.py                             │
│                                                         │
│  Reusable business logic. No direct DB access.          │
│  No transport awareness.                                │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                      DATA LAYER                         │
│                                                         │
│  services/memory_store.py    services/link_store.py     │
│  services/reflection_store.py  services/metrics_store.py│
│  services/config_store.py    services/database.py       │
│                                                         │
│  Pure SQL — reads and writes only, no commits.          │
│  Commits owned by orchestrator (service layer).         │
│  database.py owns connection lifecycle + migrations.    │
└─────────────────────────────────────────────────────────┘
```

## Handler layer — two transports, same responsibility

MCP and HTTP are different transports into the same service. They follow the same pattern:

|                             | MCP         | HTTP                                         |
| --------------------------- | ----------- | -------------------------------------------- |
| Registration + input/output | `server.py` | `dashboard/app.py` + `dashboard/routes/*.py` |

Both transports live in one file per transport entry point. MCP input sanitization lives as private `_handle_*` helpers inside `server.py` — same file, clearly separated by a comment block.

## Key invariants

- **Stores never commit.** `conn.commit()` lives only in `orchestrator.py` and `dashboard/routes/` (via `svc.commit()`).
- **Dashboard handlers may access store methods through `svc` public attributes** (e.g. `svc.memories.update_memory_fields`). They must call `svc.commit()` after writes. MCP handlers go through `orchestrator` methods exclusively.
- **Modules are stateless.** `serializers.py`, `search.py`, `dedup.py`, `feedback.py` are pure functions — no DB, no service references.
- **One shared SQLite connection.** All stores share `database.conn`. Orchestrator grabs it as `self._conn = memories._conn`.
