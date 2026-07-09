import { describe, it, expect } from 'vitest';
import { isNumericColumn, toggleDirection, sortRows } from '$lib/sort.js';

// ─── isNumericColumn ─────────────────────────────────────────────────────────

describe('isNumericColumn', () => {
	it('returns true for known numeric keys', () => {
		expect(isNumericColumn('score')).toBe(true);
		expect(isNumericColumn('uses')).toBe(true);
		expect(isNumericColumn('confidence')).toBe(true);
		expect(isNumericColumn('count')).toBe(true);
		expect(isNumericColumn('updated')).toBe(true);
		expect(isNumericColumn('created')).toBe(true);
	});

	it('returns false for text keys', () => {
		expect(isNumericColumn('title')).toBe(false);
		expect(isNumericColumn('namespace')).toBe(false);
		expect(isNumericColumn('relation')).toBe(false);
		expect(isNumericColumn('label')).toBe(false);
	});
});

// ─── toggleDirection ─────────────────────────────────────────────────────────

describe('toggleDirection', () => {
	it('toggles asc to desc', () => {
		expect(toggleDirection('asc')).toBe('desc');
	});

	it('toggles desc to asc', () => {
		expect(toggleDirection('desc')).toBe('asc');
	});
});

// ─── sortRows ────────────────────────────────────────────────────────────────

interface TestRow {
	id: number;
	title: string;
	score: number;
}

const rows: TestRow[] = [
	{ id: 1, title: 'Zebra', score: 10 },
	{ id: 2, title: 'apple', score: 5 },
	{ id: 3, title: 'Apple', score: 5 },
	{ id: 4, title: 'Banana', score: 20 }
];

describe('sortRows — text columns', () => {
	it('sorts text ascending (case-insensitive)', () => {
		const result = sortRows(rows, 'title', 'asc', false);
		expect(result[0].title).toBe('apple');
		expect(result[1].title).toBe('Apple');
		expect(result[2].title).toBe('Banana');
		expect(result[3].title).toBe('Zebra');
	});

	it('sorts text descending', () => {
		const result = sortRows(rows, 'title', 'desc', false);
		expect(result[0].title).toBe('Zebra');
		// Case-insensitive: 'apple' and 'Apple' are equal, stable sort preserves order
		expect(result[3].title).toBe('Apple');
	});

	it('does not mutate the original array', () => {
		const original = [...rows];
		sortRows(rows, 'title', 'asc', false);
		expect(rows).toEqual(original);
	});
});

describe('sortRows — numeric columns', () => {
	it('sorts numeric ascending', () => {
		const result = sortRows(rows, 'score', 'asc', true);
		expect(result[0].score).toBe(5);
		expect(result[1].score).toBe(5);
		expect(result[2].score).toBe(10);
		expect(result[3].score).toBe(20);
	});

	it('sorts numeric descending', () => {
		const result = sortRows(rows, 'score', 'desc', true);
		expect(result[0].score).toBe(20);
		expect(result[3].score).toBe(5);
	});
});

describe('sortRows — edge cases', () => {
	it('handles empty array', () => {
		expect(sortRows([], 'title', 'asc', false)).toEqual([]);
	});

	it('handles null/undefined values (sorts to end)', () => {
		const sparse: TestRow[] = [
			{ id: 1, title: 'A', score: 10 },
			{ id: 2, title: '', score: 5 },
			{ id: 3, title: null as unknown as string, score: 5 }
		];
		const result = sortRows(sparse, 'title', 'asc', false);
		// null and '' should not crash — null/undefined coerces to ''
		expect(result).toHaveLength(3);
	});

	it('handles NaN numeric values (sorts to end)', () => {
		const nanRows: TestRow[] = [
			{ id: 1, title: 'A', score: 10 },
			{ id: 2, title: 'B', score: NaN },
			{ id: 3, title: 'C', score: 5 }
		];
		const result = sortRows(nanRows, 'score', 'asc', true);
		expect(result[0].score).toBe(5);
		expect(result[1].score).toBe(10);
		// NaN sorts to end
		expect(isNaN(result[2].score as number)).toBe(true);
	});

	it('handles single row', () => {
		const single = [{ id: 1, title: 'Only', score: 1 }];
		expect(sortRows(single, 'title', 'asc', false)).toEqual(single);
	});
});