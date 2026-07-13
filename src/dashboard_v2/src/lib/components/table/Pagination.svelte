<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';
	import { PAGINATION_STRINGS } from '$lib/constants/strings.js';
	import { ICON_ARROW_RIGHT } from '$lib/constants/icons.js';

	interface Props {
		totalRows: number;
		page?: number;
		pageSize?: number;
		showPageSize?: boolean;
	}

	let {
		totalRows,
		page = $bindable(1),
		pageSize = $bindable(50),
		showPageSize = false
	}: Props = $props();

	let totalPages = $derived(Math.max(1, Math.ceil(totalRows / pageSize)));
	let startRow = $derived(totalRows === 0 ? 0 : (page - 1) * pageSize + 1);
	let endRow = $derived(Math.min(page * pageSize, totalRows));
	let isFirstPage = $derived(page <= 1);
	let isLastPage = $derived(page >= totalPages);

	// Clamp page when totalRows shrinks (e.g. after filtering)
	$effect(() => {
		if (page > totalPages) {
			page = totalPages;
		}
	});

	function goPrev() {
		if (page > 1) page--;
	}

	function goNext() {
		if (page < totalPages) page++;
	}

	function rangeLabel(): string {
		return PAGINATION_STRINGS.rangeLabel
			.replace('{start}', String(startRow))
			.replace('{end}', String(endRow))
			.replace('{total}', String(totalRows));
	}

	function pageIndicator(): string {
		return PAGINATION_STRINGS.pageIndicator
			.replace('{page}', String(page))
			.replace('{pages}', String(totalPages));
	}
</script>

<div class="pagination" role="navigation" aria-label={PAGINATION_STRINGS.navAriaLabel}>
	<span class="range-label">
		{rangeLabel()}
	</span>

	<div class="controls">
		<button
			class="nav-btn nav-btn-prev"
			type="button"
			aria-label={PAGINATION_STRINGS.prevAriaLabel}
			disabled={isFirstPage}
			onclick={goPrev}
		>
			<Icon path={ICON_ARROW_RIGHT} size={16} />
		</button>

		<span class="page-indicator" aria-live="polite">
			{pageIndicator()}
		</span>

		<button
			class="nav-btn"
			type="button"
			aria-label={PAGINATION_STRINGS.nextAriaLabel}
			disabled={isLastPage}
			onclick={goNext}
		>
			<Icon path={ICON_ARROW_RIGHT} size={16} />
		</button>
	</div>

	{#if showPageSize}
		<select
			class="page-size-select"
			bind:value={pageSize}
			aria-label={PAGINATION_STRINGS.pageSizeLabel}
		>
			<option value={25}>{PAGINATION_STRINGS.pageSize25}</option>
			<option value={50}>{PAGINATION_STRINGS.pageSize50}</option>
			<option value={100}>{PAGINATION_STRINGS.pageSize100}</option>
		</select>
	{/if}
</div>

<style>
	.pagination {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--pagination-bar-padding);
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
		gap: var(--pagination-controls-gap);
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: var(--pagination-btn-size);
		height: var(--pagination-btn-size);
		padding: 0;
		background: transparent;
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-icon);
		color: var(--color-text-muted);
		cursor: pointer;
		transition: background var(--pagination-transition-duration), color var(--pagination-transition-duration);
	}

	.nav-btn:hover:not(:disabled) {
		background: var(--color-hover-bg);
		color: var(--color-text-primary);
	}

	.nav-btn:disabled {
		opacity: var(--pagination-disabled-opacity);
		cursor: not-allowed;
	}

	.nav-btn-prev {
		transform: scaleX(-1);
	}

	.page-indicator {
		white-space: nowrap;
		min-width: var(--pagination-page-min-width);
		text-align: center;
	}

	.page-size-select {
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: var(--font-size-sub);
		background: var(--color-surface);
		color: var(--color-text-primary);
	}
</style>