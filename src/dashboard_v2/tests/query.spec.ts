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
		// The query is async (~0.5s). Wait for the outcome to actually render —
		// either result rows (role=option inside the listbox) or an empty state —
		// rather than just the container, which mounts before results arrive.
		const resultRow = page.locator('[aria-label="Query results"] [role="option"], .empty-state');
		await expect(resultRow.first()).toBeVisible({ timeout: 10_000 });
		const resultCount = await page.locator('[aria-label="Query results"] [role="option"]').count();
		const emptyState = await page.locator('.empty-state').count();
		expect(resultCount + emptyState).toBeGreaterThan(0);
	});

	test('Enter key triggers query', async ({ page }) => {
		await page.locator('.query-input').fill('test');
		// `.fill()` dispatches the input event, but Svelte's bind:value → queryText
		// update flushes on a microtask. Wait for the Run button to enable, which
		// proves queryText committed, before pressing Enter — otherwise the keydown
		// handler reads a stale empty value and runQuery() early-returns.
		await expect(page.getByRole('button', { name: 'Run query' })).toBeEnabled();
		await page.locator('.query-input').press('Enter');
		// Wait for the query outcome to render, not merely the results container.
		const resultRow = page.locator('[aria-label="Query results"] [role="option"], .empty-state');
		await expect(resultRow.first()).toBeVisible({ timeout: 10_000 });
	});
});
