import { defineConfig, devices } from '@playwright/test';

/**
 * Dashboard V2 E2E config — real FE+BE stack (LKPR-140).
 *
 * webServer[0] = FastAPI backend (serves /api/*), started FIRST.
 * webServer[1] = Vite dev server, proxies /api/* → backend (see vite.config.ts).
 * Playwright's baseURL always hits the frontend; the browser never talks to the
 * backend directly.
 *
 * The backend command SEEDS deterministic fixture data (memories, links,
 * reflections, suggestion sweep) in-process *before* uvicorn starts — this
 * ordering is required because the dashboard builds its in-memory BM25 search
 * index at startup, so the data must already be on disk when it boots. (This is
 * why we seed in the webServer command, not Playwright's globalSetup — globalSetup
 * runs AFTER webServer plugins start, which would leave search stale.)
 *
 * Ports are env-configurable so the suite never collides with a developer's own
 * running dashboard (which owns the conventional 7777/7778). Defaults are
 * deliberately offset to 7787 (FE) / 7788 (BE) so a plain `npx playwright test`
 * never hijacks or is hijacked by a live dev dashboard via reuseExistingServer.
 * E2E_FRONTEND_PORT / E2E_BACKEND_PORT override both here and in vite.config.ts.
 */
const FRONTEND_PORT = process.env.E2E_FRONTEND_PORT ?? '7787';
const BACKEND_PORT = process.env.E2E_BACKEND_PORT ?? '7788';

export default defineConfig({
	testDir: './tests',
	timeout: 30_000,
	retries: 0,
	use: {
		baseURL: `http://localhost:${FRONTEND_PORT}`,
		screenshot: 'only-on-failure',
	},
	projects: [
		{
			name: 'chromium',
			use: {
				...devices['Desktop Chrome'],
				viewport: { width: 1440, height: 900 },
			},
		},
	],
	webServer: [
		{
			// 1. Seed fixture data, then start the FastAPI backend (serves /api/*).
			//    Must be index 0 (Playwright starts webServer entries in order).
			//    fastapi/uvicorn live in the `dashboard` optional-dependency group.
			//    LORE_DASH_RELOAD=0 → single process (no reloader child) so the seeded
			//    data dir is read once at startup.
			command:
				'uv run --extra dashboard python src/dashboard_v2/tests/seed.py && ' +
				`uv run --extra dashboard python -m lorekeeper.dashboard --port ${BACKEND_PORT}`,
			url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
			cwd: '../..',
			reuseExistingServer: !process.env.CI,
			timeout: 180_000,
			env: {
				LORE_DATA_DIR: process.env.LORE_DATA_DIR ?? '/tmp/lk-e2e',
				LORE_DASH_RELOAD: '0',
				TOKENIZERS_PARALLELISM: 'false',
			},
		},
		{
			// 2. Vite dev server — proxies /api/* → backend above.
			//    Vite binds to `localhost` by default (not the IPv4 127.0.0.1
			//    literal), so the readiness url must use localhost too.
			command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
			url: `http://localhost:${FRONTEND_PORT}`,
			reuseExistingServer: !process.env.CI,
			timeout: 60_000,
			env: {
				E2E_BACKEND_PORT: BACKEND_PORT,
			},
		},
	],
});
