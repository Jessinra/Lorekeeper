<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import RelationshipDrawer from '$lib/components/overlays/RelationshipDrawer.svelte';
	import RelationPill from '../../components/ui/RelationPill.svelte';
	import { LINKS_STRINGS as S } from '$lib/constants/strings.js';
	import { ICON_SEARCH, ICON_TABLE_EMPTY } from '$lib/constants/icons.js';
	import { fetchLinks, deleteLink } from '$lib/api/links.js';
	import { fetchMemoryDetail } from '$lib/api/memories.js';
	import type { LinkRow } from '$lib/api/links.js';
	import type { MemoryData } from '$lib/components/overlays/types.js';
	import { showToast } from '$lib/toast.js';
	import { relativeTime } from '$lib/time.js';
	import { RELATION_STYLES } from '$lib/constants/primitives.js';
	import { readSearchParam } from '$lib/url.js';

	// ── URL state ──────────────────────────────────────────────────────────────

	let searchQuery = $state(readSearchParam((k) => page.url.searchParams.get(k), 'q', ''));
	let includeDeleted = $state(false);

	function syncUrl() {
		const params = new URLSearchParams();
		if (searchQuery) params.set('q', searchQuery);
		replaceState(`?${params.toString()}`, {});
	}

	// ── Data state ─────────────────────────────────────────────────────────────

	let allRows: LinkRow[] = $state([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let filteredRows = $derived(
		searchQuery
			? allRows.filter(
					(r) =>
						r.source_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
						r.target_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
						r.relation_type.toLowerCase().includes(searchQuery.toLowerCase()),
				)
			: allRows,
	);

	// ── Load ───────────────────────────────────────────────────────────────────

	let reloadSignal = $state(0);

	// Load effect: only reruns when includeDeleted or reloadSignal changes
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		reloadSignal;
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		includeDeleted;
		load();
	});

	// URL sync effect: only reruns when searchQuery changes
	$effect(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions
		searchQuery;
		syncUrl();
	});

	async function load() {
		loading = true;
		error = null;
		try {
			allRows = await fetchLinks(includeDeleted);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	// ── Search ─────────────────────────────────────────────────────────────────

	// Also remove the redundant timer-based URL update — URL sync is handled by the effect above
	function onSearchInput(e: Event) {
		searchQuery = (e.target as HTMLInputElement).value;
	}

	// ── Relationship drawer ────────────────────────────────────────────────────

	let drawerOpen = $state(false);
	let drawerLinkId = $state<string | null>(null);
	let drawerRelationType = $state('');
	let drawerSource = $state<MemoryData | null>(null);
	let drawerTarget = $state<MemoryData | null>(null);
	let drawerAbortController: AbortController | null = null;

	async function openDrawer(row: LinkRow) {
		// Cancel any in-flight fetch for a previously opened row
		drawerAbortController?.abort();
		const controller = new AbortController();
		drawerAbortController = controller;

		const requestedLinkId = row.id;
		drawerLinkId = requestedLinkId;
		drawerRelationType = row.relation_type;
		drawerSource = null;
		drawerTarget = null;
		drawerOpen = true;

		try {
			// Fetch both memories in parallel
			const [srcDetail, tgtDetail] = await Promise.all([
				fetchMemoryDetail(row.source_memory_id),
				fetchMemoryDetail(row.target_memory_id),
			]);
			// Guard: discard results if a newer row was opened before this resolved
			if (controller.signal.aborted || drawerLinkId !== requestedLinkId) return;
			drawerSource = srcDetail.memory as MemoryData;
			drawerTarget = tgtDetail.memory as MemoryData;
		} catch (e) {
			if (controller.signal.aborted) return;
			// Fetch failed — close drawer rather than leaving it in a broken loading state
			drawerOpen = false;
			drawerLinkId = null;
			showToast((e as Error).message || S.loadError, 'error');
		}
	}

	function onDrawerClose() {
		drawerOpen = false;
		drawerSource = null;
		drawerTarget = null;
		drawerLinkId = null;
	}

	async function onDrawerDelete(linkId: string): Promise<boolean> {
		// Optimistic: remove the row immediately, restore on failure
		const removedRow = allRows.find((r) => r.id === linkId);
		allRows = allRows.filter((r) => r.id !== linkId);
		drawerOpen = false;

		try {
			const ok = await deleteLink(linkId);
			if (ok) {
				showToast(S.deleteSuccess, 'success');
				return true;
			} else {
				// Non-OK response: restore row
				if (removedRow) allRows = [...allRows, removedRow];
				drawerOpen = true;
				showToast(S.deleteError, 'error');
				return false;
			}
		} catch (e) {
			// Network/thrown error: restore row
			if (removedRow) allRows = [...allRows, removedRow];
			drawerOpen = true;
			showToast(S.deleteError, 'error');
			return false;
		}
	}

	function onDrawerNavigate(_memoryId: string) {
		// future: navigate to memory detail
	}
</script>

<PageShell title="Links">
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

		<label class="include-deleted-label">
			<input
				type="checkbox"
				bind:checked={includeDeleted}
				onchange={() => (reloadSignal++)}
			/>
			{S.includeDeletedLabel}
		</label>

		<span class="row-count" aria-live="polite">
			{filteredRows.length} link{filteredRows.length !== 1 ? 's' : ''}
		</span>
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
		{:else if filteredRows.length === 0}
			<div class="empty-state">
				<Icon path={ICON_TABLE_EMPTY} size={40} />
				<p class="empty-title">{S.emptyTitle}</p>
				<p class="empty-msg">{S.emptyMessage}</p>
			</div>
		{:else}
			<table>
				<thead>
					<tr>
						<th class="col-source">{S.colSource}</th>
						<th class="col-relation">{S.colRelation}</th>
						<th class="col-target">{S.colTarget}</th>
						<th class="col-score">{S.colScore}</th>
						<th class="col-date">{S.colDate}</th>
						<th class="col-reason">{S.colReason}</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredRows as row (row.id)}
						<tr
							class="link-row"
							onclick={() => openDrawer(row)}
							aria-label={`${row.source_title} ${row.relation_type} ${row.target_title}`}
						>
							<td class="col-source" title={row.source_title}>
								<button
									class="row-open-btn memory-title"
									onclick={(e: MouseEvent) => { e.stopPropagation(); openDrawer(row); }}
									aria-label={`Open link: ${row.source_title} ${row.relation_type} ${row.target_title}`}
								>{row.source_title}</button>
							</td>
							<td class="col-relation">
								<RelationPill type={row.relation_type as keyof typeof RELATION_STYLES} />
							</td>
							<td class="col-target" title={row.target_title}>
								<span class="memory-title">{row.target_title}</span>
							</td>
							<td class="col-score">
								<span class="score-badge">{row.score.toFixed(2)}</span>
							</td>
							<td class="col-date">{relativeTime(row.created_at)}</td>
							<td class="col-reason" title={row.reason}>
								<span class="reason-text">{row.reason}</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</PageShell>

<!-- Relationship drawer -->
<RelationshipDrawer
	open={drawerOpen}
	sourceMemory={drawerSource}
	targetMemory={drawerTarget}
	relationType={drawerRelationType}
	linkId={drawerLinkId}
	suggestionId={null}
	page="links"
	onClose={onDrawerClose}
	onNavigate={onDrawerNavigate}
	onDelete={onDrawerDelete}
/>

<style>
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

	.include-deleted-label {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: var(--font-size-sm);
		color: var(--color-text-muted);
		cursor: pointer;
		user-select: none;
	}

	.row-count {
		font-size: var(--font-size-sm);
		color: var(--color-text-muted);
		margin-left: auto;
	}

	/* ── Table ────────────────────────────────────────────────────────────────── */

	.table-wrap {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	thead th {
		padding: var(--space-2) var(--space-3);
		text-align: left;
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-muted);
		border-bottom: var(--border-width) solid var(--color-border);
		white-space: nowrap;
	}

	tbody tr {
		border-bottom: var(--border-width) solid var(--color-border-subtle);
		cursor: pointer;
		transition: background-color 0.1s;
	}

	tbody tr:last-child {
		border-bottom: none;
	}

	tbody tr:hover,
	tbody tr:focus-visible {
		background: var(--color-surface-raised);
		outline: none;
	}

	td {
		padding: var(--space-2) var(--space-3);
		font-size: var(--font-size-body);
		vertical-align: middle;
	}

	.col-source,
	.col-target {
		max-width: 200px;
	}

	.col-reason {
		max-width: 240px;
	}

	.col-score {
		width: 70px;
		text-align: right;
	}

	.col-date {
		width: 100px;
		white-space: nowrap;
	}

	.memory-title,
	.reason-text {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.row-open-btn {
		background: none;
		border: none;
		padding: 0;
		margin: 0;
		font: inherit;
		color: inherit;
		text-align: left;
		cursor: pointer;
		width: 100%;
	}

	.reason-text {
		color: var(--color-text-muted);
		font-size: var(--font-size-sm);
	}

	.score-badge {
		font-size: var(--font-size-badge);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-muted);
		font-variant-numeric: tabular-nums;
	}

	/* ── Skeleton ─────────────────────────────────────────────────────────────── */

	.skeleton-rows {
		padding: var(--space-2);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.skeleton-row {
		height: 40px;
		background: var(--color-border-subtle);
		border-radius: var(--radius-sm);
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: var(--opacity-skeleton, 0.4); }
	}

	/* ── Empty state ──────────────────────────────────────────────────────────── */

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-8);
		color: var(--color-text-muted);
	}

	.empty-title {
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-secondary);
		margin: 0;
	}

	.empty-msg {
		font-size: var(--font-size-sm);
		text-align: center;
		margin: 0;
	}

	/* ── Error ────────────────────────────────────────────────────────────────── */

	.error-banner {
		padding: var(--space-4);
		color: var(--color-danger-text);
		background: var(--color-danger-bg);
		border-radius: var(--radius-sm);
		margin: var(--space-2);
		font-size: var(--font-size-body);
	}
</style>
