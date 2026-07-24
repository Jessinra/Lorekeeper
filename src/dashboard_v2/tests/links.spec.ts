/**
 * Links page E2E tests
 * @see LKPR-137 ACs: table loads, relationship drawer opens, delete confirms
 */
import { test, expect } from '@playwright/test';

test.describe('Links page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/links');
	});

	test('loads links table', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const content = page.locator('[aria-label="Memory links table"], .empty-state, table');
		await expect(content.first()).toBeVisible({ timeout: 10_000 });
	});

	test('opens relationship drawer on row click', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const rowLink = page.locator('[aria-label^="Open link:"]').first();
		if (await rowLink.count() === 0) { test.skip(); return; }
		await rowLink.click();
		await expect(page.getByRole('dialog', { name: 'Relationship' })).toBeVisible({ timeout: 5_000 });
	});

	test('relationship drawer delete requires confirmation', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const rowLink = page.locator('[aria-label^="Open link:"]').first();
		if (await rowLink.count() === 0) { test.skip(); return; }
		await rowLink.click();
		const drawer = page.getByRole('dialog', { name: 'Relationship' });
		await expect(drawer).toBeVisible({ timeout: 5_000 });

		// "Delete link" button must exist in an open drawer
		const deleteBtn = drawer.locator('button').filter({ hasText: /delete link/i }).first();
		await expect(deleteBtn).toBeVisible({ timeout: 3_000 });
		await deleteBtn.click();
		// Confirmation text should appear
		await expect(drawer.locator('button').filter({ hasText: /delete this link/i })).toBeVisible({ timeout: 3_000 });
	});

	test('relationship drawer cancel restores normal state', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const rowLink = page.locator('[aria-label^="Open link:"]').first();
		if (await rowLink.count() === 0) { test.skip(); return; }
		await rowLink.click();
		const drawer = page.getByRole('dialog', { name: 'Relationship' });
		await expect(drawer).toBeVisible({ timeout: 5_000 });

		const deleteBtn = drawer.locator('button').filter({ hasText: /delete link/i }).first();
		await expect(deleteBtn).toBeVisible({ timeout: 3_000 });
		await deleteBtn.click();
		// Cancel button appears
		const cancelBtn = drawer.getByRole('button', { name: /cancel/i });
		await expect(cancelBtn).toBeVisible({ timeout: 3_000 });
		await cancelBtn.click();
		// Back to normal — "Delete link" button (not confirmation)
		await expect(drawer.locator('button').filter({ hasText: /^delete link$/i })).toBeVisible();
	});
});
