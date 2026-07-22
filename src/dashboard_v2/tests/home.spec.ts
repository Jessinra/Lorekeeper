/**
 * Home page E2E tests
 * @see LKPR-137 ACs: health ring, stat tiles, activity feed
 */
import { test, expect } from '@playwright/test';

test.describe('Home page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
	});

	test('loads health ring section', async ({ page }) => {
		await expect(page.locator('[aria-labelledby="health-card-title"]')).toBeVisible({ timeout: 10_000 });
	});

	test('loads activity section', async ({ page }) => {
		await expect(page.locator('[aria-labelledby="activity-heading"]')).toBeVisible({ timeout: 10_000 });
	});

	test('stat tiles are present', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Home renders 4 .stat-link tile wrappers — assert their presence directly
		await expect(page.locator('.stat-link').first()).toBeVisible({ timeout: 10_000 });
		const count = await page.locator('.stat-link').count();
		expect(count).toBeGreaterThanOrEqual(4);
	});
});
