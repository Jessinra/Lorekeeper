/**
 * Sessions page E2E tests
 * @see LKPR-137 ACs: timeline loads, session drawer opens, stacked drawer works
 */
import { test, expect } from '@playwright/test';

test.describe('Sessions page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/sessions');
	});

	test('loads sessions timeline / table', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const content = page.locator('table, .timeline, .session-row, .empty-state');
		await expect(content.first()).toBeVisible({ timeout: 10_000 });
	});

	test('opens session drawer on row click', async ({ page }) => {
		const sessionLink = page.locator('[aria-label^="Open session:"]').first();
		await expect(sessionLink).toBeVisible({ timeout: 10_000 });
		await sessionLink.click();
		await expect(page.getByRole('dialog', { name: 'Session detail' })).toBeVisible({ timeout: 5_000 });
	});

	test('session drawer closes on close button', async ({ page }) => {
		const sessionLink = page.locator('[aria-label^="Open session:"]').first();
		await expect(sessionLink).toBeVisible({ timeout: 10_000 });
		await sessionLink.click();
		const drawer = page.getByRole('dialog', { name: 'Session detail' });
		await expect(drawer).toBeVisible({ timeout: 5_000 });
		await drawer.getByRole('button', { name: 'Close drawer' }).click();
		await expect(drawer).not.toBeVisible();
	});
});
