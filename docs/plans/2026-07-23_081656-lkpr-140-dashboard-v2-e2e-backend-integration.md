# [LKPR-140] Plan: Dashboard V2 E2E — Full FE/BE Integration Test Suite

**Filed:** 2026-07-23  
**Branch:** `feat/LKPR-140-dashboard-v2-e2e-backend-integration`  
**Base:** `origin/main`  
**PR target:** `main`

---

## Problem Summary

The existing Playwright suite (LKPR-137) is broken for all data-driven tests in CI.

Root cause: `playwright.config.ts` starts `npm run preview` as the web server, which serves only the static SvelteKit bundle — it has **no dev proxy** and does not expose the FastAPI `/api/*` routes (`/api/health`, `/api/memories`, `/api/config`, `/api/links`, `/api/metrics`, etc.).

With no backend on port 7777, every API call fails. Pages fall back to their `{:else}` error/loading branches. Tests that rely on real rendered data — Home stats, Memory table rows, Settings sections, visual snapshots — cannot pass.

Additionally there is no seeded test data, so even if the API were reachable, many tests would silently skip or see empty states.

---

## Goal

Wire the Playwright suite to a **real running backend + frontend** so that every test exercises actual FE↔BE interaction:

1. Backend (FastAPI, port **7778**) starts before Playwright, seeded with deterministic fixture data
2. Frontend (Vite dev server, port **7777**) proxies `/api/*` → backend
3. Every existing test that was skipping due to missing data now runs for real
4. CI (`ci.yml`) runs the full suite on every push

---

## Architecture

```
Playwright test runner
        │
        ▼
Vite dev server :7777   (npm run dev -- --port 7777)
        │
        │  /api/* → proxy
        ▼
FastAPI backend :7778   (uv run python -m lorekeeper.dashboard --port 7778)
        │
        ▼
SQLite + LanceDB at $LORE_DATA_DIR=/tmp/lk-e2e-<run-id>/
```

The Vite dev server acts as the single entry point for Playwright. All page navigation goes through port 7777. All API calls are proxied to 7778 by Vite's `server.proxy`. The backend is seeded with fixture data before any test runs via Playwright's `globalSetup`.

---

## Step-by-Step Implementation

### Step 1 — `vite.config.ts`: Add dev proxy

Add a `server.proxy` block so `/api/*` calls from the Vite dev server are forwarded to the FastAPI backend on port 7778.

```ts
// vite.config.ts — add inside defineConfig({})
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:7778',
      changeOrigin: false,
    }
  }
}
```

**Why 7778 not 7777?** Vite dev server owns 7777. The backend must be on a different port so Playwright's single `baseURL: 'http://127.0.0.1:7777'` hits Vite, not the backend directly.

---

### Step 2 — `playwright.config.ts`: Dual `webServer`

Replace the single `webServer` entry with an array of two. Playwright waits for both to be ready before running any test.

```ts
webServer: [
  {
    // 1. Start the FastAPI backend (serves /api/*)
    command: 'uv run python -m lorekeeper.dashboard --port 7778',
    url: 'http://127.0.0.1:7778/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      LORE_DATA_DIR: process.env.LORE_DATA_DIR ?? '/tmp/lk-e2e',
      TOKENIZERS_PARALLELISM: 'false',
    },
  },
  {
    // 2. Start Vite dev server (proxies /api/* → backend above)
    command: 'npm run dev -- --port 7777',
    url: 'http://127.0.0.1:7777',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
],
globalSetup: './tests/global-setup.ts',
```

**Order matters:** backend must start first (it's entry 0). Playwright starts `webServer` entries in array order.

---

### Step 3 — `tests/global-setup.ts` + `tests/seed.py`: Seed fixture data

The seed runs in two parts because reflections and suggestions have no REST POST endpoint — they are MCP-only. Strategy: use `fetch` for everything with a REST endpoint, then shell out to `seed.py` for the MCP-only parts.

#### `tests/global-setup.ts`

```ts
// tests/global-setup.ts
import { execSync } from "child_process";
import type { FullConfig } from "@playwright/test";

const BASE_API = "http://127.0.0.1:7778";

async function post(url: string, body: unknown): Promise<any> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Seed failed: POST ${url} → ${res.status}`);
  return res.json();
}

export default async function globalSetup(_config: FullConfig) {
  // ── 1. Memories (REST: POST /api/memories) ─────────────────────────────
  const memoryIds: string[] = [];
  for (let i = 1; i <= 10; i++) {
    const res = await post(`${BASE_API}/api/memories`, {
      thought: `Fixture memory ${i}: testing dashboard interaction with real data.`,
      source_type: i % 3 === 0 ? "inferred" : "observed",
    });
    if (res?.lore_id) memoryIds.push(res.lore_id);
  }

  // ── 2. Links (REST: POST /api/links) ───────────────────────────────────
  if (memoryIds.length >= 2) {
    await post(`${BASE_API}/api/links`, {
      source_id: memoryIds[0],
      target_id: memoryIds[1],
      relation: "related",
    });
  }
  if (memoryIds.length >= 3) {
    await post(`${BASE_API}/api/links`, {
      source_id: memoryIds[1],
      target_id: memoryIds[2],
      relation: "supports",
    });
  }

  // ── 3. Reflections + suggestions (MCP-only: shell out to Python) ───────
  // Reflections have no REST POST — submitted via MCP lore_reflect tool only.
  // seed.py imports processors directly and inserts 3 reflections + runs sweep.
  const dataDir = process.env.LORE_DATA_DIR ?? "/tmp/lk-e2e";
  const repoRoot = process.cwd().replace(/\/src\/dashboard_v2$/, "");
  execSync(`uv run python src/dashboard_v2/tests/seed.py`, {
    cwd: repoRoot,
    env: { ...process.env, LORE_DATA_DIR: dataDir },
    stdio: "inherit",
  });
}
```

#### `tests/seed.py`

Handles reflections and suggestion sweep via direct processor imports.

```python
# src/dashboard_v2/tests/seed.py
# Run from repo root: uv run python src/dashboard_v2/tests/seed.py
import asyncio, os, sys
sys.path.insert(0, 'src')
os.environ.setdefault('LORE_DATA_DIR', '/tmp/lk-e2e')

from lorekeeper.infra.settings import Settings
from lorekeeper.infra.database import Database
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.domains.suggestion.repository import LinkSuggestionStore
from lorekeeper.processors.reflection import ReflectionProcessor
from lorekeeper.processors.suggestion import SuggestionProcessor

async def main():
    settings = Settings()
    db = Database(settings)
    db.migrate()

    memory_store = MemoryStore(db)
    link_store = LinkStore(db)
    reflection_store = ReflectionStore(db)
    suggestion_store = LinkSuggestionStore(db)
    engine = LanceDBEngine(settings)
    keyword_index = KeywordIndex(db)

    # 3 reflections → sessions timeline page has data
    refp = ReflectionProcessor(reflection_store, memory_store)
    for i in range(1, 4):
        refp.submit_reflection(
            session_id=f"fixture-session-{i:03d}",
            summary=f"Fixture session {i}: explored memory retrieval patterns.",
            topic=f"topic-{i}",
            task_type="feature",
            lessons_learnt=[f"Lesson {i}a", f"Lesson {i}b"],
            factual_discoveries=[f"Discovery {i}"],
        )

    # Suggestion sweep → /api/suggestions returns candidates
    suggestp = SuggestionProcessor(
        memory_store=memory_store,
        link_store=link_store,
        suggestion_store=suggestion_store,
        engine=engine,
        keyword_index=keyword_index,
    )
    await suggestp.sweep()
    print("Seed complete: 3 reflections + suggestion sweep done.")

asyncio.run(main())
```

**Data shape guarantees:**

| Page                   | Seeded data              | What it enables                   |
| ---------------------- | ------------------------ | --------------------------------- |
| Home                   | 10 memories              | stat tiles show counts > 0        |
| Memories               | 10 rows                  | table renders, pagination visible |
| Links                  | 2 links                  | link list renders, not empty      |
| Sessions / Reflections | 3 reflections            | sessions timeline renders         |
| Suggestions / Review   | sweep run                | suggestions list has candidates   |
| Settings               | config from backend init | sections render with real values  |

---

### Step 4 — Existing tests: Remove defensive skips

With real data seeded, `test.skip()` guards in `memories.spec.ts` become unnecessary. Remove them so the full test body always runs:

```ts
// Before:
if ((await firstRow.count()) === 0) {
  test.skip();
  return;
}

// After:
await expect(firstRow).toBeVisible({ timeout: 10_000 }); // must have data — fails loudly if not
```

This is important: the skip guards were a workaround for missing backend. With a seeded backend they hide real failures.

---

### Step 5 — `.github/workflows/ci.yml`: Add `playwright-dashboard` job

New job after the existing `e2e` job:

```yaml
playwright-dashboard:
  name: Playwright Dashboard V2 (FE+BE)
  runs-on: ubuntu-latest
  needs: test

  steps:
    - uses: actions/checkout@v7

    - name: Set up Python, uv & dependencies
      uses: ./.github/actions/setup-python-uv

    - name: Cache & pre-warm HuggingFace model
      uses: ./.github/actions/setup-huggingface

    - name: Setup Node.js for Dashboard V2
      uses: ./.github/actions/setup-node-dashboard-v2

    - name: Install Playwright browsers
      working-directory: src/dashboard_v2
      run: npx playwright install chromium --with-deps

    - name: Run Playwright suite
      working-directory: src/dashboard_v2
      env:
        CI: "true"
        LORE_DATA_DIR: /tmp/lk-e2e-${{ github.run_id }}
        TOKENIZERS_PARALLELISM: "false"
        HF_HOME: ~/.cache/huggingface
      run: npx playwright test

    - name: Upload Playwright report
      if: failure()
      uses: actions/upload-artifact@v4
      with:
        name: playwright-report
        path: src/dashboard_v2/playwright-report/
        retention-days: 7
```

**Why `needs: test`?** The Python unit tests must pass before we spin up the backend for E2E. Fail fast.

**Why upload report on failure?** Playwright HTML report contains screenshots + traces. Essential for debugging CI failures without re-running locally.

---

## Files Changed

| File                                      | Change                                                              |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `src/dashboard_v2/vite.config.ts`         | Add `server.proxy: { '/api': { target: 'http://127.0.0.1:7778' } }` |
| `src/dashboard_v2/playwright.config.ts`   | Two-entry `webServer[]`, add `globalSetup` reference                |
| `src/dashboard_v2/tests/global-setup.ts`  | New file — seeds fixture data before suite                          |
| `src/dashboard_v2/tests/memories.spec.ts` | Remove `test.skip()` guards, replace with hard `expect`             |
| `.github/workflows/ci.yml`                | New `playwright-dashboard` job                                      |

**No backend code changes.** The existing FastAPI routes are already correct — this is purely test infrastructure wiring.

---

## Acceptance Criteria

- [ ] `npx playwright test` passes locally when run from `src/dashboard_v2/` with the backend running
- [ ] Home page test verifies health ring, stat tiles (with real counts > 0), activity section
- [ ] Memories page test verifies table renders rows from seed data, drawer opens on row click, edit mode activates
- [ ] Settings page test verifies all 4 sections render, unsaved indicator fires, save toast fires (real PATCH to backend)
- [ ] Shell test verifies nav rail, breadcrumbs, command palette (aria-activedescendant), confirm dialog
- [ ] Links, review, query, metrics, sessions, visual snapshot tests pass
- [ ] CI `playwright-dashboard` job green on a clean push
- [ ] Playwright HTML report uploaded as artifact on failure
- [ ] No `test.skip()` guards remaining that exist solely because "no data in test environment"

---

## What This Does NOT Cover

- Mobile / responsive Playwright tests (separate ticket if needed)
- Performance / load testing
- Cross-browser (Firefox, WebKit) — can be added to `playwright.config.ts` projects array later
- Accessibility automated audit (axe-playwright) — separate ticket
