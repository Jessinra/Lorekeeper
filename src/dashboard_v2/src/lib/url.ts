/**
 * URL / search-param utilities for dashboard route pages.
 *
 * All paginated / filterable dashboard pages synchronise their state with URL
 * search params. These helpers provide a consistent way to read typed values
 * from the URL.
 */

/**
 * Read a string search param with a fallback.
 */
export function readSearchParam(getParam: (key: string) => string | null, key: string, fallback: string): string {
	return getParam(key) ?? fallback;
}

/**
 * Read a boolean search param (expects 'true').
 */
export function readSearchParamBool(getParam: (key: string) => string | null, key: string): boolean {
	return getParam(key) === 'true';
}

/**
 * Read an integer search param with a fallback.
 */
export function readSearchParamInt(getParam: (key: string) => string | null, key: string, fallback: number): number {
	const v = getParam(key);
	return v ? parseInt(v, 10) : fallback;
}