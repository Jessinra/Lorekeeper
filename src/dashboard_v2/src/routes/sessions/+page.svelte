<script lang="ts">
	import { page } from '$app/state';
	import { replaceState, goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { SvelteMap, SvelteDate } from 'svelte/reactivity';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import FilterChip from '../../components/ui/FilterChip.svelte';
	import SessionDrawer from '$lib/components/overlays/SessionDrawer.svelte';
	import { SESSIONS_STRINGS as S } from '$lib/constants/strings';
	import { ICON_SEARCH, ICON_TABLE_EMPTY } from '$lib/constants/icons';
	import Icon from '$lib/components/ui/Icon.svelte';
	import Pagination from '$lib/components/table/Pagination.svelte';
	import type { SessionRow, SessionMemory, SessionDetail } from '$lib/api/sessions.js';
	import { fetchSessions, fetchSessionDetail } from '$lib/api/sessions.js';
	import type { MemoryEditFields } from '$lib/components/overlays/types.js';
	import { readSearchParam, readSearchParamInt } from '$lib/url.js';

	// ── URL state ──────────────────────────────────────────────────────────────

	let searchQuery = $state(readSearchParam((k) => page.url.searchParams.get(k), 'q', ''));
	let activeTask = $state(readSearchParam((k) => page.url.searchParams.get(k), 'task', ''));
	let currentPage = $state(readSearchParamInt((k) => page.url.searchParams.get(k), 'page', 1));
	let perPage = $state(50);

	function syncUrl() {
		const params = new URLSearchParams();
		if (searchQuery) params.set('q', searchQuery);
		if (activeTask) params.set('task', activeTask);
		if (currentPage > 1) params.set('page', String(currentPage));
		replaceState(`?${params.toString()}`, {});
	}

	// ── Data state ─────────────────────────────────────────────────────────────

	let sessions: SessionRow[] = $state([]);
	let total = $state(0);
	let totalPages = $state(1);
	let taskCounts: Record<string, number> = $state({});
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Drawer state ───────────────────────────────────────────────────────────

	let drawerOpen = $state(false);
	let selectedSession = $state<SessionRow | null>(null);
	let selectedMemories = $state<SessionMemory[]>([]);
	let selectedReflection = $state<SessionDetail['reflection']>(null);

	// ── Debounce timer ─────────────────────────────────────────────────────────

	let searchTimer: ReturnType<typeof setTimeout> | undefined = $state(undefined);

	// ── Load ───────────────────────────────────────────────────────────────────

	async function load() {
		loading = true;
		error = null;
		try {
			const res = await fetchSessions({
				q: searchQuery || undefined,
				task: activeTask || undefined,
				page: currentPage,
				page_size: perPage,
			});
			sessions = res.sessions;
			total = res.total;
			totalPages = res.total_pages;
			taskCounts = res.task_counts;
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	// ── Reload trigger ─────────────────────────────────────────────────────────
	// Explicit signal so resetAndLoad always fires a load even if currentPage
	// is already 1, without leaking searchQuery/activeTask as $effect deps.

	let reloadSignal = $state(0);

	$effect(() => {
		void currentPage;   // re-run when Pagination advances
		void reloadSignal;  // re-run when filter/search resets trigger
		syncUrl();
		void load();
	});

	// ── Page activation ────────────────────────────────────────────────────────

	onMount(() => { reloadSignal++; });

	function resetAndLoad() {
		currentPage = 1;
		reloadSignal++; // always fires load, even if page was already 1
	}

	// ── Search handling ────────────────────────────────────────────────────────

	function onSearchInput(e: Event) {
		searchQuery = (e.target as HTMLInputElement).value;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => resetAndLoad(), 300);
	}

	// ── Filter chips ───────────────────────────────────────────────────────────

	const TASK_TYPES = ['build', 'debug', 'review', 'design'];

	function toggleTask(task: string) {
		activeTask = activeTask === task ? '' : task;
		resetAndLoad();
	}

	// ── Day grouping ───────────────────────────────────────────────────────────

	interface DayGroup {
		label: string;
		sessions: SessionRow[];
	}

	let dayGroups = $derived.by(() => {
		const groups: DayGroup[] = [];
		const seen = new SvelteMap<string, DayGroup>();

		const today = new SvelteDate();
		today.setHours(0, 0, 0, 0);
		const yesterday = new SvelteDate(today);
		yesterday.setDate(today.getDate() - 1);

		for (const s of sessions) {
			const rawDate = s.session_date ?? s.reviewed_at;
			const d = new SvelteDate(rawDate);
			d.setHours(0, 0, 0, 0);

			let label: string;
			if (d.getTime() === today.getTime()) {
				label = 'Today';
			} else if (d.getTime() === yesterday.getTime()) {
				label = 'Yesterday';
			} else {
				label = d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
			}

			const key = d.toISOString();
			if (!seen.has(key)) {
				const group: DayGroup = { label, sessions: [] };
				seen.set(key, group);
				groups.push(group);
			}
			seen.get(key)!.sessions.push(s);
		}
		return groups;
	});

	// ── Session card helpers ───────────────────────────────────────────────────

	function taskBadgeClass(type: string | null): string {
		switch (type) {
			case 'build': return 'task-build';
			case 'debug': return 'task-debug';
			case 'review': return 'task-review';
			case 'design': return 'task-design';
			default: return 'task-other';
		}
	}

	function formatTime(dateStr: string | null): string {
		if (!dateStr) return '—';
		const d = new SvelteDate(dateStr);
		return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}

	// ── Drawer open/close ──────────────────────────────────────────────────────

	async function openSession(s: SessionRow) {
		selectedSession = s;
		selectedMemories = [];
		selectedReflection = null;
		drawerOpen = true;
		// Fetch full detail in background
		try {
			const detail = await fetchSessionDetail(s.session_id);
			selectedMemories = detail.memories;
			selectedReflection = detail.reflection;
			// Update session with richer data if available
			selectedSession = detail.session;
		} catch {
			// non-fatal; drawer still shows with partial data
		}
	}

	function closeDrawer() {
		drawerOpen = false;
		selectedSession = null;
	}

	// ── Memory drawer handlers (delegated to memories page API) ────────────────

	async function onMemorySave(id: string, fields: MemoryEditFields): Promise<boolean> {
		try {
			const res = await fetch(`/api/memories/${id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(fields),
			});
			return res.ok;
		} catch {
			return false;
		}
	}

	function onMemoryDelete(id: string) {
		// Optimistically remove from local list; MemoryDetailDrawer calls onSave
		// with soft_deleted:true which persists the removal server-side.
		selectedMemories = selectedMemories.filter((m) => m.lore_id !== id);
	}

	async function onMemoryNavigate(targetId: string) {
		await goto(`/memories?open=${encodeURIComponent(targetId)}`);
	}
</script>

<PageShell title="Sessions">
	<!-- Toolbar -->
	<div class="toolbar">
		<div class="search-wrapper">
			<Icon path={ICON_SEARCH} size={14} />
			<input
				type="search"
				class="search-input"
				placeholder={S.searchPlaceholder}
				value={searchQuery}
				oninput={onSearchInput}
				aria-label={S.searchPlaceholder}
			/>
		</div>
	</div>

	<!-- Filter chips -->
	<div class="chip-row" role="group" aria-label="Task type filters">
		<FilterChip
			label={S.filterAll}
			active={!activeTask}
			count={total}
			onToggle={() => { activeTask = ''; resetAndLoad(); }}
		/>
		{#each TASK_TYPES as taskType (taskType)}
			<FilterChip
				label={taskType}
				active={activeTask === taskType}
				count={taskCounts[taskType] ?? 0}
				onToggle={() => toggleTask(taskType)}
			/>
		{/each}
	</div>

	<!-- Timeline -->
	{#if loading}
		<div class="loading-state" aria-live="polite">Loading sessions…</div>
	{:else if error}
		<div class="error-banner" role="alert">{error}</div>
	{:else if dayGroups.length === 0}
		<div class="empty-state" aria-live="polite">
			<Icon path={ICON_TABLE_EMPTY} size={40} />
			<p>{S.emptyState}</p>
		</div>
	{:else}
		<div class="timeline">
			{#each dayGroups as group (group.label)}
				<section class="day-section">
					<h2 class="day-header">{group.label}</h2>
					<ul class="session-list" role="list">
						{#each group.sessions as s (s.session_id)}
							<li>
								<button
									class="session-card"
									onclick={() => openSession(s)}
									aria-label={`Open session: ${s.topic ?? s.session_id.slice(0, 8)}`}
								>
									<div class="card-left">
										<span class="timeline-dot" aria-hidden="true"></span>
										<div class="card-body">
											<div class="card-top">
												{#if s.task_type}
													<span class="task-badge {taskBadgeClass(s.task_type)}">{s.task_type}</span>
												{/if}
												<span class="card-title">{s.topic ?? '(untitled)'}</span>
											</div>
											<div class="card-meta">
												<span class="card-time">{formatTime(s.session_date ?? s.reviewed_at)}</span>
												<span class="meta-sep" aria-hidden="true">·</span>
												<code class="session-id-chip">{s.session_id.slice(0, 8)}</code>
											</div>
										</div>
									</div>
									<span class="card-arrow" aria-hidden="true">›</span>
								</button>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>

		<!-- Pagination -->
		{#if totalPages > 1}
			<div class="pagination-bar">
				<Pagination
					totalRows={total}
					bind:page={currentPage}
					bind:pageSize={perPage}
				/>
			</div>
		{/if}
	{/if}
</PageShell>

<SessionDrawer
	open={drawerOpen}
	session={selectedSession}
	memories={selectedMemories}
	reflection={selectedReflection}
	onClose={closeDrawer}
	onMemoryNavigate={onMemoryNavigate}
	onMemorySave={onMemorySave}
	onMemoryDelete={onMemoryDelete}
/>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6) 0;
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

	.chip-row {
		display: flex;
		gap: var(--space-1-5);
		padding: var(--space-3) var(--space-6) var(--space-1);
		flex-wrap: wrap;
	}

	.loading-state,
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: 80px var(--space-6);
		color: var(--color-text-muted);
		font-size: var(--font-size-body);
	}

	.error-banner {
		margin: var(--space-3) var(--space-6);
		padding: var(--space-3) var(--space-4);
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border-radius: var(--radius-card);
		font-size: var(--font-size-body);
	}

	.timeline {
		padding: var(--space-4) var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-8);
	}

	.day-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.day-header {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-bold);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-muted);
		margin: 0 0 var(--space-1);
		padding-left: var(--space-5);
	}

	.session-list {
		list-style: none;
		padding: 0;
		margin: 0;
		border-left: 2px solid var(--color-border);
		margin-left: var(--space-2);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.session-card {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		background: var(--color-card-bg, var(--color-surface));
		border: var(--border-width) solid var(--color-card-border, var(--color-border));
		border-radius: var(--radius-card);
		padding: var(--space-2-5) var(--space-3) var(--space-2-5) 0;
		cursor: pointer;
		text-align: left;
		margin-left: var(--space-4);
		transition: background-color 150ms, border-color 150ms;
		gap: var(--space-2);
	}

	.session-card:hover {
		background-color: var(--color-chip-hover-bg);
		border-color: var(--color-brand-tint, var(--color-border));
	}

	.card-left {
		display: flex;
		align-items: center;
		gap: 0;
		flex: 1;
		min-width: 0;
	}

	.timeline-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: var(--color-brand, #6366f1);
		flex-shrink: 0;
		margin-left: -4px; /* overlap the timeline line */
		margin-right: var(--space-3);
	}

	.card-body {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		min-width: 0;
		flex: 1;
	}

	.card-top {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.task-badge {
		display: inline-flex;
		align-items: center;
		border-radius: var(--radius-pill);
		padding: 1px var(--space-2);
		font-size: var(--font-size-badge);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.05em;
		text-transform: uppercase;
		flex-shrink: 0;
	}

	.task-build {
		background-color: var(--color-task-build-bg);
		color: var(--color-task-build-text);
	}
	.task-debug {
		background-color: var(--color-task-debug-bg);
		color: var(--color-task-debug-text);
	}
	.task-review {
		background-color: var(--color-task-review-bg);
		color: var(--color-task-review-text);
	}
	.task-design {
		background-color: var(--color-task-design-bg);
		color: var(--color-task-design-text);
	}
	.task-other {
		background-color: var(--color-chip-bg);
		color: var(--color-chip-text);
	}

	.card-title {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--color-text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.card-meta {
		display: flex;
		align-items: center;
		gap: var(--space-1-5);
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
	}

	.card-time {
		font-variant-numeric: tabular-nums;
	}

	.meta-sep {
		opacity: 0.5;
	}

	.session-id-chip {
		font-family: var(--font-mono, monospace);
		font-size: var(--font-size-badge);
		color: var(--color-text-muted);
		opacity: 0.7;
	}

	.card-arrow {
		font-size: var(--font-size-body);
		color: var(--color-text-muted);
		flex-shrink: 0;
	}

	.pagination-bar {
		padding: var(--space-3) var(--space-6);
		display: flex;
		justify-content: center;
	}
</style>
