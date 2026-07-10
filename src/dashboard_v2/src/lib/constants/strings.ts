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

// ── Data Table ────────────────────────────────────────────────────────────────

export const TABLE_STRINGS = {
	/** Default empty-state message when no rows match */
	emptyMessage: 'No rows to display',
} as const;

// ── Pagination ─────────────────────────────────────────────────────────────────

export const PAGINATION_STRINGS = {
	/** aria-label for the pagination <nav> */
	navAriaLabel: 'Table pagination',
	/** aria-label for the previous page button */
	prevAriaLabel: 'Previous page',
	/** aria-label for the next page button */
	nextAriaLabel: 'Next page',
	/** Template for the range label: "Showing {start}–{end} of {total}" */
	rangeLabel: 'Showing {start}–{end} of {total}',
	/** Template for the page indicator: "Page {page} of {pages}" */
	pageIndicator: 'Page {page} of {pages}',
} as const;

// ── Confirm Dialog ────────────────────────────────────────────────────────────

export const CONFIRM_STRINGS = {
	/** Default label for the cancel button (overridable via prop) */
	cancelLabel: 'Cancel',
} as const;

// ── UI Primitives (LKPR-126) ──────────────────────────────────────────────────

// ── NamespaceDot ──
export const NAMESPACE_DOT_STRINGS = {
	ariaHidden: 'true' as const,
} as const;

// ── StatTile ──
export const STAT_TILE_STRINGS = {
	iconAriaHidden: 'true' as const,
} as const;

// ── EmptyState ──
export const EMPTY_STATE_STRINGS = {
	iconAriaHidden: 'true' as const,
} as const;

// ── HeatmapGrid ──
export const HEATMAP_GRID_STRINGS = {
	ariaLabel: 'Heatmap grid' as const,
} as const;