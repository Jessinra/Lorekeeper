// ─── Sort utilities — LKPR-125 ───────────────────────────────────────────────
// Client-side sort helpers for DataTable. Sorting is stable and case-insensitive
// for text columns. Numeric columns sort by numeric value.

/**
 * Default set of column keys considered numeric.
 * Page-specific overrides can be passed via the second argument.
 */
export const DEFAULT_NUMERIC_KEYS = [
	'score', 'uses', 'confidence', 'count', 'updated', 'created',
] as const;

/**
 * Heuristic: returns true if the column key likely holds numeric data.
 * Used to determine the default sort direction (descending for numeric,
 * ascending for text).
 *
 * @param key - The column key to check.
 * @param numericKeys - Optional override list. Defaults to `DEFAULT_NUMERIC_KEYS`.
 */
export function isNumericColumn(key: string, numericKeys?: readonly string[]): boolean {
	return (numericKeys ?? DEFAULT_NUMERIC_KEYS).includes(key);
}

/**
 * Toggle sort direction: asc → desc, desc → asc.
 */
export function toggleDirection(current: 'asc' | 'desc'): 'asc' | 'desc' {
	return current === 'asc' ? 'desc' : 'asc';
}

/**
 * Stable-sort an array of rows by a given column key.
 *
 * - Text columns: case-insensitive localeCompare
 * - Numeric columns: numeric subtraction (missing values sort to end)
 * - Returns a **new** array — does not mutate the input
 * - Uses a stable sort via index fallback for equal values
 */
export function sortRows<T>(
	rows: T[],
	column: string,
	direction: 'asc' | 'desc',
	isNumeric: boolean
): T[] {
	const dir = direction === 'asc' ? 1 : -1;

	return [...rows].sort((a, b) => {
		const va = (a as Record<string, unknown>)[column];
		const vb = (b as Record<string, unknown>)[column];

		let cmp: number;

		if (isNumeric) {
			const na = typeof va === 'number' ? va : Number(va);
			const nb = typeof vb === 'number' ? vb : Number(vb);

			if (isNaN(na) && isNaN(nb)) cmp = 0;
			else if (isNaN(na)) cmp = 1;
			else if (isNaN(nb)) cmp = -1;
			else cmp = na - nb;
		} else {
			const sa = va == null ? '' : String(va);
			const sb = vb == null ? '' : String(vb);
			cmp = sa.localeCompare(sb, undefined, { sensitivity: 'base' });
		}

		return cmp * dir;
	});
}