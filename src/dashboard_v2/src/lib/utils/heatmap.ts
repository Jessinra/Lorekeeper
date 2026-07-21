/**
 * Shared heatmap utilities — hour array and day label formatter.
 * Used by the main metrics page heatmap and ToolBreakdownCard mini-heatmaps.
 */

/** Ordered array of all 24 hours (0–23). */
export const HEATMAP_HOURS: readonly number[] = Array.from({ length: 24 }, (_, i) => i);

/**
 * Convert an ISO date string ("YYYY-MM-DD") to a short weekday label ("Mon").
 * Uses noon to avoid any timezone-boundary date shift.
 */
export function heatmapDayLabel(day: string): string {
	return new Date(day + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' });
}
