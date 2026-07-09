import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

export default defineConfig({
	plugins: [svelte({ hot: false })],
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: ['./src/test-setup.ts'],
		include: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
		// Use browser package exports so Svelte resolves to the client build
		// (avoids "mount is not available on the server" error with Svelte 5)
		server: {
			deps: {
				inline: [/svelte/]
			}
		}
	},
	resolve: {
		conditions: ['browser'],
		alias: {
			$lib: resolve(__dirname, 'src/lib')
		}
	}
});
