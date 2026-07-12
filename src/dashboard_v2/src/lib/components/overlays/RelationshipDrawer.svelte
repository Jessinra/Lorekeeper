<script lang="ts">
	import { tick } from 'svelte';
	import { RELATION_DRAWER_STRINGS as S } from '$lib/constants/strings';
	import { RELATION_STYLES, readableLabel } from '$lib/constants/primitives';
	import type { MemoryData } from './types';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
	import RelationPill from '../../../components/ui/RelationPill.svelte';
	import MemoryCard from './MemoryCard.svelte';

	// ── Props ──────────────────────────────────────────────────────────────────

	type PageContext = 'links' | 'review-suggestions' | 'review-stale';

	interface Props {
		open: boolean;
		sourceMemory: MemoryData | null;
		targetMemory: MemoryData | null;
		relationType: string;
		linkId: string | null;
		suggestionId: string | null;
		page: PageContext;
		onClose: () => void;
		onNavigate: (memoryId: string) => void;
		onDelete: (linkId: string) => Promise<boolean>;
		onAccept?: (suggestionId: string) => Promise<boolean>;
		onReject?: (suggestionId: string) => Promise<boolean>;
		onRefresh?: (linkId: string) => Promise<boolean>;
	}

	let {
		open,
		sourceMemory,
		targetMemory,
		relationType,
		linkId = null,
		suggestionId = null,
		page,
		onClose,
		onNavigate,
		onDelete,
		onAccept = async () => true,
		onReject = async () => true,
		onRefresh = async () => true,
	}: Props = $props();

	// ── State ──────────────────────────────────────────────────────────────────

	let drawerEl: HTMLElement | null = $state(null);
	let actionPending = $state(false);
	let actionResult: 'accepted' | 'rejected' | null = $state(null);
	let confirmDelete = $state(false);

	// Auto-focus drawer on open
	$effect(() => {
		if (open && drawerEl) {
			tick().then(() => drawerEl?.focus());
		}
		if (!open) {
			actionResult = null;
			actionPending = false;
			confirmDelete = false;
		}
	});

	// ── Derived ────────────────────────────────────────────────────────────────

	let subtitle = $derived(
		`${sourceMemory?.title ?? '…'} ${readableLabel(relationType)} ${targetMemory?.title ?? '…'}`,
	);

	let directionArrow = $derived(
		relationType === 'references' || relationType === 'implements' || relationType === 'depends_on'
			? '→'
			: '↔',
	);

	let hasConflictTint = $derived(relationType === 'conflicts_with');

	// ── Type-safe casts ──────────────────────────────────────────────────────

	function rel(type: string): keyof typeof RELATION_STYLES {
		return type as keyof typeof RELATION_STYLES;
	}

	// ── Focus trap ─────────────────────────────────────────────────────────

	const FOCUSABLE_SELECTOR =
		'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

	let previouslyFocused: HTMLElement | null = null;

	function trapFocus(e: KeyboardEvent) {
		if (e.key !== 'Tab' || !drawerEl) return;
		const focusable = Array.from(drawerEl.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
		if (focusable.length === 0) return;
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (e.shiftKey) {
			if (document.activeElement === first) {
				e.preventDefault();
				last.focus();
			}
		} else {
			if (document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	// ── Handlers ────────────────────────────────────────────────────────────

	function handleKeydown(e: KeyboardEvent) {
		trapFocus(e);
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
		}
	}

	function handleCardClick(memoryId: string) {
		onClose();
		onNavigate(memoryId);
	}

	async function handleDelete() {
		if (!linkId) return;
		if (!confirmDelete) {
			confirmDelete = true;
			return;
		}
		actionPending = true;
		try {
			const success = await onDelete(linkId);
			if (success) onClose();
		} finally {
			actionPending = false;
			confirmDelete = false;
		}
	}

	async function handleAccept() {
		if (!suggestionId) return;
		actionPending = true;
		try {
			const success = await onAccept(suggestionId);
			if (success) {
				actionResult = 'accepted';
				setTimeout(() => onClose(), 1500);
			}
		} finally {
			actionPending = false;
		}
	}

	async function handleReject() {
		if (!suggestionId) return;
		actionPending = true;
		try {
			const success = await onReject(suggestionId);
			if (success) {
				actionResult = 'rejected';
				setTimeout(() => onClose(), 1500);
			}
		} finally {
			actionPending = false;
		}
	}

	async function handleRefresh() {
		if (!linkId) return;
		actionPending = true;
		try {
			await onRefresh(linkId);
		} finally {
			actionPending = false;
		}
	}

	function handleDeleteCancel() {
		confirmDelete = false;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
{#if open}
	<OverlayScrim onclick={onClose} />
	<div
		class="drawer"
		class:conflict-tint={hasConflictTint}
		bind:this={drawerEl}
		role="dialog"
		aria-modal="true"
		aria-label={S.drawerAriaLabel}
		onkeydown={handleKeydown}
		tabindex="-1"
	>
		<!-- Close button -->
		<button
			type="button"
			class="close-btn"
			onclick={onClose}
			aria-label={S.closeButtonAriaLabel}
		>
			&times;
		</button>

		<!-- Header -->
		<div class="header">
			<h2 class="header-title">{S.drawerAriaLabel}</h2>
			<p class="header-subtitle">{subtitle}</p>
		</div>

		<!-- Body: two memory cards -->
		<div class="body">
		{#if sourceMemory && targetMemory}
				<MemoryCard memory={sourceMemory} conflictTint={hasConflictTint} onClick={() => handleCardClick(sourceMemory.lore_id)} />

				<!-- Relation center column -->
				<div class="relation-center">
					<RelationPill type={rel(relationType)} />
					<span class="direction-arrow">{directionArrow}</span>
				</div>

				<MemoryCard memory={targetMemory} conflictTint={hasConflictTint} onClick={() => handleCardClick(targetMemory.lore_id)} />
			{:else if !sourceMemory && !targetMemory}
				<div class="empty-state">{S.loading}</div>
			{/if}
		</div>

		<!-- Footer: context-sensitive actions -->
		<div class="footer" class:accepted={actionResult === 'accepted'} class:rejected={actionResult === 'rejected'}>
			{#if page === 'links'}
				{#if confirmDelete}
					<button
						type="button"
						class="btn-confirm"
						disabled={actionPending}
						onclick={handleDelete}
					>
						{actionPending ? '…' : S.deleteConfirm}
					</button>
					<button
						type="button"
						class="btn-outline"
						disabled={actionPending}
						onclick={handleDeleteCancel}
					>
						Cancel
					</button>
				{:else}
					<button
						type="button"
						class="btn-danger"
						disabled={actionPending}
						onclick={handleDelete}
					>
						{actionPending ? '…' : S.deleteLink}
					</button>
				{/if}
			{:else if page === 'review-suggestions'}
				{#if actionResult === 'accepted'}
					<span class="result-label accepted">{S.accept} ✓</span>
				{:else if actionResult === 'rejected'}
					<span class="result-label rejected">{S.reject} ✕</span>
				{:else}
					<button
						type="button"
						class="btn-reject"
						disabled={actionPending}
						onclick={handleReject}
					>
						{actionPending ? '…' : S.reject}
					</button>
					<button
						type="button"
						class="btn-accept"
						disabled={actionPending}
						onclick={handleAccept}
					>
						{actionPending ? '…' : S.accept}
					</button>
				{/if}
			{:else if page === 'review-stale'}
				<button
					type="button"
					class="btn-danger"
					disabled={actionPending}
					onclick={handleDelete}
				>
					{actionPending ? '…' : S.deleteLink}
				</button>
				<button
					type="button"
					class="btn-refresh"
					disabled={actionPending}
					onclick={handleRefresh}
				>
					{actionPending ? '⟳' : S.refresh}
				</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	/* ── Drawer container ── */
	.drawer {
		position: fixed;
		top: 0;
		right: 0;
		width: 640px;
		max-width: 92vw;
		height: 100vh;
		z-index: 801;
		background-color: var(--color-drawer-bg);
		box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		animation: slide-in 200ms ease forwards;
	}

	.drawer.conflict-tint {
		border-left: 3px solid #fecaca;
	}

	@keyframes slide-in {
		from { transform: translateX(100%); }
		to   { transform: translateX(0); }
	}

	/* ── Close button ── */
	.close-btn {
		position: absolute;
		top: 12px;
		right: 12px;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: none;
		font-size: 18px;
		color: var(--color-text-muted);
		cursor: pointer;
		border-radius: 4px;
	}

	.close-btn:hover {
		background-color: var(--color-hover-bg);
		color: var(--color-text-primary);
	}

	/* ── Header ── */
	.header {
		padding: 24px 24px 16px;
		border-bottom: var(--border-width) solid var(--color-drawer-border);
	}

	.header-title {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
		color: var(--color-text-primary);
		padding-right: 32px;
	}

	.header-subtitle {
		margin: 4px 0 0;
		font-size: 13px;
		color: #6b7280;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* ── Body ── */
	.body {
		flex: 1;
		padding: 20px 24px;
		display: flex;
		gap: 16px;
		align-items: stretch;
	}

	/* ── Relation center column ── */
	.relation-center {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 6px;
		min-width: 40px;
		flex-shrink: 0;
	}

	.direction-arrow {
		font-size: 16px;
		color: var(--color-text-faint);
		font-weight: 500;
	}

	/* ── Empty / loading state ── */
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		padding: 48px 24px;
		color: var(--color-text-muted);
		font-size: 14px;
	}

	/* ── Footer ── */
	.footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 24px;
		border-top: var(--border-width) solid var(--color-drawer-border);
		background-color: var(--color-drawer-bg);
		transition: background-color 300ms ease;
	}

	.footer.accepted {
		background-color: var(--color-success-bg);
	}

	.footer.rejected {
		background-color: #f9f9fb;
		opacity: 0.7;
	}

	/* ── Footer buttons ── */
	.btn-outline {
		display: inline-flex;
		align-items: center;
		padding: 6px 16px;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-control);
		background: none;
		font-size: 14px;
		font-weight: 500;
		color: var(--color-text-body);
		cursor: pointer;
	}

	.btn-outline:hover {
		background-color: var(--color-hover-bg);
	}

	.btn-danger {
		display: inline-flex;
		align-items: center;
		padding: 6px 16px;
		border: var(--border-width) solid var(--color-drawer-danger-text);
		border-radius: var(--radius-control);
		background: none;
		font-size: 13px;
		font-weight: 500;
		color: var(--color-drawer-danger-text);
		cursor: pointer;
	}

	.btn-danger:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-danger:hover:not(:disabled) {
		background-color: var(--color-drawer-danger-bg);
	}

	.btn-accept {
		display: inline-flex;
		align-items: center;
		padding: 6px 20px;
		border: none;
		border-radius: var(--radius-control);
		background-color: #16a34a;
		font-size: 14px;
		font-weight: 500;
		color: #ffffff;
		cursor: pointer;
	}

	.btn-accept:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-accept:hover:not(:disabled) {
		background-color: #15803d;
	}

	.btn-reject {
		display: inline-flex;
		align-items: center;
		padding: 6px 16px;
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-control);
		background: none;
		font-size: 14px;
		font-weight: 500;
		color: var(--color-text-muted);
		cursor: pointer;
	}

	.btn-reject:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-reject:hover:not(:disabled) {
		background-color: var(--color-hover-bg);
		color: var(--color-text-body);
	}

	.btn-refresh {
		display: inline-flex;
		align-items: center;
		padding: 6px 16px;
		border: none;
		border-radius: var(--radius-control);
		background-color: var(--color-brand);
		font-size: 13px;
		font-weight: 500;
		color: #ffffff;
		cursor: pointer;
	}

	.btn-refresh:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-refresh:hover:not(:disabled) {
		background-color: var(--color-brand-hover);
	}

	.btn-confirm {
		display: inline-flex;
		align-items: center;
		padding: 6px 16px;
		border: none;
		border-radius: var(--radius-control);
		background-color: var(--color-drawer-danger-text);
		font-size: 13px;
		font-weight: 500;
		color: #ffffff;
		cursor: pointer;
	}

	.btn-confirm:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-confirm:hover:not(:disabled) {
		background-color: #b91c1c;
	}

	/* Result labels */
	.result-label {
		font-size: 14px;
		font-weight: 600;
		padding: 6px 0;
	}

	.result-label.accepted {
		color: #16a34a;
	}

	.result-label.rejected {
		color: var(--color-text-muted);
	}
</style>