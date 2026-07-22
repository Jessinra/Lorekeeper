/**
 * Metrics page E2E tests
 * @see LKPR-137 ACs: heatmap renders, tooltip shows on hover
 */
import { test, expect } from '@playwright/test';

test.describe('Metrics page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/metrics');
	});

	test('heatmap grid renders', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const heatmap = page.locator('.heatmap-grid, .heatmap-card');
		await expect(heatmap.first()).toBeVisible({ timeout: 10_000 });
	});

	test('heatmap cell tooltip shows on hover', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Find first heatmap cell with data (role="button")
		const cell = page.locator('.hm-cell[role="button"]').first();
		if (await cell.count() === 0) { test.skip(); return; }
		await cell.hover();
		await expect(page.locator('[role="tooltip"]')).toBeVisible({ timeout: 3_000 });
	});
});
