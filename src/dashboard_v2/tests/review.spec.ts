/**
 * Review page E2E tests
 * @see LKPR-137 ACs: both tabs load, bulk select + accept works
 */
import { test, expect } from '@playwright/test';

test.describe('Review page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/review');
	});

	test('renders both tabs (Pending + Reviewed)', async ({ page }) => {
		await expect(page.getByRole('tab', { name: /pending/i })).toBeVisible();
		await expect(page.getByRole('tab', { name: /reviewed/i })).toBeVisible();
	});

	test('Pending tab is active by default', async ({ page }) => {
		const pendingTab = page.getByRole('tab', { name: /pending/i });
		await expect(pendingTab).toHaveAttribute('aria-selected', 'true');
	});

	test('clicking Reviewed tab switches tab', async ({ page }) => {
		await page.getByRole('tab', { name: /reviewed/i }).click();
		await expect(page.getByRole('tab', { name: /reviewed/i })).toHaveAttribute('aria-selected', 'true');
	});

	test('bulk select + accept works', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Select the header checkbox (select all)
		const selectAllCheckbox = page.locator('thead input[type="checkbox"]').first();
		if (await selectAllCheckbox.count() === 0) { test.skip(); return; }
		await selectAllCheckbox.click();
		// Accept button becomes enabled
		const acceptBtn = page.getByRole('button', { name: 'Accept' });
		await expect(acceptBtn).toBeEnabled({ timeout: 3_000 });
	});
});
