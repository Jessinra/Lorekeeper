<script lang="ts">
	import { tick } from 'svelte';
	import { SESSIONS_STRINGS as S } from '$lib/constants/strings';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
	import ScorePill from '../../../components/ui/ScorePill.svelte';
	import MemoryDetailDrawer from './MemoryDetailDrawer.svelte';
	import type { MemoryData, LinkData, MemoryEditFields } from './types.js';
	import type { SessionRow, SessionMemory } from '$lib/api/sessions.js';
	import { relativeTime } from '$lib/time.js';

	// ── Props ──────────────────────────────────────────────────────────────────

	interface Props {
		open: boolean;
		session: SessionRow | null;
		memories?: SessionMemory[];
		reflection?: { id: string; created_at: string; summary: string } | null;
		onClose: () => void;
		onMemoryNavigate: (targetId: string) => void;
		onMemorySave: (id: string, fields: MemoryEditFields) => Promise<boolean> | void;
		onMemoryDelete: (id: string) => void;
	}

	let {
		open,
		session,
		memories = [],
		reflection = null,
		onClose,
		onMemoryNavigate,
		onMemorySave,
		onMemoryDelete,
	}: Props = $props();

	// ── State ──────────────────────────────────────────────────────────────────

	let drawerEl: HTMLElement | null = $state(null);
	let copyTooltipVisible = $state(false);

	// Stacked memory drawer
	let memoryDrawerOpen = $state(false);
	let selectedMemory = $state<MemoryData | null>(null);
	let selectedLinks = $state<LinkData[]>([]);

	// Auto-focus on open
	$effect(() => {
		if (open && session && drawerEl) {
			void tick().then(() => { drawerEl?.focus(); });
		}
		if (!open) {
			memoryDrawerOpen = false;
			selectedMemory = null;
			selectedLinks = [];
		}
	});

	// ── Derived ────────────────────────────────────────────────────────────────

	let taskBadgeStyle = $derived.by(() => {
		const type = session?.task_type ?? '';
		switch (type) {
			case 'build': return 'background-color: var(--color-task-build-bg); color: var(--color-task-build-text);';
			case 'debug': return 'background-color: var(--color-task-debug-bg); color: var(--color-task-debug-text);';
			case 'review': return 'background-color: var(--color-task-review-bg); color: var(--color-task-review-text);';
			case 'design': return 'background-color: var(--color-task-design-bg); color: var(--color-task-design-text);';
			default: return 'background-color: var(--color-chip-bg); color: var(--color-chip-text);';
		}
	});

	let formattedDate = $derived(
		session?.session_date
			? new Date(session.session_date).toLocaleDateString(undefined, { dateStyle: 'long' })
			: session?.reviewed_at
				? relativeTime(session.reviewed_at)
				: '—',
	);

	// ── Actions ────────────────────────────────────────────────────────────────

	async function copySessionId() {
		if (!session) return;
		await navigator.clipboard.writeText(session.session_id);
		copyTooltipVisible = true;
		setTimeout(() => { copyTooltipVisible = false; }, 2000);
	}

	function openMemory(mem: SessionMemory) {
		selectedMemory = {
			lore_id: mem.lore_id,
			title: mem.title,
			description: mem.description,
			content: '',
			namespace: mem.namespace,
			source_type: mem.source_type,
			score: mem.score,
			confidence: 0,
			usage_count: 0,
			soft_deleted: false,
			created_at: '',
			updated_at: '',
		};
		selectedLinks = [];
		memoryDrawerOpen = true;
	}

	function closeMemoryDrawer() {
		memoryDrawerOpen = false;
		selectedMemory = null;
	}

	// ── Focus trap ─────────────────────────────────────────────────────────────

	const FOCUSABLE_SELECTOR =
		'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

	function trapFocus(e: KeyboardEvent) {
		if (e.key !== 'Tab' || !drawerEl) return;
		const focusable = Array.from(drawerEl.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
		if (focusable.length === 0) return;
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (e.shiftKey) {
			if (document.activeElement === first) { e.preventDefault(); last.focus(); }
		} else {
			if (document.activeElement === last) { e.preventDefault(); first.focus(); }
		}
	}
</script>

{#if open && session}
	<OverlayScrim onclick={onClose} />

	<!-- Session drawer panel -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<aside
		bind:this={drawerEl}
		class="drawer"
		role="complementary"
		aria-label={S.drawerAriaLabel}
		tabindex="-1"
		onkeydown={(e) => {
			if (e.key === 'Escape') onClose();
			else trapFocus(e);
		}}
	>
		<!-- Close button -->
		<button class="close-btn" onclick={onClose} aria-label={S.closeButtonAriaLabel}>✕</button>

		<!-- Header -->
		<div class="header">
			{#if session.task_type}
				<span class="task-badge" style={taskBadgeStyle}>{session.task_type}</span>
			{/if}
			<h2 class="title">{session.topic ?? session.session_id.slice(0, 8)}</h2>
		</div>

		<!-- Meta row -->
		<div class="meta-row">
			<span class="meta-label">Date</span>
			<span class="meta-value">{formattedDate}</span>
			<span class="meta-divider" aria-hidden="true"></span>
			<span class="meta-label">Session ID</span>
			<code class="meta-session-id">{session.session_id.slice(0, 8)}</code>
			{#if session.reflection_id && reflection}
				<span class="meta-divider" aria-hidden="true"></span>
				<span class="meta-label">Reflection</span>
				<span class="meta-value">{reflection.summary?.slice(0, 40) ?? '…'}</span>
			{/if}
		</div>

		<!-- Body -->
		<div class="body">
			{#if session.what_was_done}
				<section class="section">
					<h3 class="section-heading">Summary</h3>
					<p class="section-text">{session.what_was_done}</p>
				</section>
			{/if}

			<!-- Memories list -->
			<section class="section">
				<h3 class="section-heading">{S.memoriesHeading} ({memories.length})</h3>
				{#if memories.length === 0}
					<p class="empty-memories">{S.noMemories}</p>
				{:else}
					<ul class="memory-list" role="list">
						{#each memories as mem (mem.lore_id)}
							<li>
								<button class="memory-card" onclick={() => openMemory(mem)}>
									<div class="memory-card-top">
										<span class="memory-title">{mem.title}</span>
										<ScorePill score={mem.score} />
									</div>
									{#if mem.description}
										<p class="memory-desc">{mem.description}</p>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</div>

		<!-- Footer -->
		<div class="footer">
			<button class="copy-btn" onclick={copySessionId}>
				{copyTooltipVisible ? S.copyIdDone : S.copyId}
			</button>
		</div>
	</aside>

	<!-- Stacked MemoryDetailDrawer -->
	<MemoryDetailDrawer
		open={memoryDrawerOpen}
		memory={selectedMemory}
		links={selectedLinks}
		onClose={closeMemoryDrawer}
		onSave={onMemorySave}
		onDelete={onMemoryDelete}
		onNavigate={onMemoryNavigate}
	/>
{/if}

<style>
	.drawer {
		position: fixed;
		inset-block: 0;
		inset-inline-end: 0;
		width: min(460px, 100vw);
		z-index: 800;
		background-color: var(--color-drawer-bg);
		border-left: var(--border-width) solid var(--color-drawer-border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		animation: slide-in 240ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
		outline: none;
	}

	@keyframes slide-in {
		from { transform: translateX(100%); }
		to   { transform: translateX(0); }
	}

	.close-btn {
		position: absolute;
		inset-block-start: var(--space-3);
		inset-inline-end: var(--space-3);
		background: none;
		border: none;
		cursor: pointer;
		color: var(--color-text-muted);
		font-size: 1rem;
		padding: var(--space-1);
		border-radius: var(--radius-sm);
		line-height: 1;
	}

	.close-btn:hover {
		color: var(--color-text);
		background-color: var(--color-chip-hover-bg);
	}

	.header {
		padding: var(--space-6) var(--space-5) var(--space-3);
		border-bottom: var(--border-width) solid var(--color-drawer-border);
		padding-right: var(--space-10);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.task-badge {
		display: inline-flex;
		align-items: center;
		border-radius: 9999px;
		padding: 2px 10px;
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.04em;
		text-transform: uppercase;
		width: fit-content;
	}

	.title {
		font-size: 1.05rem;
		font-weight: var(--font-weight-semibold);
		color: var(--color-text);
		margin: 0;
		line-height: 1.3;
	}

	.meta-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-5);
		border-bottom: var(--border-width) solid var(--color-drawer-border);
		font-size: var(--font-size-micro);
	}

	.meta-label {
		color: var(--color-text-muted);
	}

	.meta-value {
		color: var(--color-text);
	}

	.meta-divider {
		width: 1px;
		height: 12px;
		background-color: var(--color-drawer-divider);
	}

	.meta-session-id {
		font-family: var(--font-mono, monospace);
		font-size: var(--font-size-badge);
		color: var(--color-text-muted);
		background-color: var(--color-drawer-code-bg, var(--color-chip-bg));
		border: var(--border-width) solid var(--color-drawer-code-border, var(--color-chip-border));
		border-radius: var(--radius-sm);
		padding: 1px 5px;
	}

	.body {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-4) var(--space-5);
		display: flex;
		flex-direction: column;
		gap: var(--space-5);
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.section-heading {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--color-text-muted);
		margin: 0;
	}

	.section-text {
		font-size: var(--font-size-sm);
		line-height: 1.6;
		color: var(--color-text);
		margin: 0;
		white-space: pre-wrap;
	}

	.memory-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.memory-card {
		width: 100%;
		text-align: left;
		background: var(--color-card-bg, var(--color-chip-bg));
		border: var(--border-width) solid var(--color-card-border, var(--color-chip-border));
		border-radius: var(--radius-md);
		padding: var(--space-3);
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		transition: background-color 150ms;
	}

	.memory-card:hover {
		background-color: var(--color-chip-hover-bg);
	}

	.memory-card-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
	}

	.memory-title {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--color-text);
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.memory-desc {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.empty-memories {
		font-size: var(--font-size-xs);
		color: var(--color-text-muted);
		margin: 0;
	}

	.footer {
		padding: var(--space-3) var(--space-5);
		border-top: var(--border-width) solid var(--color-drawer-border);
		background-color: var(--color-drawer-bg);
		display: flex;
		gap: var(--space-2);
	}

	.copy-btn {
		font-size: var(--font-size-xs);
		padding: var(--space-1) var(--space-3);
		border-radius: var(--radius-sm);
		border: var(--border-width) solid var(--color-chip-border);
		background: var(--color-chip-bg);
		color: var(--color-chip-text);
		cursor: pointer;
		transition: background-color 150ms;
	}

	.copy-btn:hover {
		background-color: var(--color-chip-hover-bg);
	}
</style>
