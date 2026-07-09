/**
 * Named SVG path constants for the app icon set.
 *
 * All paths assume a 24×24 viewBox, stroke-based rendering (fill="none").
 * Single source of truth — import here instead of embedding path strings
 * inline in routes, commands, or components.
 */

// ─── Navigation icons ─────────────────────────────────────────────────────────

export const ICON_HOME     = 'M3 11l9-8 9 8M5 10v10h14V10';
export const ICON_MEMORIES = 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z';
export const ICON_LINKS    =
	'M5 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M19 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M12 19m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M7 7.3L10.2 16.5M17 7.3L13.8 16.5M7.5 6H16.5';
export const ICON_SEARCH   = 'M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M21 21l-4.3-4.3';
export const ICON_REVIEW   = 'M4 4h16v12H8l-4 4V4zM4 12h5l2 3h2l2-3h5';
export const ICON_SESSIONS = 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 7v5l4 2';
export const ICON_METRICS  = 'M4 20V10M12 20V4M20 20v-7';
export const ICON_SETTINGS =
	'M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1M12 12m-3.2 0a3.2 3.2 0 1 0 6.4 0a3.2 3.2 0 1 0-6.4 0';

// ─── Generic UI icons ──────────────────────────────────────────────────────────

export const ICON_ARROW_RIGHT = 'M5 12h14M12 5l7 7-7 7';

// ─── Status / feedback icons ───────────────────────────────────────────────────

export const ICON_CHECK    = 'M5 13l4 4L19 7';
export const ICON_X_CLOSE  = 'M6 18L18 6M6 6l12 12';
export const ICON_INFO_DOT = 'M12 8v4m0 4h.01';

// ─── Dialog icons ──────────────────────────────────────────────────────────────

export const ICON_INFO_CIRCLE =
	'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';

// ─── Data table icons ───────────────────────────────────────────────────────────

/** Empty / no-data table icon — a document with a dash */
export const ICON_TABLE_EMPTY =
	'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4';

export const ICON_TRASH =
	'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16';
