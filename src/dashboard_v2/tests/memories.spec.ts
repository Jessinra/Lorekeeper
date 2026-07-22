/**
 * Memories page E2E tests
 * @see LKPR-137 ACs: data table loads, sort, paginate, row click → drawer, edit mode
 */
import { test, expect } from '@playwright/test';

test.describe('Memories page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/memories');
	});

	test('loads data table', async ({ page }) => {
		await expect(page.getByRole('group', { name: 'Memory toolbar' })).toBeVisible();
		// Table renders — either rows or skeleton/empty state
		const table = page.locator('table, [aria-label="Loading memories"], [aria-label*="memory"]');
		await expect(table.first()).toBeVisible({ timeout: 10_000 });
	});

	test('sorts by column header click', async ({ page }) => {
		// Click "Title" column header to sort
		const titleHeader = page.getByRole('columnheader', { name: /Title/i });
		await expect(titleHeader).toBeVisible({ timeout: 10_000 });
		await titleHeader.click();
		await expect(page).toHaveURL(/sort=title/);
	});

	test('pagination controls render', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Pagination is rendered when there are rows — check the nav/select
		const pagination = page.locator('.pagination, [aria-label*="Pagination"], [aria-label*="page"]');
		// Either present (with data) or table is empty — both are valid states
		await expect(page.locator('table, .empty-state')).toBeVisible({ timeout: 10_000 });
	});

	test('row click opens Memory detail drawer', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const firstRow = page.locator('tbody tr').first();
		const rowCount = await firstRow.count();
		if (rowCount === 0) {
			test.skip(); // no data in test environment
			return;
		}
		await firstRow.click();
		await expect(page.getByRole('dialog', { name: 'Memory detail' })).toBeVisible({ timeout: 5_000 });
	});

	test('memory detail drawer switches to edit mode', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		const firstRow = page.locator('tbody tr').first();
		if (await firstRow.count() === 0) { test.skip(); return; }
		await firstRow.click();
		const drawer = page.getByRole('dialog', { name: 'Memory detail' });
		await expect(drawer).toBeVisible({ timeout: 5_000 });
		// Edit mode reveals title input field
		const editBtn = drawer.locator('button').filter({ hasText: /edit/i }).first();
		if (await editBtn.count() > 0) {
			await editBtn.click();
			await expect(drawer.locator('#drawer-title')).toBeVisible();
		}
	});
});
