import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests',
	timeout: 30_000,
	retries: 0,
	use: {
		baseURL: 'http://127.0.0.1:7777',
		viewport: { width: 1440, height: 900 },
		screenshot: 'only-on-failure',
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
	],
	webServer: {
		command: 'npm run preview -- --port 7777',
		url: 'http://127.0.0.1:7777',
		reuseExistingServer: !process.env.CI,
		timeout: 60_000,
	},
});
