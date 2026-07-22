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
	{ name: 'home', url: '/' },
	{ name: 'memories', url: '/memories' },
	{ name: 'sessions', url: '/sessions' },
	{ name: 'review', url: '/review' },
	{ name: 'links', url: '/links' },
	{ name: 'query', url: '/query' },
	{ name: 'metrics', url: '/metrics' },
	{ name: 'settings', url: '/settings' },
];

for (const p of PAGES) {
	test(`@visual ${p.name} page matches baseline`, async ({ page }) => {
		await page.goto(p.url);
		await page.waitForLoadState('networkidle');
		// Brief settle for animations
		await page.waitForTimeout(300);
		await expect(page).toHaveScreenshot(`${p.name}.png`, {
			maxDiffPixelRatio: 0.001, // 0.1%
			fullPage: false,          // viewport only — 1440×900 per config
		});
	});
}
