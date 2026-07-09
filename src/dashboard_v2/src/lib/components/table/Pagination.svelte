<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		totalRows: number;
		page?: number;
		pageSize?: number;
		onPageChange?: (page: number) => void;
	}

	let {
		totalRows,
		page = $bindable(1),
		pageSize = 50,
		onPageChange = undefined
	}: Props = $props();

	let totalPages = $derived(Math.max(1, Math.ceil(totalRows / pageSize)));
	let startRow = $derived(totalRows === 0 ? 0 : (page - 1) * pageSize + 1);
	let endRow = $derived(Math.min(page * pageSize, totalRows));
	let isFirstPage = $derived(page <= 1);
	let isLastPage = $derived(page >= totalPages);

	function goPrev() {
		if (page > 1) {
			page--;
			onPageChange?.(page);
		}
	}

	function goNext() {
		if (page < totalPages) {
			page++;
			onPageChange?.(page);
		}
	}
</script>

<div class="pagination" role="navigation" aria-label="Table pagination">
	<span class="range-label">
		Showing {startRow}–{endRow} of {totalRows}
	</span>

	<div class="controls">
		<button
			class="nav-btn"
			type="button"
			aria-label="Previous page"
			disabled={isFirstPage}
			onclick={goPrev}
		>
			<Icon path="M15 18l-6-6 6-6" size={16} />
		</button>

		<span class="page-indicator" aria-live="polite">
			Page {page} of {totalPages}
		</span>

		<button
			class="nav-btn"
			type="button"
			aria-label="Next page"
			disabled={isLastPage}
			onclick={goNext}
		>
			<Icon path="M9 18l6-6-6-6" size={16} />
		</button>
	</div>
</div>

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px;
		border-top: var(--border-width) solid var(--color-border);
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		user-select: none;
	}

	.range-label {
		white-space: nowrap;
	}

	.controls {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		padding: 0;
		background: transparent;
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-icon);
		color: var(--color-text-muted);
		cursor: pointer;
		transition: background 100ms, color 100ms;
	}

	.nav-btn:hover:not(:disabled) {
		background: var(--color-hover-bg);
		color: var(--color-text-primary);
	}

	.nav-btn:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.page-indicator {
		white-space: nowrap;
		min-width: 72px;
		text-align: center;
	}
</style>