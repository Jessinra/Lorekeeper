<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import DataTable from '$lib/components/table/DataTable.svelte';
	import type { Column } from '$lib/components/table/types.js';
	import FilterChip from '../../components/ui/FilterChip.svelte';
	import ToggleSwitch from '../../components/ui/ToggleSwitch.svelte';
	import Pagination from '$lib/components/table/Pagination.svelte';
	import MemoryDetailDrawer from '$lib/components/overlays/MemoryDetailDrawer.svelte';
	import type { MemoryData, LinkData, MemoryEditFields } from '$lib/components/overlays/types.js';
	import { MEMORIES_STRINGS as S } from '$lib/constants/strings.js';
	import { ICON_SEARCH, ICON_TABLE_EMPTY } from '$lib/constants/icons.js';
	import type { MemoryRow, MemoryCounts } from '$lib/api/memories.js';
	import { fetchMemories, fetchMemoryCounts, fetchNamespaces, fetchMemoryDetail } from '$lib/api/memories.js';

	// ── URL state helpers ──────────────────────────────────────────────────────

	function readUrlParam(key: string, fallback: string): string {
		return page.url.searchParams.get(key) ?? fallback;
	}
	function readUrlParamBool(key: string): boolean {
		return page.url.searchParams.get(key) === 'true';
	}
	function readUrlParamInt(key: string, fallback: number): number {
		const v = page.url.searchParams.get(key);
		return v ? parseInt(v, 10) : fallback;
	}

	// ── Reactive state from URL ───────────────────────────────────────────────

	let searchQuery = $state(readUrlParam('q', ''));
	let selectedNamespace = $state(readUrlParam('namespace', ''));
	let showDeleted = $state(readUrlParamBool('include_deleted'));
	let activeFilter = $state(readUrlParam('filter', ''));
	let currentPage = $state(readUrlParamInt('page', 1));
	let perPage = $state(readUrlParamInt('per_page', 50));
	let sortColumn = $state(readUrlParam('sort', 'updated_at'));
	let sortDirection = $state<'asc' | 'desc'>(
		readUrlParam('sort_dir', 'desc') as 'asc' | 'desc',
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

	// Separate effect for Pagination page changes (prev/next via bind:page)
	$effect(() => {
		if (currentPage && !firstLoad) {
			void loadMemories();
		}
	});

	// ── Handlers ───────────────────────────────────────────────────────────────

	function onSearchInput(e: Event) {
		const value = (e.target as HTMLInputElement).value;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			searchQuery = value;
			currentPage = 1;
			if (activeFilter) activeFilter = '';
			void loadMemories();
		}, 300);
	}

	function onNamespaceChange(e: Event) {
		selectedNamespace = (e.target as HTMLSelectElement).value;
		currentPage = 1;
		void loadMemories();
	}

	function onToggleDeleted(val: boolean) {
		showDeleted = val;
		currentPage = 1;
		void loadMemories();
	}

	function onFilterClick(filter: string) {
		activeFilter = activeFilter === filter ? '' : filter;
		if (searchQuery) searchQuery = '';
		currentPage = 1;
		void loadMemories();
	}

	// onPageChange handled by Pagination's bind:page + $effect below

	function onPageSizeChange(e: Event) {
		perPage = parseInt((e.target as HTMLSelectElement).value, 10);
		currentPage = 1;
		void loadMemories();
	}

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

	function relativeTime(iso: string): string {
		const d = new Date(iso);
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'now';
		if (diffMin < 60) return `${diffMin}m ago`;
		const diffHrs = Math.floor(diffMin / 60);
		if (diffHrs < 24) return `${diffHrs}h ago`;
		const diffDays = Math.floor(diffHrs / 24);
		if (diffDays < 7) return `${diffDays}d ago`;
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function filterChipCount(key: string): number | undefined {
		if (!counts) return undefined;
		if (key === '') return counts.all;
		if (key === 'needs_review') return counts.needs_review;
		if (key === 'high_confidence') return counts.high_confidence;
		if (key === 'stale_30d') return counts.stale_30d;
		return undefined;
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
	<div class="toolbar">
		<div class="search-wrapper">
			<span class="search-icon" aria-hidden="true" style="width:16px;height:16px;">{@html ICON_SEARCH}</span>
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
			aria-label="Filter by namespace"
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
	<div class="chip-row" role="group" aria-label="Memory filter presets">
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
				<Pagination totalRows={totalMemories} bind:page={currentPage} />
				<select
					class="page-size-select"
					value={perPage}
					onchange={onPageSizeChange}
					aria-label="Page size"
				>
					<option value={25}>25</option>
					<option value={50}>50</option>
					<option value={100}>100</option>
				</select>
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
		gap: 12px;
		padding: 16px 24px;
		flex-wrap: wrap;
	}
	.search-wrapper {
		flex: 1;
		min-width: 200px;
		position: relative;
	}
	.search-icon {
		position: absolute;
		left: 10px;
		top: 50%;
		transform: translateY(-50%);
		color: var(--color-text-muted);
		pointer-events: none;
	}
	.search-input {
		width: 100%;
		padding: 8px 12px 8px 32px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: 13px;
		background: var(--color-surface);
		color: var(--color-text-primary);
		outline: none;
	}
	.search-input:focus {
		border-color: var(--color-brand);
		box-shadow: 0 0 0 2px var(--color-brand-tint);
	}
	.ns-select {
		padding: 8px 12px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: 13px;
		background: var(--color-surface);
		color: var(--color-text-primary);
		min-width: 100px;
	}
	.btn-new {
		padding: 8px 16px;
		background: var(--color-brand);
		color: #fff;
		border: none;
		border-radius: var(--radius-input);
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.btn-new:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.chip-row {
		display: flex;
		gap: 6px;
		padding: 0 24px 12px;
		flex-wrap: wrap;
	}
	.pagination-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 8px;
	}
	.page-size-select {
		padding: 4px 8px;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		font-size: 12px;
		background: var(--color-surface);
		color: var(--color-text-primary);
	}
	.error-banner {
		margin: 12px 24px;
		padding: 12px 16px;
		background: #fef2f2;
		color: #dc2626;
		border-radius: var(--radius-card);
		font-size: 13px;
	}
</style>