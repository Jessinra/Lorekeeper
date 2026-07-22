import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests',
	timeout: 30_000,
	retries: 0,
	use: {
		baseURL: 'http://127.0.0.1:7777',
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
	webServer: {
		command: 'npm run build && npm run preview -- --port 7777',
		url: 'http://127.0.0.1:7777',
		reuseExistingServer: !process.env.CI,
		timeout: 120_000,
	},
});
