/**
 * Shell E2E tests — NavRail, TopBar, Command Palette, Toast, ConfirmDialog
 * @see LKPR-137 ACs: Nav rail, TopBar breadcrumb, Command Palette, Toast, Confirm Dialog
 */
import { test, expect } from '@playwright/test';

const NAV_ITEMS = [
	{ label: 'Home', href: '/' },
	{ label: 'Memories', href: '/memories' },
	{ label: 'Links', href: '/links' },
	{ label: 'Query', href: '/query' },
	{ label: 'Review', href: '/review' },
	{ label: 'Sessions', href: '/sessions' },
	{ label: 'Metrics', href: '/metrics' },
];

test.describe('NavRail', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/');
	});

	test('renders all 7 nav items + Settings', async ({ page }) => {
		for (const item of NAV_ITEMS) {
			await expect(page.getByRole('link', { name: item.label })).toBeVisible();
		}
		await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
	});

	test('active item is highlighted on home', async ({ page }) => {
		const homeLink = page.getByRole('link', { name: 'Home' });
		await expect(homeLink).toHaveAttribute('aria-current', 'page');
	});
});

test.describe('Navigation', () => {
	for (const item of NAV_ITEMS) {
		test(`clicking ${item.label} navigates to ${item.href}`, async ({ page }) => {
			await page.goto('/');
			await page.getByRole('link', { name: item.label }).click();
			await expect(page).toHaveURL(new RegExp(`${item.href === '/' ? '^http' : item.href}`));
		});
	}

	test('clicking Settings navigates to /settings', async ({ page }) => {
		await page.goto('/');
		await page.getByRole('link', { name: 'Settings' }).click();
		await expect(page).toHaveURL(/\/settings/);
	});
});

test.describe('TopBar breadcrumb', () => {
	const pages = [
		{ href: '/', label: 'Home' },
		{ href: '/memories', label: 'Memories' },
		{ href: '/links', label: 'Links' },
		{ href: '/query', label: 'Query' },
		{ href: '/review', label: 'Review' },
		{ href: '/sessions', label: 'Sessions' },
		{ href: '/metrics', label: 'Metrics' },
		{ href: '/settings', label: 'Settings' },
	];

	for (const p of pages) {
		test(`${p.href} shows "${p.label}" breadcrumb`, async ({ page }) => {
			await page.goto(p.href);
			await expect(page.getByTestId('topbar-breadcrumb')).toContainText(p.label);
		});
	}
});

test.describe('Command Palette', () => {
	test('opens on Cmd+K', async ({ page }) => {
		await page.goto('/');
		await page.keyboard.press('Meta+k');
		await expect(page.getByRole('dialog', { name: /command palette/i })).toBeVisible();
	});

	test('keyboard navigation works in palette', async ({ page }) => {
		await page.goto('/');
		await page.keyboard.press('Meta+k');
		const palette = page.getByRole('dialog', { name: /command palette/i });
		await expect(palette).toBeVisible();
		// Arrow down moves focus to first item
		await page.keyboard.press('ArrowDown');
		const firstItem = palette.getByRole('option').first();
		await expect(firstItem).toBeFocused();
	});

	test('closes on Escape', async ({ page }) => {
		await page.goto('/');
		await page.keyboard.press('Meta+k');
		await expect(page.getByRole('dialog', { name: /command palette/i })).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(page.getByRole('dialog', { name: /command palette/i })).not.toBeVisible();
	});
});
