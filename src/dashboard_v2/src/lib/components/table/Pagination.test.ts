import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import Pagination from '$lib/components/table/Pagination.svelte';

describe('Pagination — rendering', () => {
	it('renders range label with correct values', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50 }
		});
		expect(container.textContent).toContain('Showing 1–50 of 100');
	});

	it('renders correct range for last page', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 51, page: 2, pageSize: 50 }
		});
		expect(container.textContent).toContain('Showing 51–51 of 51');
	});

	it('renders correct range for single page', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 25, page: 1, pageSize: 50 }
		});
		expect(container.textContent).toContain('Showing 1–25 of 25');
	});

	it('shows 0–0 of 0 when totalRows is 0', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 0, page: 1, pageSize: 50 }
		});
		expect(container.textContent).toContain('Showing 0–0 of 0');
	});

	it('renders page indicator', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 100, page: 2, pageSize: 50 }
		});
		expect(container.textContent).toContain('Page 2 of 2');
	});

	it('has role="navigation" and aria-label', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50 }
		});
		const nav = container.querySelector('.pagination');
		expect(nav).toHaveAttribute('role', 'navigation');
		expect(nav).toHaveAttribute('aria-label', 'Table pagination');
	});
});

describe('Pagination — prev/next buttons', () => {
	it('renders prev and next buttons', () => {
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 2, pageSize: 50 }
		});
		expect(getByLabelText('Previous page')).toBeInTheDocument();
		expect(getByLabelText('Next page')).toBeInTheDocument();
	});

	it('disables prev on first page', () => {
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50 }
		});
		expect(getByLabelText('Previous page')).toBeDisabled();
	});

	it('disables next on last page', () => {
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 2, pageSize: 50 }
		});
		expect(getByLabelText('Next page')).toBeDisabled();
	});

	it('both buttons disabled on single page', () => {
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 25, page: 1, pageSize: 50 }
		});
		expect(getByLabelText('Previous page')).toBeDisabled();
		expect(getByLabelText('Next page')).toBeDisabled();
	});

	it('both buttons disabled on 0 rows', () => {
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 0, page: 1, pageSize: 50 }
		});
		expect(getByLabelText('Previous page')).toBeDisabled();
		expect(getByLabelText('Next page')).toBeDisabled();
	});
});

describe('Pagination — navigation', () => {
	it('calls onPageChange with page 2 when next is clicked', async () => {
		const onPageChange = vi.fn();
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50, onPageChange }
		});
		await fireEvent.click(getByLabelText('Next page'));
		expect(onPageChange).toHaveBeenCalledWith(2);
	});

	it('calls onPageChange with page 1 when prev is clicked', async () => {
		const onPageChange = vi.fn();
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 2, pageSize: 50, onPageChange }
		});
		await fireEvent.click(getByLabelText('Previous page'));
		expect(onPageChange).toHaveBeenCalledWith(1);
	});

	it('does not call onPageChange when prev is clicked on first page', async () => {
		const onPageChange = vi.fn();
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50, onPageChange }
		});
		await fireEvent.click(getByLabelText('Previous page'));
		expect(onPageChange).not.toHaveBeenCalled();
	});

	it('does not call onPageChange when next is clicked on last page', async () => {
		const onPageChange = vi.fn();
		const { getByLabelText } = render(Pagination, {
			props: { totalRows: 100, page: 2, pageSize: 50, onPageChange }
		});
		await fireEvent.click(getByLabelText('Next page'));
		expect(onPageChange).not.toHaveBeenCalled();
	});

	it('page indicator has aria-live="polite"', () => {
		const { container } = render(Pagination, {
			props: { totalRows: 100, page: 1, pageSize: 50 }
		});
		const indicator = container.querySelector('.page-indicator');
		expect(indicator).toHaveAttribute('aria-live', 'polite');
	});
});