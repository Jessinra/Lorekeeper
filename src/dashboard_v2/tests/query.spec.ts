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
		// Result list or "no results" both confirm the query ran
		const resultArea = page.locator('[aria-label="Query results"], .empty-state, [role="listbox"]');
		await expect(resultArea.first()).toBeVisible({ timeout: 10_000 });
	});

	test('Enter key triggers query', async ({ page }) => {
		await page.locator('.query-input').fill('test');
		await page.locator('.query-input').press('Enter');
		const resultArea = page.locator('[aria-label="Query results"], .empty-state');
		await expect(resultArea.first()).toBeVisible({ timeout: 10_000 });
	});
});
