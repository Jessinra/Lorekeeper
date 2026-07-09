/**
 * UI display strings — single source of truth for all user-visible text.
 *
 * Centralised here so they're easy to audit, swap for i18n, and keep
 * consistent across components. Every string that appears in the rendered
 * DOM or an ARIA attribute should live here rather than inline in templates.
 *
 * Naming: group by component, prefer descriptive semantic names over positional
 * ones (e.g. `closeButtonAriaLabel` not `button2Label`).
 */

// ── App-wide ──────────────────────────────────────────────────────────────────

export const APP_NAME = 'Lorekeeper' as const;

// ── Command Palette ───────────────────────────────────────────────────────────

export const PALETTE_STRINGS = {
	/** role="dialog" aria-label */
	dialogAriaLabel: 'Command palette',
	/** Text input placeholder */
	inputPlaceholder: 'Search or jump to…',
	/** Close button aria-label */
	closeButtonAriaLabel: 'Close palette',
	/** Results listbox aria-label */
	resultsListAriaLabel: 'Commands',
	/** Static prefix for the empty-state message — e.g. 'No results for "foo"' */
	emptyStatePreamble: 'No results for',
	/** Footer keyboard hint labels */
	footerNavigate: 'navigate',
	footerSelect: 'select',
	footerClose: 'close',
} as const;

// ── Top Bar ───────────────────────────────────────────────────────────────────

export const TOP_BAR_STRINGS = {
	/** aria-label for the breadcrumb <nav> */
	breadcrumbNavAriaLabel: 'Breadcrumb',
	/** Static "root" segment shown in the breadcrumb trail */
	breadcrumbRoot: APP_NAME,
	/** Visible placeholder inside the search trigger button */
	searchTriggerPlaceholder: 'Search or jump to…',
} as const;

// ── Nav Rail ──────────────────────────────────────────────────────────────────

export const NAV_RAIL_STRINGS = {
	/** aria-label for the primary <nav> element */
	navAriaLabel: 'Primary navigation',
	/** Alt text for the brand logo image */
	logoAlt: APP_NAME,
	/** Tooltip title on the health indicator dot */
	healthDotTitle: 'System healthy',
	/** aria-label on the health indicator dot */
	healthDotAriaLabel: 'System status: healthy',
	/** Suffix appended to badge counts: "{N} pending" */
	badgePendingSuffix: 'pending',
} as const;

// ── Toast ─────────────────────────────────────────────────────────────────────

export const TOAST_STRINGS = {
	/** aria-label for the dismiss (×) button */
	dismissAriaLabel: 'Dismiss notification',
} as const;

// ── Confirm Dialog ────────────────────────────────────────────────────────────

export const CONFIRM_STRINGS = {
	/** Default label for the cancel button (overridable via prop) */
	cancelLabel: 'Cancel',
} as const;
