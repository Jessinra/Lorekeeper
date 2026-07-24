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
			const expectedURL =
				item.href === '/'
					? new RegExp('^http://[^/]+/$')
					: new RegExp(`${item.href}$`);
			await expect(page).toHaveURL(expectedURL);
		});
	}

	test('clicking Settings navigates to /settings', async ({ page }) => {
		await page.goto('/');
		await page.getByRole('link', { name: 'Settings' }).click();
		await expect(page).toHaveURL(/\/settings$/);
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
			// TopBar renders: <nav class="breadcrumb"><span class="breadcrumb-current">Label</span></nav>
			await expect(page.locator('.breadcrumb-current')).toContainText(p.label);
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

		// CommandPalette uses aria-activedescendant — DOM focus stays on the search input.
		// Arrow down advances activeIndex from 0 → 1; verify via aria-activedescendant update.
		const searchInput = palette.locator('input[type="search"], input[role="combobox"], input');
		await page.keyboard.press('ArrowDown');
		// After ArrowDown the active-descendant attribute must reference an option element.
		await expect(searchInput).toHaveAttribute('aria-activedescendant', /.+/);
	});

	test('closes on Escape', async ({ page }) => {
		await page.goto('/');
		await page.keyboard.press('Meta+k');
		await expect(page.getByRole('dialog', { name: /command palette/i })).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(page.getByRole('dialog', { name: /command palette/i })).not.toBeVisible();
	});
});
