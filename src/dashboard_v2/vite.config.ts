import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

// Minimal ambient declaration for the Node `process` global. This tsconfig
// scope intentionally omits @types/node (browser-oriented SvelteKit app), but
// vite.config runs under Node — we only need `process.env` here for the proxy
// port override, so declare just that slice rather than pulling in all of Node.
declare const process: { env: Record<string, string | undefined> };

// Backend port for the dev-server API proxy. Overridable (E2E_BACKEND_PORT) so
// the E2E suite can run on alternate ports without colliding with a developer's
// own dashboard. Playwright's webServer passes this as a runtime env var to the
// dev process, so we read process.env (not Vite's loadEnv, which only reads
// .env files). Default 7788 matches playwright.config.ts.
const BACKEND_PORT = process.env.E2E_BACKEND_PORT ?? '7788';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		// Dev-server proxy so /api/* calls forward to the FastAPI backend.
		// The Vite dev server owns the browser origin and proxies API traffic.
		proxy: {
			'/api': {
				target: `http://127.0.0.1:${BACKEND_PORT}`,
				changeOrigin: false
			}
		}
	}
});
