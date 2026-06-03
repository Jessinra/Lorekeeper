# Lorekeeper Architecture

Lorekeeper follows a strict 4-layer architecture. Every file belongs to exactly one layer. Dependencies only flow downward — a layer may call the layer below it, never above.

```
┌─────────────────────────────────────────────────────────┐
│                     HANDLER LAYER                       │
│                                                         │
│  MCP transport          │  HTTP transport               │
│  server.py              │  dashboard/app.py             │
│  handlers.py            │  dashboard/routes/            │
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
│  services/chromadb_engine.py                            │
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

| | MCP | HTTP |
|---|---|---|
| Registration | `server.py` (`@mcp.tool`) | `dashboard/app.py` (`router.include_router`) |
| Input/output | `handlers.py` | `dashboard/routes/*.py` |

`handlers.py` exists because MCP tool registration (`server.py`) and input sanitization are kept separate — `server.py` would otherwise become a fat file mixing FastMCP wiring with 70+ lines of search path logic.

## Key invariants

- **Stores never commit.** `conn.commit()` lives only in `orchestrator.py` and `dashboard/routes/` (via `svc.commit()`).
- **Handlers never touch stores directly.** All writes go through `orchestrator`.
- **Modules are stateless.** `serializers.py`, `search.py`, `dedup.py`, `feedback.py` are pure functions — no DB, no service references.
- **One shared SQLite connection.** All stores share `database.conn`. Orchestrator grabs it as `self._conn = memories._conn`.
