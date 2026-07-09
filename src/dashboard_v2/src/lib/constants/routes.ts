/**
 * Single source of truth for all navigation routes.
 *
 * Consumed by:
 *  - NavRail.svelte (nav items, icons, badges)
 *  - TopBar.svelte (breadcrumb label lookup)
 *  - commands.ts (jump commands for the Command Palette)
 */

import {
	ICON_HOME,
	ICON_MEMORIES,
	ICON_LINKS,
	ICON_SEARCH,
	ICON_REVIEW,
	ICON_SESSIONS,
	ICON_METRICS,
	ICON_SETTINGS
} from '$lib/constants/icons.js';

export interface NavRoute {
	href: string;
	label: string;
	/** SVG path `d` attribute data — viewBox="0 0 24 24", stroke-based */
	icon: string;
	badge?: number;
}

/** Ordered list of primary nav routes shown in the rail. */
export const NAV_ROUTES: NavRoute[] = [
	{ href: '/',          label: 'Home',     icon: ICON_HOME     },
	{ href: '/memories',  label: 'Memories', icon: ICON_MEMORIES },
	{ href: '/links',     label: 'Links',    icon: ICON_LINKS    },
	{ href: '/query',     label: 'Query',    icon: ICON_SEARCH   },
	{ href: '/review',    label: 'Review',   icon: ICON_REVIEW, badge: 8 },
	{ href: '/sessions',  label: 'Sessions', icon: ICON_SESSIONS },
	{ href: '/metrics',   label: 'Metrics',  icon: ICON_METRICS  }
];

/** Bottom-pinned nav routes, rendered below the spacer (e.g. settings). */
export const UTILITY_ROUTES: NavRoute[] = [
	{ href: '/settings', label: 'Settings', icon: ICON_SETTINGS }
];

/** All routes, in priority order for prefix matching (used by matchRoute / labelFromPath). */
const ALL_ROUTES: NavRoute[] = [...NAV_ROUTES, ...UTILITY_ROUTES];

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
