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
		// Toolbar is a plain <div aria-label="Memory toolbar"> with no role="group"
		await expect(page.locator('[aria-label="Memory toolbar"]')).toBeVisible({ timeout: 10_000 });
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

	test('pagination controls render when data present', async ({ page }) => {
		// Seed guarantees rows exist — assert loudly rather than skipping.
		await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 });
		const pagination = page.locator('.pagination, [aria-label*="Pagination"], [aria-label*="page"]');
		await expect(pagination.first()).toBeVisible({ timeout: 10_000 });
	});

	test('row click opens Memory detail drawer', async ({ page }) => {
		// Only hydrated data rows carry `.clickable`; skeleton rows shown during
		// the client fetch are aria-hidden and non-interactive. Targeting
		// `tbody tr.clickable` auto-waits for real rows so the click lands on a
		// row with an attached onclick handler (not a pre-hydration skeleton).
		const firstRow = page.locator('tbody tr.clickable').first();
		await expect(firstRow).toBeVisible({ timeout: 10_000 });
		await firstRow.click();
		await expect(page.getByRole('dialog', { name: 'Memory detail' })).toBeVisible({ timeout: 5_000 });
	});

	test('memory detail drawer switches to edit mode', async ({ page }) => {
		const firstRow = page.locator('tbody tr.clickable').first();
		await expect(firstRow).toBeVisible({ timeout: 10_000 });
		await firstRow.click();
		const drawer = page.getByRole('dialog', { name: 'Memory detail' });
		await expect(drawer).toBeVisible({ timeout: 5_000 });
		// Edit mode reveals title input field — require edit button to be present
		const editBtn = drawer.locator('button').filter({ hasText: /edit/i }).first();
		await expect(editBtn).toBeVisible({ timeout: 3_000 });
		await editBtn.click();
		await expect(drawer.locator('#drawer-title')).toBeVisible();
	});
});
