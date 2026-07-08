/**
 * Single source of truth for all navigation routes.
 *
 * Consumed by:
 *  - NavRail.svelte (nav items, icons, badges)
 *  - TopBar.svelte (breadcrumb label lookup)
 */

export interface NavRoute {
	href: string;
	label: string;
	/** SVG path `d` attribute data — viewBox="0 0 24 24", stroke-based */
	icon: string;
	badge?: number;
}

/** Ordered list of primary nav routes shown in the rail. */
export const NAV_ROUTES: NavRoute[] = [
	{
		href: '/',
		label: 'Home',
		icon: 'M3 11l9-8 9 8M5 10v10h14V10'
	},
	{
		href: '/memories',
		label: 'Memories',
		icon: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'
	},
	{
		href: '/links',
		label: 'Links',
		icon: 'M5 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M19 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M12 19m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M7 7.3L10.2 16.5M17 7.3L13.8 16.5M7.5 6H16.5'
	},
	{
		href: '/query',
		label: 'Query',
		icon: 'M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M21 21l-4.3-4.3'
	},
	{
		href: '/review',
		label: 'Review',
		icon: 'M4 4h16v12H8l-4 4V4zM4 12h5l2 3h2l2-3h5',
		badge: 8
	},
	{
		href: '/sessions',
		label: 'Sessions',
		icon: 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 7v5l4 2'
	},
	{
		href: '/metrics',
		label: 'Metrics',
		icon: 'M4 20V10M12 20V4M20 20v-7'
	}
];

export const SETTINGS_ROUTE: NavRoute = {
	href: '/settings',
	label: 'Settings',
	icon: 'M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1M12 12m-3.2 0a3.2 3.2 0 1 0 6.4 0a3.2 3.2 0 1 0-6.4 0'
};

/** All routes, in priority order for prefix matching (used by matchRoute / labelFromPath). */
const ALL_ROUTES: NavRoute[] = [...NAV_ROUTES, SETTINGS_ROUTE];

/**
 * True when `pathname` belongs to the route at `href`.
 * `/` matches only the exact root; other routes match themselves or any sub-path.
 */
export function matchRoute(pathname: string, href: string): boolean {
	if (href === '/') return pathname === '/';
	return pathname === href || pathname.startsWith(href + '/');
}

/**
 * Derive the page label from a pathname.
 * Exact match first, then longest prefix, fallback to 'Home'.
 */
export function labelFromPath(pathname: string): string {
	const exact = ALL_ROUTES.find((r) => r.href === pathname);
	if (exact) return exact.label;
	const prefix = ALL_ROUTES.filter((r) => matchRoute(pathname, r.href) && r.href !== '/').sort(
		(a, b) => b.href.length - a.href.length
	)[0];
	return prefix ? prefix.label : 'Home';
}
