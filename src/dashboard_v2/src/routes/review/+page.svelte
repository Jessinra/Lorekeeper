<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { SvelteSet } from 'svelte/reactivity';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Pagination from '$lib/components/table/Pagination.svelte';
	import { REVIEW_STRINGS as S } from '$lib/constants/strings.js';
	import { ICON_CHECK, ICON_X_CLOSE, ICON_TABLE_EMPTY, ICON_SEARCH } from '$lib/constants/icons.js';
	import { fetchSuggestions, batchSuggestions } from '$lib/api/suggestions.js';
	import type { SuggestionRow } from '$lib/api/suggestions.js';
	import { showToast } from '$lib/toast.js';
	import { readSearchParam, readSearchParamInt } from '$lib/url.js';
	import { relativeTime } from '$lib/time.js';

	// ── URL state ──────────────────────────────────────────────────────────────

	type Tab = 'pending' | 'reviewed';

	let activeTab = $state<Tab>(
		(readSearchParam((k) => page.url.searchParams.get(k), 'tab', 'pending') as Tab),
	);
	let searchQuery = $state(readSearchParam((k) => page.url.searchParams.get(k), 'q', ''));
	let currentPage = $state(readSearchParamInt((k) => page.url.searchParams.get(k), 'page', 1));
	const perPage = 50;

	function syncUrl() {
		const params = new URLSearchParams();
		if (activeTab !== 'pending') params.set('tab', activeTab);
		if (searchQuery) params.set('q', searchQuery);
		if (currentPage > 1) params.set('page', String(currentPage));
		// replaceState throws if called before SvelteKit's router is initialized
		// (e.g. during the initial mount $effect). URL sync is cosmetic, so guard
		// it — otherwise a throw here aborts the effect before load() runs and the
		// page hangs on its loading state.
		try {
			replaceState(`?${params.toString()}`, {});
		} catch {
			/* router not ready yet — skip URL sync this pass */
		}
	}

	// ── Sort state ─────────────────────────────────────────────────────────────

	let sortBy = $state('weighted_score');
	let sortDir = $state<'asc' | 'desc'>('desc');
	let sortKey = $derived(
		sortBy === 'weighted_score' && sortDir === 'desc' ? 'score-desc'
		: sortBy === 'weighted_score' && sortDir === 'asc' ? 'score-asc'
		: 'newest',
	);

	// ── Data state ─────────────────────────────────────────────────────────────

	let pendingRows: SuggestionRow[] = $state([]);
	let reviewedRows: SuggestionRow[] = $state([]);
	let total = $state(0);
	let totalPages = $state(1);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Selection state ────────────────────────────────────────────────────────

	let selectedIds = new SvelteSet<string>();
	let activeRows = $derived(activeTab === 'pending' ? pendingRows : reviewedRows);
	let allSelected = $derived(
		activeRows.length > 0 && activeRows.every((r) => selectedIds.has(r.id)),
	);

	// ── Debounce ───────────────────────────────────────────────────────────────

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	// ── Load ───────────────────────────────────────────────────────────────────

	let reloadSignal = $state(0);

	function resetAndLoad() {
		selectedIds.clear();
		currentPage = 1;
		reloadSignal++;
	}

	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		reloadSignal;
		syncUrl();
		load();
	});

	// Clear selection whenever the user navigates to a different page directly
	// (not via resetAndLoad, which already clears it).
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		currentPage;
		selectedIds.clear();
	});

	async function load() {
		loading = true;
		error = null;
		try {
			const offset = (currentPage - 1) * perPage;
			const res = await fetchSuggestions({
				limit: perPage,
				offset,
				sort_by: sortBy,
				sort_dir: sortDir,
				status: activeTab,
			});

			// Client-side filter by search query (title match on source or target)
			const filtered = searchQuery
				? res.items.filter(
						(r) =>
							r.source_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
							r.target_title.toLowerCase().includes(searchQuery.toLowerCase()),
					)
				: res.items;

			if (activeTab === 'pending') {
				pendingRows = filtered;
			} else {
				reviewedRows = filtered;
			}
			total = res.total;
			// Note: search is client-side (current page only); no backend q= param yet.
			totalPages = Math.max(1, Math.ceil(res.total / perPage));
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	// ── Selection handlers ─────────────────────────────────────────────────────

	function toggleRow(id: string) {
		if (selectedIds.has(id)) selectedIds.delete(id);
		else selectedIds.add(id);
	}

	function toggleAll() {
		if (allSelected) {
			selectedIds.clear();
		} else {
			selectedIds.clear();
			for (const r of activeRows) selectedIds.add(r.id);
		}
	}

	// ── Batch actions ──────────────────────────────────────────────────────────

	let acting = $state(false);

	async function batchAction(action: 'accept' | 'reject') {
		if (selectedIds.size === 0 || acting) return;
		acting = true;
		const ids = [...selectedIds];
		try {
			const res = await batchSuggestions(ids, action);
			const count = action === 'accept' ? res.accepted : res.rejected;
			showToast(
				action === 'accept' ? S.acceptSuccess(count) : S.rejectSuccess(count),
				'success',
			);
			if (res.errors.length > 0) {
				console.error('Batch suggestion errors:', res.errors);
				showToast(S.batchError, 'error');
			}
			// Move only successfully acted rows to reviewed tab, carrying the final status
			const successIds = new Set(
				res.results.filter((r) => r.status === 'accepted' || r.status === 'rejected').map((r) => r.id),
			);
			const actedRows = pendingRows.filter((r) => successIds.has(r.id));
			reviewedRows = [
				...actedRows.map((r) => ({ ...r, status: action === 'accept' ? 'accepted' : 'rejected' as SuggestionRow['status'] })),
				...reviewedRows,
			];
			resetAndLoad();
		} catch (e) {
			showToast((e as Error).message, 'error');
		} finally {
			acting = false;
		}
	}

	// ── Tab change ─────────────────────────────────────────────────────────────

	function onTabChange(tab: Tab) {
		activeTab = tab;
		searchQuery = '';
		selectedIds.clear();
		currentPage = 1;
		syncUrl();
		reloadSignal++;
	}

	// ── Search ─────────────────────────────────────────────────────────────────

	function onSearchInput(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		searchQuery = val;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => resetAndLoad(), 280);
	}

	// ── Sort change ────────────────────────────────────────────────────────────

	function onSortChange(e: Event) {
		const val = (e.target as HTMLSelectElement).value;
		if (val === 'score-desc') { sortBy = 'weighted_score'; sortDir = 'desc'; }
		else if (val === 'score-asc') { sortBy = 'weighted_score'; sortDir = 'asc'; }
		else if (val === 'newest') { sortBy = 'created_at'; sortDir = 'desc'; }
		resetAndLoad();
	}


</script>

<PageShell title="Review">
	<!-- Tab bar -->
	<div class="tab-bar" role="tablist" aria-label="Review tabs">
		<button
			type="button"
			role="tab"
			class="tab-btn"
			aria-selected={activeTab === 'pending'}
			onclick={() => onTabChange('pending')}
		>
			{S.tabPending}
		</button>
		<button
			type="button"
			role="tab"
			class="tab-btn"
			aria-selected={activeTab === 'reviewed'}
			onclick={() => onTabChange('reviewed')}
		>
			{S.tabReviewed}
		</button>
	</div>

	<!-- Toolbar -->
	<div class="toolbar" aria-label={S.toolbarAriaLabel}>
		<div class="search-wrapper">
			<Icon path={ICON_SEARCH} size={16} />
			<input
				type="search"
				class="search-input"
				placeholder={S.searchPlaceholder}
				value={searchQuery}
				oninput={onSearchInput}
				aria-label={S.searchPlaceholder}
			/>
		</div>

		{#if activeTab === 'pending'}
			<select
				class="sort-select"
				value={sortKey}
				onchange={onSortChange}
				aria-label="Sort suggestions"
			>
				<option value="score-desc">{S.sortScoreDesc}</option>
				<option value="score-asc">{S.sortScoreAsc}</option>
				<option value="newest">{S.sortNewest}</option>
			</select>
		{/if}

		<div class="spacer"></div>

		{#if activeTab === 'pending'}
			<span class="selection-hint" aria-live="polite">
				{selectedIds.size > 0 ? S.selectedCount(selectedIds.size) : S.noneSelected}
			</span>
			<button
				type="button"
				class="btn-action btn-accept"
				disabled={selectedIds.size === 0 || acting}
				onclick={() => batchAction('accept')}
				aria-label={S.acceptSelected}
			>
				<Icon path={ICON_CHECK} size={14} />
				{S.acceptSelected}
			</button>
			<button
				type="button"
				class="btn-action btn-reject"
				disabled={selectedIds.size === 0 || acting}
				onclick={() => batchAction('reject')}
				aria-label={S.rejectSelected}
			>
				<Icon path={ICON_X_CLOSE} size={14} />
				{S.rejectSelected}
			</button>
		{/if}
	</div>

	<!-- Table -->
	<div class="table-wrap" aria-label={S.tableAriaLabel}>
		{#if loading}
			<div class="skeleton-rows" aria-label={S.skeletonLabel}>
				{#each { length: 8 } as _, i (i)}
					<div class="skeleton-row"></div>
				{/each}
			</div>
		{:else if error}
			<div class="error-banner" role="alert">{error}</div>
		{:else if activeRows.length === 0}
			<div class="empty-state">
				<Icon path={ICON_TABLE_EMPTY} size={40} />
				<p class="empty-title">
					{activeTab === 'pending' ? S.emptyPending : S.emptyReviewed}
				</p>
				<p class="empty-msg">
					{activeTab === 'pending' ? S.emptyPendingMessage : S.emptyReviewedMessage}
				</p>
			</div>
		{:else}
			<table>
				<thead>
					<tr>
						{#if activeTab === 'pending'}
							<th class="col-check">
								<input
									type="checkbox"
									checked={allSelected}
									indeterminate={selectedIds.size > 0 && !allSelected}
									onchange={toggleAll}
									aria-label={S.selectAll}
								/>
							</th>
						{/if}
						<th class="col-source">{S.colSource}</th>
						<th class="col-target">{S.colTarget}</th>
						<th class="col-score">{S.colScore}</th>
						<th class="col-date">{S.colDate}</th>
						{#if activeTab === 'reviewed'}
							<th class="col-status">{S.colStatus}</th>
						{/if}
						</tr>
				</thead>
				<tbody>
					{#each activeRows as row (row.id)}
						<tr
							class:selected={selectedIds.has(row.id)}
							onclick={activeTab === 'pending' ? () => toggleRow(row.id) : undefined}
							tabindex={activeTab === 'pending' ? 0 : undefined}
							onkeydown={activeTab === 'pending'
								? (e: KeyboardEvent) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggleRow(row.id); } }
								: undefined}
							aria-selected={activeTab === 'pending' ? selectedIds.has(row.id) : undefined}
						>
							{#if activeTab === 'pending'}
								<td class="col-check" onclick={(e) => e.stopPropagation()}>
									<input
										type="checkbox"
										checked={selectedIds.has(row.id)}
										onchange={() => toggleRow(row.id)}
										aria-label={`Select ${row.source_title}`}
									/>
								</td>
							{/if}
							<td class="col-source" title={row.source_title}>
								<span class="memory-title">{row.source_title}</span>
							</td>
							<td class="col-target" title={row.target_title}>
								<span class="memory-title">{row.target_title}</span>
							</td>
							<td class="col-score">
								<span class="score-badge">{row.weighted_score.toFixed(2)}</span>
							</td>
							<td class="col-date">{relativeTime(row.created_at)}</td>
							{#if activeTab === 'reviewed'}
								<td class="col-status">
									<span class="status-badge status-{row.status}">
										{row.status === 'accepted' ? S.statusAccepted : S.statusRejected}
									</span>
								</td>
							{/if}
							</tr>
					{/each}
				</tbody>
			</table>

			{#if activeTab === 'pending' && totalPages > 1}
				<Pagination
					totalRows={total}
					bind:page={currentPage}
				/>
			{/if}
		{/if}
	</div>
</PageShell>

<style>
	/* ── Tab bar ─────────────────────────────────────────────────────────────── */

	.tab-bar {
		display: flex;
		gap: var(--space-1);
		margin-bottom: var(--space-4);
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.tab-btn {
		padding: var(--space-2) var(--space-4);
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-muted);
		transition: color 0.15s, border-color 0.15s;
		margin-bottom: -1px;
	}

	.tab-btn[aria-selected='true'] {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
		font-weight: var(--font-weight-semibold);
	}

	/* ── Toolbar ──────────────────────────────────────────────────────────────── */

	.toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-bottom: var(--space-4);
		flex-wrap: wrap;
	}

	.search-wrapper {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-input);
		padding: var(--space-1) var(--space-2);
		min-width: 220px;
	}

	.search-input {
		background: none;
		border: none;
		outline: none;
		font-size: var(--font-size-body);
		color: var(--color-text-primary);
		width: 100%;
	}

	.sort-select {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-input);
		padding: var(--space-1) var(--space-2);
		font-size: var(--font-size-body);
		color: var(--color-text-primary);
		cursor: pointer;
	}

	.spacer {
		flex: 1;
	}

	.selection-hint {
		font-size: var(--font-size-small);
		color: var(--color-text-muted);
	}

	.btn-action {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		border-radius: var(--radius-input);
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		border: var(--border-width) solid transparent;
		transition: opacity 0.15s;
	}

	.btn-action:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-accept {
		background: var(--color-success-bg);
		color: var(--color-success-text);
		border-color: var(--color-success-text);
	}

	.btn-reject {
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border-color: var(--color-danger-text);
	}

	/* ── Table ────────────────────────────────────────────────────────────────── */

	.table-wrap {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-card);
		overflow: hidden;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--font-size-body);
	}

	thead tr {
		background: var(--color-surface-raised, var(--color-surface));
		border-bottom: var(--border-width) solid var(--color-border);
	}

	th {
		padding: var(--space-2) var(--space-3);
		text-align: left;
		font-size: var(--font-size-small);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	tbody tr {
		border-bottom: var(--border-width) solid var(--color-border-subtle, var(--color-border));
		transition: background 0.1s;
		cursor: default;
	}

	tbody tr:last-child {
		border-bottom: none;
	}

	tbody tr:hover {
		background: var(--color-surface-hover, var(--color-surface-raised, var(--color-surface)));
	}

	tbody tr.selected {
		background: var(--color-selection-bg, #eff6ff);
	}

	td {
		padding: var(--space-2) var(--space-3);
		color: var(--color-text-primary);
	}

	.col-check {
		width: 36px;
	}

	.col-source,
	.col-target {
		max-width: 280px;
	}

	.col-score {
		width: 80px;
	}

	.col-date {
		width: 120px;
		color: var(--color-text-muted);
		font-size: var(--font-size-small);
	}

	.col-status {
		width: 100px;
	}

	.status-badge {
		display: inline-block;
		padding: 2px var(--space-2);
		border-radius: var(--radius-input);
		font-size: var(--font-size-small);
		font-weight: var(--font-weight-medium);
	}

	.status-accepted {
		background: var(--color-success-bg);
		color: var(--color-success-text);
	}

	.status-rejected {
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
	}

	.memory-title {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.score-badge {
		display: inline-block;
		font-variant-numeric: tabular-nums;
		font-size: var(--font-size-small);
		color: var(--color-text-muted);
	}

	/* ── Empty state ─────────────────────────────────────────────────────────── */

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-12, 3rem) var(--space-4);
		color: var(--color-text-muted);
		gap: var(--space-2);
	}

	.empty-title {
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-semibold);
		margin: 0;
	}

	.empty-msg {
		font-size: var(--font-size-small);
		margin: 0;
	}

	/* ── Skeleton ─────────────────────────────────────────────────────────────── */

	.skeleton-rows {
		padding: var(--space-2);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.skeleton-row {
		height: 40px;
		border-radius: var(--radius-input);
		background: var(--color-skeleton-bg, #f1f5f9);
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.4; }
	}

	/* ── Error ────────────────────────────────────────────────────────────────── */

	.error-banner {
		padding: var(--space-4);
		color: var(--color-danger, #991b1b);
		font-size: var(--font-size-body);
	}
</style>
