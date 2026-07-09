<script lang="ts" generics="T extends { id?: unknown }">
	import type { Snippet } from 'svelte';
	import type { Column } from '$lib/components/table/types.js';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import { isNumericColumn, toggleDirection } from '$lib/sort.js';

	// ─── Props ────────────────────────────────────────────────────────────────

	let {
		columns,
		rows,
		sortColumn = $bindable(null),
		sortDirection = $bindable('desc'),
		onRowClick = undefined,
		selectable = false,
		selectedRows = new Set<string>(),
		emptyMessage = 'No rows to display',
		emptyIcon = 'M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4',
		loading = false,
		children = undefined,
		pagination = undefined
	}: {
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
	} = $props();

	// ─── Sort handling ────────────────────────────────────────────────────────

	function handleHeaderClick(col: Column<T>): void {
		if (!col.sortable) return;
		if (sortColumn === col.key) {
			sortDirection = toggleDirection(sortDirection);
		} else {
			sortColumn = col.key;
			sortDirection = isNumericColumn(col.key) ? 'desc' : 'asc';
		}
	}

	function isActive(col: Column<T>): boolean {
		return sortColumn === col.key;
	}

	function getSortIndicator(col: Column<T>): string {
		if (!isActive(col)) return '';
		return sortDirection === 'asc' ? '↑' : '↓';
	}

	function getCellValue(row: T, col: Column<T>): string | Snippet {
		if (col.render) {
			return col.render(row);
		}
		return String((row as Record<string, unknown>)[col.key] ?? '');
	}
</script>

{#if loading}
	<div class="data-table" role="table" aria-busy="true">
		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						{#if selectable}
							<th class="col-checkbox" aria-hidden="true"></th>
						{/if}
						{#each columns as col}
							<th class="th-skeleton" style={col.width ? 'width: ' + col.width : ''} aria-hidden="true">
								<span class="skeleton-line">&nbsp;</span>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each [1, 2, 3, 4, 5] as _i}
						<tr class="skeleton-row" aria-hidden="true">
							{#if selectable}
								<td class="col-checkbox"></td>
							{/if}
							{#each columns as col}
								<td style={col.width ? 'width: ' + col.width : ''}>
									<span class="skeleton-line">&nbsp;</span>
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{:else if rows.length === 0}
	<EmptyState icon={emptyIcon} message={emptyMessage} />
{:else}
	<div class="data-table" role="table">
		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						{#if selectable}
							<th class="col-checkbox" aria-hidden="true">
								<!-- checkbox placeholder — full bulk-select wiring in LKPR-131 -->
							</th>
						{/if}
						{#each columns as col (col.key)}
							<th
								class:sortable={col.sortable}
								class:active={isActive(col)}
								style={col.width ? 'width: ' + col.width : ''}
								style:--col-align={col.align ?? 'left'}
								role="columnheader"
								aria-sort={isActive(col) ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
								onclick={col.sortable ? () => handleHeaderClick(col) : undefined}
								tabindex={col.sortable ? 0 : -1}
								onkeydown={col.sortable ? (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleHeaderClick(col); } } : undefined}
							>
								{col.label}
								{#if col.sortable}
									<span class="sort-indicator">{getSortIndicator(col)}</span>
								{/if}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each rows as row (row.id !== undefined ? row.id : row)}
						{@const cellValues = columns.map((col) => getCellValue(row, col))}
						<tr
							class:clickable={onRowClick !== undefined}
							onclick={onRowClick ? () => onRowClick(row) : undefined}
						>
							{#if selectable}
								<td class="col-checkbox" onclick={(e: MouseEvent) => e.stopPropagation()}>
									<!-- checkbox shell — selection logic in LKPR-131 -->
								</td>
							{/if}
							{#each columns as col, i (col.key)}
								{@const cell = cellValues[i]}
								<td
									style:--col-align={col.align ?? 'left'}
									style={col.width ? 'width: ' + col.width : ''}
								>
									{#if typeof cell === 'string'}
										{cell}
									{:else if cell !== undefined}
										{@render cell()}
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if pagination}
			{@render pagination()}
		{/if}
	</div>
{/if}

<style>
	.data-table {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.table-wrapper {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	th {
		position: sticky;
		top: 0;
		background: var(--color-surface);
		padding: 10px 12px;
		font-size: var(--font-size-micro);
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-align: var(--col-align, left);
		white-space: nowrap;
		border-bottom: var(--border-width) solid var(--color-border);
		user-select: none;
		transition: color 100ms;
	}

	th.sortable {
		cursor: pointer;
	}

	th.sortable:hover {
		color: var(--color-text-primary);
	}

	th.active {
		color: var(--color-brand);
	}

	.sort-indicator {
		margin-left: 4px;
		font-size: var(--font-size-micro);
		display: inline-block;
		vertical-align: middle;
	}

	td {
		padding: 8px 12px;
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		text-align: var(--col-align, left);
		border-bottom: var(--border-width) solid var(--color-divider);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	tr:last-child td {
		border-bottom: none;
	}

	tr.clickable {
		cursor: pointer;
		transition: background 80ms;
	}

	tr.clickable:hover {
		background: var(--color-brand-tint);
		opacity: 0.88;
	}

	/* Checkbox column */
	.col-checkbox {
		width: 36px;
		min-width: 36px;
		padding: 8px 4px;
		text-align: center;
	}

	/* Loading skeleton */
	.skeleton-line {
		display: inline-block;
		height: 12px;
		background: var(--color-border);
		border-radius: 4px;
		width: 70%;
		animation: skeleton-pulse 1.5s ease-in-out infinite;
	}

	@keyframes skeleton-pulse {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 0.8; }
	}
</style>