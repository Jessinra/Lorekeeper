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
		// The tooltip only renders for cells with data (cell.total > 0); empty
		// cells intentionally show nothing. Seeded tool calls land in the current
		// hour, and interactive cells carry tabindex="0" (empty cells are -1), so
		// target the first cell with data rather than the grid's first cell.
		const cell = page.locator('.hm-cell[role="button"][tabindex="0"]').first();
		await expect(cell).toBeVisible({ timeout: 10_000 });
		await cell.hover();
		await expect(page.locator('[role="tooltip"]')).toBeVisible({ timeout: 3_000 });
	});
});
