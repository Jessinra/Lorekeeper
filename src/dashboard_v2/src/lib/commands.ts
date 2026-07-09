/**
 * Command registry — single source of truth for all palette commands.
 *
 * Commands are grouped into three categories:
 *  - 'recent'  — recently accessed items (dynamically populated at runtime)
 *  - 'jump'    — navigation shortcuts (Jump to …)
 *  - 'actions' — app-level actions (run search, open settings, …)
 */

import { NAV_ROUTES } from '$lib/constants/routes.js';

export type CommandGroup = 'recent' | 'jump' | 'actions';

export interface Command {
	id: string;
	label: string;
	/** Short secondary text shown to the right (e.g. keyboard hint or category) */
	hint?: string;
	group: CommandGroup;
	/** SVG path `d` — 24×24 stroke-based icon */
	icon?: string;
	/** Handler called when the command is selected */
	action: () => void;
}

// ─── Icon paths ──────────────────────────────────────────────────────────────

const ICON_ARROW_RIGHT = 'M5 12h14M12 5l7 7-7 7';
const ICON_SETTINGS =
	'M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1M12 12m-3.2 0a3.2 3.2 0 1 0 6.4 0a3.2 3.2 0 1 0-6.4 0';
const ICON_SEARCH = 'M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M21 21l-4.3-4.3';

// ─── Jump commands (generated from NAV_ROUTES) ────────────────────────────────

function buildJumpCommands(navigate: (href: string) => void): Command[] {
	return NAV_ROUTES.map((route) => ({
		id: `jump:${route.href}`,
		label: route.label,
		hint: route.href,
		group: 'jump' as CommandGroup,
		icon: route.icon ?? ICON_ARROW_RIGHT,
		action: () => navigate(route.href)
	}));
}

// ─── Static action commands ────────────────────────────────────────────────────

function buildActionCommands(callbacks: {
	openQuery: () => void;
	openSettings: () => void;
}): Command[] {
	return [
		{
			id: 'action:open-query',
			label: 'Search memories',
			hint: 'Query',
			group: 'actions',
			icon: ICON_SEARCH,
			action: callbacks.openQuery
		},
		{
			id: 'action:open-settings',
			label: 'Open settings',
			hint: 'Settings',
			group: 'actions',
			icon: ICON_SETTINGS,
			action: callbacks.openSettings
		}
	];
}

// ─── Public API ───────────────────────────────────────────────────────────────

export interface BuildCommandsOptions {
	navigate: (href: string) => void;
	openQuery: () => void;
	openSettings: () => void;
}

/** Returns the full command list (recent is empty until runtime population). */
export function buildCommands(opts: BuildCommandsOptions): Command[] {
	return [...buildJumpCommands(opts.navigate), ...buildActionCommands(opts)];
}

/** Group display labels — used by CommandPalette to render section headers. */
export const GROUP_LABELS: Record<CommandGroup, string> = {
	recent: 'Recent',
	jump: 'Jump to',
	actions: 'Actions'
};

/** Ordered group rendering sequence. */
export const GROUP_ORDER: CommandGroup[] = ['recent', 'jump', 'actions'];

/**
 * Filter commands by a query string.
 * Empty query returns all commands unchanged.
 * Matching: case-insensitive substring on label or hint.
 */
export function filterCommands(commands: Command[], query: string): Command[] {
	const q = query.trim().toLowerCase();
	if (!q) return commands;
	return commands.filter(
		(cmd) =>
			cmd.label.toLowerCase().includes(q) ||
			(cmd.hint ?? '').toLowerCase().includes(q)
	);
}
