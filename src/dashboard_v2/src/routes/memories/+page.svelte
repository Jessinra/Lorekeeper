<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import DataTable from '$lib/components/table/DataTable.svelte';
	import type { Column } from '$lib/components/table/types.js';
	import FilterChip from '../../components/ui/FilterChip.svelte';
	import ToggleSwitch from '../../components/ui/ToggleSwitch.svelte';
	import Pagination from '$lib/components/table/Pagination.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import MemoryDetailDrawer from '$lib/components/overlays/MemoryDetailDrawer.svelte';
	import type { MemoryData, LinkData, MemoryEditFields } from '$lib/components/overlays/types.js';
	import { MEMORIES_STRINGS as S } from '$lib/constants/strings.js';
	import { ICON_SEARCH, ICON_TABLE_EMPTY } from '$lib/constants/icons.js';
	import type { MemoryRow, MemoryCounts } from '$lib/api/memories.js';
	import { fetchMemories, fetchMemoryCounts, fetchNamespaces, fetchMemoryDetail } from '$lib/api/memories.js';
	import { relativeTime } from '$lib/time.js';
	import { readSearchParam, readSearchParamBool, readSearchParamInt } from '$lib/url.js';

	// ── URL state helpers ──────────────────────────────────────────────────────

	let searchQuery = $state(readSearchParam((k) => page.url.searchParams.get(k), 'q', ''));
	let selectedNamespace = $state(readSearchParam((k) => page.url.searchParams.get(k), 'namespace', ''));
	let showDeleted = $state(readSearchParamBool((k) => page.url.searchParams.get(k), 'include_deleted'));
	let activeFilter = $state(readSearchParam((k) => page.url.searchParams.get(k), 'filter', ''));
	let currentPage = $state(readSearchParamInt((k) => page.url.searchParams.get(k), 'page', 1));
	let perPage = $state(readSearchParamInt((k) => page.url.searchParams.get(k), 'per_page', 50));
	let sortColumn = $state(readSearchParam((k) => page.url.searchParams.get(k), 'sort', 'updated_at'));
	let sortDirection = $state<'asc' | 'desc'>(
		readSearchParam((k) => page.url.searchParams.get(k), 'sort_dir', 'desc') as 'asc' | 'desc',
	);

	// ── Data state ────────────────────────────────────────────────────────────

	let memories: MemoryRow[] = $state([]);
	let totalMemories = $state(0);
	let counts = $state<MemoryCounts | null>(null);
	let namespaces: string[] = $state([]);

	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Drawer state ──────────────────────────────────────────────────────────

	let drawerOpen = $state(false);
	let selectedMemory = $state<MemoryData | null>(null);
	let selectedLinks = $state<LinkData[]>([]);

	// ── Debounce timer ────────────────────────────────────────────────────────

	let searchTimer: ReturnType<typeof setTimeout> | undefined = $state(undefined);

	// ── Sync URL ──────────────────────────────────────────────────────────────

	function syncUrl() {
		const params = new URLSearchParams();
		if (searchQuery) params.set('q', searchQuery);
		if (selectedNamespace) params.set('namespace', selectedNamespace);
		if (showDeleted) params.set('include_deleted', 'true');
		if (activeFilter) params.set('filter', activeFilter);
		if (currentPage > 1) params.set('page', String(currentPage));
		if (perPage !== 50) params.set('per_page', String(perPage));
		if (sortColumn !== 'updated_at') params.set('sort', sortColumn);
		if (sortDirection !== 'desc') params.set('sort_dir', sortDirection);
		replaceState(params.toString(), page.url);
	}

	async function loadMemories() {
		loading = true;
		error = null;
		try {
			const result = await fetchMemories({
				page: currentPage,
				per_page: perPage,
				q: searchQuery,
				namespace: selectedNamespace || undefined,
				include_deleted: showDeleted || undefined,
				filter: activeFilter || undefined,
				sort: sortColumn,
				sort_dir: sortDirection,
			});
			memories = result.memories;
			totalMemories = result.total;
			syncUrl();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load memories';
			memories = [];
			totalMemories = 0;
		} finally {
			loading = false;
		}
	}

	async function loadCounts() {
		try { counts = await fetchMemoryCounts(); } catch { /* non-critical */ }
	}

	async function loadNamespaces() {
		try { namespaces = await fetchNamespaces(); } catch { /* non-critical */ }
	}

	// ── Initial load + react to page changes from Pagination ──────────────

	let firstLoad = true;

	$effect(() => {
		if (firstLoad) {
			firstLoad = false;
			void Promise.all([loadMemories(), loadCounts(), loadNamespaces()]);
		}
	});

	// Separate effect for Pagination/DataTable changes (page, perPage, sort)
	$effect(() => {
		// Access reactive deps to establish tracking
		void [currentPage, perPage, sortColumn, sortDirection];
		if (!firstLoad) {
			void loadMemories();
		}
	});

	// ── Handlers ───────────────────────────────────────────────────────────────

	function onSearchInput(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			searchQuery = value;
			if (activeFilter) activeFilter = '';
			resetAndLoad();
		}, 300);
	}

	function onNamespaceChange(e: Event) {
		selectedNamespace = (e.target as HTMLSelectElement).value;
		resetAndLoad();
	}

	function onToggleDeleted(val: boolean) {
		showDeleted = val;
		resetAndLoad();
	}

	function onFilterClick(filter: string) {
		activeFilter = activeFilter === filter ? '' : filter;
		if (searchQuery) searchQuery = '';
		resetAndLoad();
	}

	// onPageChange handled by Pagination's bind:page + $effect below
	// onPageSizeChange handled by Pagination's bind:pageSize + $effect below

	function onRowClick(row: MemoryRow) {
		selectedMemory = null;
		selectedLinks = [];
		drawerOpen = true;
		// Fetch full detail including links
		void fetchMemoryDetail(row.lore_id).then((detail) => {
			selectedMemory = detail.memory as MemoryData;
			selectedLinks = detail.links as LinkData[];
		});
	}

	async function onDrawerSave(_id: string, _fields: MemoryEditFields): Promise<boolean> {
		return false;
	}

	function onDrawerDelete(_id: string) {
		void loadMemories();
		drawerOpen = false;
	}

	function onDrawerNavigate(_targetId: string) {
		// future: navigate
	}

	function onDrawerClose() {
		drawerOpen = false;
		selectedMemory = null;
	}

	// ── Helpers ────────────────────────────────────────────────────────────────

	const COUNT_KEY_MAP: Record<string, keyof MemoryCounts> = {
		'': 'all',
		needs_review: 'needs_review',
		high_confidence: 'high_confidence',
		stale_30d: 'stale_30d',
	};

	function filterChipCount(key: string): number | undefined {
		return counts?.[COUNT_KEY_MAP[key]];
	}

	// Reset to page 1 and reload — used by all filter/toggle/search handlers
	function resetAndLoad() {
		currentPage = 1;
		void loadMemories();
	}

	// ── Derived ────────────────────────────────────────────────────────────────

	const chips = $derived([
		{ key: '', label: S.filterAll },
		{ key: 'needs_review', label: S.filterNeedsReview },
		{ key: 'high_confidence', label: S.filterHighConfidence },
		{ key: 'stale_30d', label: S.filterStale },
	]);

	const columns: Column<MemoryRow>[] = $derived([
		{
			key: 'title', label: S.colTitle, sortable: true, width: '30%',
			render: (r: MemoryRow) =>
				r.soft_deleted ? `${r.title} (deleted)` : r.title,
		},
		{
			key: 'namespace', label: S.colNamespace, sortable: true, width: '8%',
		},
		{
			key: 'score', label: S.colScore, sortable: true, width: '8%',
			render: (r: MemoryRow) => String(r.score),
		},
		{
			key: 'confidence', label: S.colConfidence, sortable: true, width: '8%',
		},
		{
			key: 'usage_count', label: S.colUsage, sortable: true, width: '6%',
		},
		{
			key: 'links_count', label: S.colLinks, width: '6%',
			render: (r: MemoryRow) => r.links_count > 0 ? String(r.links_count) : '\u2014',
		},
		{
			key: 'updated_at', label: S.colUpdated, sortable: true, width: '12%',
			render: (r: MemoryRow) => relativeTime(r.updated_at),
		},
	]);

	// Map MemoryRow to { id?: unknown } for DataTable compat
	const tableRows = $derived(
		memories.map((r) => ({ ...r, id: r.lore_id })),
	);
</script>

<PageShell title="Memories">
	<!-- Toolbar -->
	<div class="toolbar" aria-label={S.toolbarGroupAriaLabel}>
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
		<select
			class="ns-select"
			value={selectedNamespace}
			onchange={onNamespaceChange}
			aria-label={S.namespaceAriaLabel}
		>
			<option value="">{S.namespaceAll}</option>
			{#each namespaces as ns (ns)}
				<option value={ns}>{ns}</option>
			{/each}
		</select>
		<ToggleSwitch
			checked={showDeleted}
			onChange={onToggleDeleted}
			label={S.showDeletedLabel}
		/>
		<button type="button" class="btn-new" disabled aria-label={S.newMemoryButton}>
			{S.newMemoryButton}
		</button>
	</div>

	<!-- Filter chips -->
	<div class="chip-row" role="group" aria-label={S.filterGroupAriaLabel}>
		{#each chips as chip (chip.key)}
			<FilterChip
				label={chip.label}
				active={activeFilter === chip.key}
				count={filterChipCount(chip.key)}
				onToggle={() => onFilterClick(chip.key)}
			/>
		{/each}
	</div>

	<!-- Data table -->
	<DataTable
		columns={columns as Column<{ id?: unknown }>[]}
		rows={tableRows}
		loading={loading}
		bind:sortColumn
		bind:sortDirection
		onRowClick={(row: { id?: unknown }) => onRowClick(row as unknown as MemoryRow)}
		emptyMessage={S.emptyMessage}
		emptyIcon={ICON_TABLE_EMPTY}
	>
		{#snippet pagination()}
			<div class="pagination-bar">
				<Pagination totalRows={totalMemories} bind:page={currentPage} bind:pageSize={perPage} showPageSize />
			</div>
		{/snippet}
	</DataTable>

	{#if error}
		<div class="error-banner" role="alert">{error}</div>
	{/if}
</PageShell>

<MemoryDetailDrawer
	open={drawerOpen}
	memory={selectedMemory}
	links={selectedLinks}
	onClose={onDrawerClose}
	onSave={onDrawerSave}
	onDelete={onDrawerDelete}
	onNavigate={onDrawerNavigate}
/>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		flex-wrap: wrap;
	}
	.search-wrapper {
		flex: 1;
		min-width: 200px;
		position: relative;
	}
	.search-input {
		width: 100%;
		padding: var(--space-2) var(--space-3) var(--space-2) var(--space-8);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: var(--font-size-body);
		background: var(--color-surface);
		color: var(--color-text-primary);
		outline: none;
	}
	.search-input:focus {
		border-color: var(--color-brand);
		box-shadow: 0 0 0 2px var(--color-brand-tint);
	}
	.ns-select {
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: var(--font-size-body);
		background: var(--color-surface);
		color: var(--color-text-primary);
		min-width: 100px;
	}
	.btn-new {
		padding: var(--space-2) var(--space-4);
		background: var(--color-brand);
		color: var(--color-text-on-filled);
		border: none;
		border-radius: var(--radius-input);
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-semibold);
		cursor: pointer;
	}
	.btn-new:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.chip-row {
		display: flex;
		gap: var(--space-1-5);
		padding: 0 var(--space-6) var(--space-3);
		flex-wrap: wrap;
	}
	.pagination-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-2);
	}
	.error-banner {
		margin: var(--space-3) var(--space-6);
		padding: var(--space-3) var(--space-4);
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border-radius: var(--radius-card);
		font-size: var(--font-size-body);
	}
</style>