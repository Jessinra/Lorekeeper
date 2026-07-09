import type { Snippet } from 'svelte';

/**
 * Column definition for DataTable.
 */
export interface Column<T> {
	key: string;
	label: string;
	sortable?: boolean;
	sortKey?: string;
	width?: string;
	align?: 'left' | 'center' | 'right';
	render?: (row: T) => string | Snippet;
}

/**
 * Props for the DataTable component.
 */
export interface DataTableProps<T> {
	columns: Column<T>[];
	rows: T[];
	sortColumn?: string | null;
	sortDirection?: 'asc' | 'desc';
	onRowClick?: (row: T) => void;
	selectable?: boolean;
	selectedRows?: Set<string>;
	emptyMessage?: string;
	emptyIcon?: string;
	loading?: boolean;
	children?: Snippet<[T]>;
	pagination?: Snippet;
}