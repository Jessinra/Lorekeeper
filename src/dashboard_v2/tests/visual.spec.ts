/**
 * Visual regression tests — screenshot each page against baseline
 * Fail CI on >0.1% pixel diff.
 * @tag @visual
 * @see LKPR-137 AC: "Visual regression: Screenshot each page … CI fails on >0.1% pixel diff"
 *
 * First run: npx playwright test --grep @visual --update-snapshots
 * Subsequent: npx playwright test --grep @visual
 */
import { test, expect } from '@playwright/test';

const PAGES = [
	{ name: 'home', url: '/', readyLocator: '.stat-link' },
	{ name: 'memories', url: '/memories', readyLocator: 'table, .empty-state' },
	{ name: 'sessions', url: '/sessions', readyLocator: '.timeline, .empty-state' },
	{ name: 'review', url: '/review', readyLocator: '[role="tab"]' },
	{ name: 'links', url: '/links', readyLocator: 'table, .empty-state' },
	{ name: 'query', url: '/query', readyLocator: '.query-input' },
	{ name: 'metrics', url: '/metrics', readyLocator: '.heatmap, .empty-state, [aria-label*="heatmap"]' },
	{ name: 'settings', url: '/settings', readyLocator: '[role="region"]' },
];

for (const p of PAGES) {
	test(`@visual ${p.name} page matches baseline`, async ({ page }) => {
		const response = await page.goto(p.url);
		// Fail immediately if navigation itself returned an error page
		expect(response?.ok(), `Navigation to ${p.url} failed with status ${response?.status()}`).toBe(true);
		// Wait for a route-specific ready element instead of arbitrary timing
		await expect(page.locator(p.readyLocator).first()).toBeVisible({ timeout: 15_000 });
		await expect(page).toHaveScreenshot(`${p.name}.png`, {
			maxDiffPixelRatio: 0.001, // 0.1%
			fullPage: false,          // viewport only — 1440×900 per config
		});
	});
}
