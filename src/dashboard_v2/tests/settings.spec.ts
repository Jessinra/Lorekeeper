/**
 * Settings page E2E tests
 * @see LKPR-137 ACs: sections render, field change shows unsaved indicator, save works
 */
import { test, expect } from '@playwright/test';

test.describe('Settings page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/settings');
	});

	test('renders 4 core settings sections', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		await expect(page.getByRole('region', { name: /Search Weights/i })).toBeVisible({ timeout: 10_000 });
		await expect(page.getByRole('region', { name: /Scoring/i })).toBeVisible();
		await expect(page.getByRole('region', { name: /Search & Links/i })).toBeVisible();
		await expect(page.getByRole('region', { name: /Memory Lifecycle/i })).toBeVisible();
	});

	test('field change shows unsaved indicator', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Modify any number input in the page
		const firstNumberInput = page.locator('input[type="number"]').first();
		await expect(firstNumberInput).toBeVisible({ timeout: 10_000 });
		const currentVal = await firstNumberInput.inputValue();
		// Type a tiny change
		await firstNumberInput.fill(String(parseFloat(currentVal) + 0.01));
		await firstNumberInput.blur();
		// Unsaved banner should appear
		await expect(page.locator('[role="status"]').filter({ hasText: /unsaved/i })).toBeVisible({ timeout: 3_000 });
	});

	test('save button triggers success toast', async ({ page }) => {
		await page.waitForLoadState('networkidle');
		// Dirty a field first
		const firstNumberInput = page.locator('input[type="number"]').first();
		await expect(firstNumberInput).toBeVisible({ timeout: 10_000 });
		const currentVal = await firstNumberInput.inputValue();
		await firstNumberInput.fill(String(parseFloat(currentVal) + 0.01));
		await firstNumberInput.blur();
		// Click Save in any section
		const saveBtn = page.getByRole('button', { name: 'Save' }).first();
		await saveBtn.click();
		// Toast fires on success — filter to avoid strict-mode violation with multiple [role="status"] elements
		await expect(page.locator('[role="status"]').filter({ hasText: /saved|success/i })).toBeVisible({ timeout: 5_000 });
	});
});
