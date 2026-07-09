import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import DataTable from '$lib/components/table/DataTable.svelte';
import type { Column } from '$lib/components/table/types.js';

// ─── Fixtures ────────────────────────────────────────────────────────────────

interface TestRow {
	id: number;
	title: string;
	score: number;
}

const columns: Column<TestRow>[] = [
	{ key: 'title', label: 'Title', sortable: true },
	{ key: 'score', label: 'Score', sortable: true, align: 'right' }
];

const rows: TestRow[] = [
	{ id: 1, title: 'Zebra', score: 10 },
	{ id: 2, title: 'Apple', score: 5 },
	{ id: 3, title: 'Banana', score: 20 }
];

// ─── Rendering ───────────────────────────────────────────────────────────────

describe('DataTable — rendering', () => {
	it('renders column headers', () => {
		const { getByText } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		expect(getByText('Title')).toBeInTheDocument();
		expect(getByText('Score')).toBeInTheDocument();
	});

	it('renders row data', () => {
		const { getByText } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		expect(getByText('Zebra')).toBeInTheDocument();
		expect(getByText('Apple')).toBeInTheDocument();
		expect(getByText('Banana')).toBeInTheDocument();
		expect(getByText('10')).toBeInTheDocument();
		expect(getByText('5')).toBeInTheDocument();
		expect(getByText('20')).toBeInTheDocument();
	});

	it('has role="table"', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		expect(container.querySelector('.data-table')).toHaveAttribute('role', 'table');
	});

	it('renders empty state when rows is empty', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows: [], emptyMessage: 'No items' }
		});
		expect(container.querySelector('.empty-state')).toBeInTheDocument();
		expect(container.textContent).toContain('No items');
	});

	it('renders custom empty message', () => {
		const { getByText } = render(DataTable<TestRow>, {
			props: { columns, rows: [], emptyMessage: 'Custom empty message' }
		});
		expect(getByText('Custom empty message')).toBeInTheDocument();
	});

	it('renders loading skeleton when loading is true', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, loading: true }
		});
		expect(container.querySelector('.skeleton-line')).toBeInTheDocument();
		expect(container.querySelector('.data-table')).toHaveAttribute('aria-busy', 'true');
	});

	it('does not show empty state when loading and rows empty', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows: [], loading: true }
		});
		expect(container.querySelector('.skeleton-line')).toBeInTheDocument();
		expect(container.querySelector('.empty-state')).not.toBeInTheDocument();
	});
});

// ─── Sortable columns ────────────────────────────────────────────────────────

describe('DataTable — sortable columns', () => {
	it('renders sort indicator on active column', async () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, sortColumn: 'score', sortDirection: 'desc' }
		});
		const headerCells = container.querySelectorAll('th');
		// Score column should have sort indicator
		const scoreHeader = headerCells[1];
		expect(scoreHeader.textContent).toContain('↓');
		expect(scoreHeader).toHaveClass('active');
	});

	it('clicking sortable column sets sort column', async () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		const headerCells = container.querySelectorAll('th');
		await fireEvent.click(headerCells[0]); // Title column
		expect(headerCells[0]).toHaveClass('active');
		// Title is text → default asc
		expect(headerCells[0].textContent).toContain('↑');
	});

	it('clicking same column again toggles direction', async () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, sortColumn: 'title', sortDirection: 'asc' }
		});
		const headerCells = container.querySelectorAll('th');
		await fireEvent.click(headerCells[0]); // Title column
		expect(headerCells[0].textContent).toContain('↓');
	});

	it('numeric column defaults to desc on first click', async () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		const headerCells = container.querySelectorAll('th');
		await fireEvent.click(headerCells[1]); // Score column (numeric)
		expect(headerCells[1].textContent).toContain('↓');
	});

	it('text column defaults to asc on first click', async () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		const headerCells = container.querySelectorAll('th');
		await fireEvent.click(headerCells[0]); // Title column (text)
		expect(headerCells[0].textContent).toContain('↑');
	});

	it('non-sortable column does not respond to click', async () => {
		const nonSortCols: Column<TestRow>[] = [
			{ key: 'title', label: 'Title' },
			{ key: 'score', label: 'Score', sortable: true }
		];
		const { container } = render(DataTable<TestRow>, {
			props: { columns: nonSortCols, rows }
		});
		const headerCells = container.querySelectorAll('th');
		// Non-sortable Title column should not get active class on click
		await fireEvent.click(headerCells[0]);
		expect(headerCells[0]).not.toHaveClass('active');
	});

	it('sortable headers have aria-sort attribute', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, sortColumn: 'title', sortDirection: 'asc' }
		});
		const headerCells = container.querySelectorAll('th');
		expect(headerCells[0]).toHaveAttribute('aria-sort', 'ascending');
		expect(headerCells[1]).toHaveAttribute('aria-sort', 'none');
	});
});

// ─── Row click ───────────────────────────────────────────────────────────────

describe('DataTable — row click', () => {
	it('calls onRowClick with the clicked row', async () => {
		const onRowClick = vi.fn();
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, onRowClick }
		});
		const row = container.querySelectorAll('tbody tr')[0];
		await fireEvent.click(row);
		expect(onRowClick).toHaveBeenCalledWith(rows[0]);
	});

	it('does not call onRowClick when not provided', async () => {
		const onRowClick = vi.fn();
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		const row = container.querySelectorAll('tbody tr')[0];
		await fireEvent.click(row);
		expect(onRowClick).not.toHaveBeenCalled();
	});

	it('rows are clickable when onRowClick is provided', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, onRowClick: vi.fn() }
		});
		const row = container.querySelectorAll('tbody tr')[0];
		expect(row).toHaveClass('clickable');
	});

	it('rows are not clickable when onRowClick is not provided', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		const row = container.querySelectorAll('tbody tr')[0];
		expect(row).not.toHaveClass('clickable');
	});
});

// ─── Selectable ──────────────────────────────────────────────────────────────

describe('DataTable — selectable column', () => {
	it('renders checkbox column shell when selectable=true', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, selectable: true }
		});
		expect(container.querySelectorAll('.col-checkbox').length).toBeGreaterThan(0);
	});

	it('does not render checkbox column when selectable=false', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, selectable: false }
		});
		expect(container.querySelector('.col-checkbox')).not.toBeInTheDocument();
	});

	it('checkbox click does not trigger row click', async () => {
		const onRowClick = vi.fn();
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows, selectable: true, onRowClick }
		});
		const checkbox = container.querySelectorAll('.col-checkbox')[1]; // first data row's checkbox
		await fireEvent.click(checkbox);
		expect(onRowClick).not.toHaveBeenCalled();
	});
});

// ─── Custom render ───────────────────────────────────────────────────────────

describe('DataTable — custom render', () => {
	it('renders custom cell content via render function', () => {
		const customCols: Column<TestRow>[] = [
			{ key: 'title', label: 'Title' },
			{
				key: 'score',
				label: 'Score',
				render: (row: TestRow) => `⭐ ${row.score}`
			}
		];
		const { getByText } = render(DataTable<TestRow>, {
			props: { columns: customCols, rows }
		});
		expect(getByText('⭐ 10')).toBeInTheDocument();
		expect(getByText('⭐ 5')).toBeInTheDocument();
		expect(getByText('⭐ 20')).toBeInTheDocument();
	});
});

// ─── Pagination slot ─────────────────────────────────────────────────────────

describe('DataTable — pagination slot', () => {
	it('renders without error when pagination is not provided', () => {
		const { container } = render(DataTable<TestRow>, {
			props: { columns, rows }
		});
		// No pagination section rendered
		expect(container.querySelector('.pagination')).not.toBeInTheDocument();
	});
});