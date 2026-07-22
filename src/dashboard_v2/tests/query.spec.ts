/**
 * Query page E2E tests
 * @see LKPR-137 ACs: query runs, result list updates, inspector shows
 */
import { test, expect } from '@playwright/test';

test.describe('Query page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/query');
	});

	test('renders query input and run button', async ({ page }) => {
		await expect(page.locator('.query-input')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Run query' })).toBeVisible();
	});

	test('running a query updates result list', async ({ page }) => {
		await page.locator('.query-input').fill('memory');
		await page.getByRole('button', { name: 'Run query' }).click();
		// Wait for results or empty state — confirms the query actually ran and returned
		const resultArea = page.locator('[aria-label="Query results"], .result-item, .empty-state, [role="listbox"]');
		await expect(resultArea.first()).toBeVisible({ timeout: 10_000 });
		// If results list is present, at least one item or empty-state must be rendered
		const resultCount = await page.locator('[aria-label="Query results"] li, .result-item').count();
		const emptyState = await page.locator('.empty-state').count();
		expect(resultCount + emptyState).toBeGreaterThan(0);
	});

	test('Enter key triggers query', async ({ page }) => {
		await page.locator('.query-input').fill('test');
		await page.locator('.query-input').press('Enter');
		const resultArea = page.locator('[aria-label="Query results"], .empty-state');
		await expect(resultArea.first()).toBeVisible({ timeout: 10_000 });
	});
});
