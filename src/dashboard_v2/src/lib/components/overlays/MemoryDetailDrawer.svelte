<script lang="ts">
	import { tick } from 'svelte';
	import { DRAWER_STRINGS } from '$lib/constants/strings';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
	import ScorePill from '../../../components/ui/ScorePill.svelte';
	import NamespaceDot from '../../../components/ui/NamespaceDot.svelte';
	import RelationPill from '../../../components/ui/RelationPill.svelte';
	import type { NAMESPACE_COLORS, RELATION_STYLES } from '$lib/constants/primitives';
	import type { MemoryData, LinkData, MemoryEditFields } from './types';

	// ── Props ──────────────────────────────────────────────────────────────────

	interface Props {
		open: boolean;
		memory: MemoryData | null;
		links?: LinkData[];
		onClose: () => void;
		onSave: (id: string, fields: MemoryEditFields) => Promise<boolean> | void;
		onDelete: (id: string) => void;
		onNavigate: (targetId: string) => void;
	}

	let {
		open,
		memory,
		links = [],
		onClose,
		onSave,
		onDelete,
		onNavigate,
	}: Props = $props();

	// ── State ──────────────────────────────────────────────────────────────────

	let editMode = $state(false);
	let linksExpanded = $state(false);
	let copyTooltipVisible = $state(false);
	let drawerEl: HTMLElement | null = $state(null);
	let saveError = $state<string | null>(null);

	// Auto-focus drawer when it opens
	$effect(() => {
		if (open && memory && drawerEl) {
			void tick().then(() => { drawerEl?.focus(); });
		}
		if (!open) {
			saveError = null;
		}
	});

	// Edit form state (cloned from memory on edit entry)
	let editTitle = $state('');
	let editDescription = $state('');
	let editContent = $state('');
	let editScore = $state(0);
	let editSourceType = $state('');

	let dirty = $derived(
		editTitle !== (memory?.title ?? '') ||
		editDescription !== (memory?.description ?? '') ||
		editContent !== (memory?.content ?? '') ||
		editScore !== (memory?.score ?? 0) ||
		editSourceType !== (memory?.source_type ?? ''),
	);

	// ── Derived ────────────────────────────────────────────────────────────────

	let statusBadge = $derived.by(() => {
		if (!memory) return '';
		if (memory.soft_deleted) return DRAWER_STRINGS.statusDeleted;
		if (memory.score < 3) return DRAWER_STRINGS.statusDecaying;
		if (memory.confidence < 4) return DRAWER_STRINGS.statusLowConfidence;
		return DRAWER_STRINGS.statusActive;
	});

	let statusColor = $derived.by(() => {
		if (!memory) return 'transparent';
		if (memory.soft_deleted) return 'var(--color-drawer-status-deleted)';
		if (memory.score < 3) return 'var(--color-drawer-status-decaying)';
		if (memory.confidence < 4) return 'var(--color-drawer-status-low)';
		return 'var(--color-drawer-status-active)';
	});

	let formattedCreated = $derived.by(() => {
		if (!memory) return '';
		const d = new Date(memory.created_at);
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	});

	let formattedUpdated = $derived.by(() => {
		if (!memory) return '';
		const d = new Date(memory.updated_at);
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffDays = Math.floor(diffMs / 86400000);
		if (diffDays < 7) {
			if (diffDays === 0) return 'today';
			if (diffDays === 1) return '1d ago';
			return `${diffDays}d ago`;
		}
		return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	});

	// ── Type-safe cast helpers ─────────────────────────────────────────────────

	function ns(namespace: string): keyof typeof NAMESPACE_COLORS {
		return namespace as keyof typeof NAMESPACE_COLORS;
	}

	function rel(type: string): keyof typeof RELATION_STYLES {
		return type as keyof typeof RELATION_STYLES;
	}

	// ── Focus trap ─────────────────────────────────────────────────────────────

	const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

	

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

	// ── Handlers ───────────────────────────────────────────────────────────────

	function enterEditMode() {
		if (!memory) return;
		saveError = null;
		editTitle = memory.title;
		editDescription = memory.description;
		editContent = memory.content;
		editScore = memory.score;
		editSourceType = memory.source_type;
		editMode = true;
	}

	function handleClose() {
		if (editMode && dirty) {
			if (!confirm(DRAWER_STRINGS.discardConfirm)) return;
		}
		editMode = false;
		linksExpanded = false;
		copyTooltipVisible = false;
		saveError = null;
		onClose();
	}

	async function handleCopyId() {
		if (!memory) return;
		try {
			await navigator.clipboard.writeText(memory.lore_id);
			copyTooltipVisible = true;
			setTimeout(() => {
				copyTooltipVisible = false;
			}, 1500);
		} catch {
			// Clipboard API not available — silently fail
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		trapFocus(e);
		if (e.key === 'Escape') {
			e.preventDefault();
			handleClose();
		}
		if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
			if (editMode) {
				e.preventDefault();
				void handleSave();
			}
		}
	}

	function validateScore(val: number): string | null {
		if (typeof val !== 'number' || !isFinite(val)) return 'Score must be a number';
		if (val < 0 || val > 10) return 'Score must be between 0 and 10';
		return null;
	}

	async function handleSave() {
		if (!memory) return;

		const scoreError = validateScore(editScore);
		if (scoreError) {
			saveError = scoreError;
			return;
		}

		const result = onSave(memory.lore_id, {
			title: editTitle,
			description: editDescription,
			content: editContent,
			score: editScore,
			source_type: editSourceType,
		});

		if (result instanceof Promise) {
			const success = await result;
			if (!success) {
				saveError = 'Save failed. Please try again.';
				return;
			}
		}

		saveError = null;
		editMode = false;
	}

	function handleCancel() {
		if (dirty && !confirm(DRAWER_STRINGS.discardConfirm)) return;
		saveError = null;
		editMode = false;
	}

	function handleDelete() {
		if (!memory) return;
		if (!confirm(DRAWER_STRINGS.dangerZoneDelete)) return;
		onDelete(memory.lore_id);
	}

	function handleForget() {
		if (!memory) return;
		if (!confirm(DRAWER_STRINGS.dangerZoneForget)) return;
		void onSave(memory.lore_id, { soft_deleted: true });
	}
</script>

{#if open && memory}
	<OverlayScrim onclick={handleClose} />
	<div
		class="drawer"
		bind:this={drawerEl}
		role="dialog"
		aria-modal="true"
		aria-label={DRAWER_STRINGS.drawerAriaLabel}
		onkeydown={handleKeydown}
		tabindex="-1"
	>
		<!-- Close button -->
		<button
			type="button"
			class="close-btn"
			onclick={handleClose}
			aria-label={DRAWER_STRINGS.closeButtonAriaLabel}
		>
			&times;
		</button>

		<!-- Header: title + status badge -->
		<div class="header">
			<h2 class="title" class:strikethrough={memory.soft_deleted}>
				{memory.title}
			</h2>
			<span class="status-badge" style="background-color: {statusColor}">{statusBadge}</span>
		</div>

		<!-- Meta row -->
		<div class="meta-row">
			<NamespaceDot namespace={ns(memory.namespace)} />
			<span class="meta-value">{memory.namespace}</span>
			<span class="meta-divider" aria-hidden="true"></span>
			<span class="meta-label">{DRAWER_STRINGS.metaCreated}</span>
			<span class="meta-value">{formattedCreated}</span>
			<span class="meta-divider" aria-hidden="true"></span>
			<span class="meta-label">{DRAWER_STRINGS.metaUpdated}</span>
			<span class="meta-value">{formattedUpdated}</span>
			<span class="meta-divider" aria-hidden="true"></span>
			<ScorePill score={memory.score} />
			<span class="meta-divider" aria-hidden="true"></span>
			<span class="meta-label">{DRAWER_STRINGS.metaConfidence}</span>
			<span class="meta-value">{memory.confidence}/10</span>
			<div class="confidence-bar" style="width: {memory.confidence * 10}%;"></div>
			<span class="meta-divider" aria-hidden="true"></span>
			<span class="meta-label">{DRAWER_STRINGS.metaUsage}</span>
			<span class="meta-value">{memory.usage_count}</span>
		</div>

		<!-- Body -->
		<div class="body">
			{#if editMode}
				<!-- Edit mode: form fields -->
				<div class="edit-field">
					<label class="field-label" for="drawer-title">Title</label>
					<input type="text" id="drawer-title" class="input-title" bind:value={editTitle} />
				</div>
				<div class="edit-field">
					<label class="field-label" for="drawer-desc">Description</label>
					<textarea id="drawer-desc" class="textarea-desc" bind:value={editDescription}></textarea>
				</div>
				<div class="edit-field">
					<label class="field-label" for="drawer-content">Content</label>
					<textarea id="drawer-content" class="textarea-content" bind:value={editContent}></textarea>
				</div>
				<div class="edit-field edit-field-row">
					<div class="edit-field">
						<label class="field-label" for="drawer-score">{DRAWER_STRINGS.metaScore}</label>
						<input type="number" id="drawer-score" class="input-score" min="0" max="10" step="0.5" bind:value={editScore} />
					</div>
					<div class="edit-field">
						<label class="field-label" for="drawer-source">Source type</label>
						<select id="drawer-source" class="select-source" bind:value={editSourceType}>
							<option value="observed">observed</option>
							<option value="user_stated">user_stated</option>
							<option value="inferred">inferred</option>
							<option value="learned">learned</option>
						</select>
					</div>
				</div>

				{#if saveError}
					<div class="save-error" role="alert">{saveError}</div>
				{/if}

				<!-- Danger zone -->
				<div class="danger-zone">
					<h3 class="danger-zone-header">{DRAWER_STRINGS.dangerZoneHeader}</h3>
					<div class="danger-zone-actions">
						<button
							type="button"
							class="btn-danger"
							disabled={memory.soft_deleted}
							onclick={handleDelete}
						>
							{memory.soft_deleted ? DRAWER_STRINGS.dangerZoneAlreadyDeleted : DRAWER_STRINGS.dangerZoneDelete}
						</button>
						<button
							type="button"
							class="btn-danger-outline"
							disabled={memory.soft_deleted}
							onclick={handleForget}
						>
							{memory.soft_deleted ? DRAWER_STRINGS.dangerZoneAlreadyDeleted : DRAWER_STRINGS.dangerZoneForget}
						</button>
					</div>
				</div>
			{:else}
				<!-- View mode: display -->
				<div class="source-tag">{memory.source_type}</div>
				<p class="description">
					{memory.description || DRAWER_STRINGS.noDescription}
				</p>
				<div class="content-block">{memory.content}</div>
			{/if}
		</div>

		<!-- Links section -->
		<div class="links-section">
			<button
				type="button"
				class="links-toggle"
				aria-expanded={linksExpanded}
				aria-controls="drawer-links-list"
				onclick={() => (linksExpanded = !linksExpanded)}
			>
				{links.length} {DRAWER_STRINGS.linksHeader}
				<span class="toggle-arrow" data-expanded={linksExpanded}>&#9662;</span>
			</button>
			{#if linksExpanded}
				<div id="drawer-links-list" class="links-list">
					{#if links.length > 0}
						{#each links as link (link.target_id)}
							<button
								type="button"
								class="link-item"
								onclick={() => onNavigate(link.target_id)}
							>
								<RelationPill type={rel(link.relation_type)} />
								<span class="link-title">{link.target_title}</span>
							</button>
						{/each}
					{:else}
						<p class="links-empty">{DRAWER_STRINGS.linksEmpty}</p>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="footer">
			{#if editMode}
				<button type="button" class="btn-outline" onclick={handleCancel}>
					{DRAWER_STRINGS.footerCancel}
				</button>
				<button type="button" class="btn-primary" onclick={handleSave}>
					{DRAWER_STRINGS.footerSave}
				</button>
			{:else}
				<button type="button" class="btn-outline" onclick={handleCopyId}>
					{copyTooltipVisible ? DRAWER_STRINGS.copyIdTooltip : DRAWER_STRINGS.footerCopyId}
				</button>
				<button type="button" class="btn-primary" onclick={enterEditMode}>
					{DRAWER_STRINGS.footerEdit}
				</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	.drawer {
		position: fixed;
		top: 0;
		right: 0;
		width: 440px;
		height: 100vh;
		z-index: var(--z-drawer-top);
		background-color: var(--color-drawer-bg);
		box-shadow: var(--color-shadow-lg);
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		animation: slide-in 200ms ease forwards;
	}

	@keyframes slide-in {
		from { transform: translateX(100%); }
		to   { transform: translateX(0); }
	}

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
		font-size: var(--font-size-lg);
		color: var(--color-text-muted);
		cursor: pointer;
		border-radius: var(--radius-kbd);
	}

	.close-btn:hover {
		background-color: var(--color-hover-bg);
		color: var(--color-text-primary);
	}

	.header {
		padding: 24px 24px 12px;
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.title {
		margin: 0;
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		flex: 1;
		min-width: 0;
	}

	.strikethrough {
		text-decoration: line-through;
	}

	.status-badge {
		display: inline-flex;
		align-items: center;
		padding: 2px 8px;
		border-radius: var(--radius-pill);
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-on-filled);
		white-space: nowrap;
	}

	.meta-row {
		display: flex;
		align-items: center;
		gap: var(--space-1-5);
		padding: 8px 24px 12px;
		flex-wrap: wrap;
		border-bottom: var(--border-width) solid var(--color-drawer-border);
	}

	.meta-label {
		font-size: var(--font-size-micro);
		color: var(--color-text-faint);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.meta-value {
		font-size: var(--font-size-body);
		color: var(--color-text-body);
	}

	.meta-divider {
		width: var(--border-width);
		height: 16px;
		background-color: var(--color-drawer-divider);
	}

	.confidence-bar {
		height: 6px;
		background-color: var(--color-brand-primary);
		border-radius: var(--radius-xs);
		max-width: 40px;
	}

	.body {
		flex: 1;
		padding: 16px 24px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.source-tag {
		display: inline-flex;
		align-items: center;
		padding: 2px 8px;
		border-radius: var(--radius-pill);
		background-color: var(--color-brand-tint);
		color: var(--color-brand-primary);
		font-size: var(--font-size-micro);
		font-weight: var(--font-weight-medium);
		align-self: flex-start;
	}

	.description {
		margin: 0;
		font-size: var(--font-size-ui);
		color: var(--color-text-body);
		line-height: var(--line-height-normal);
	}

	.content-block {
		max-height: 300px;
		overflow-y: auto;
		font-family: ui-monospace, SFMono-Regular, monospace;
		font-size: var(--font-size-body);
		background-color: var(--color-drawer-code-bg);
		padding: var(--space-3);
		border-radius: var(--radius-md);
		border: var(--border-width) solid var(--color-drawer-code-border);
		color: var(--color-text-body);
		white-space: pre-wrap;
		word-break: break-all;
		line-height: var(--line-height-normal);
	}

	/* Edit mode form fields */
	.edit-field {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.edit-field-row {
		flex-direction: row;
		gap: var(--space-3);
	}

	.edit-field-row > .edit-field {
		flex: 1;
	}

	.field-label {
		font-size: var(--font-size-micro);
		color: var(--color-text-faint);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-weight: var(--font-weight-medium);
	}

	.input-title {
		font-size: var(--font-size-lg);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-control);
		padding: var(--space-1-5) var(--space-2);
		width: 100%;
	}

	.textarea-desc {
		font-size: var(--font-size-ui);
		color: var(--color-text-body);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-control);
		padding: var(--space-1-5) var(--space-2);
		min-height: 60px;
		resize: vertical;
		width: 100%;
		font-family: inherit;
	}

	.textarea-content {
		font-family: ui-monospace, SFMono-Regular, monospace;
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-control);
		padding: var(--space-2);
		min-height: 200px;
		resize: vertical;
		width: 100%;
		line-height: var(--line-height-normal);
	}

	.input-score {
		font-size: var(--font-size-ui);
		color: var(--color-text-body);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-control);
		padding: var(--space-1-5) var(--space-2);
		width: 80px;
	}

	.select-source {
		font-size: var(--font-size-ui);
		color: var(--color-text-body);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-control);
		padding: var(--space-1-5) var(--space-2);
		width: 100%;
		background-color: var(--color-surface);
		font-family: inherit;
	}

	/* Save error */
	.save-error {
		padding: var(--space-2) var(--space-3);
		border-radius: var(--radius-control);
		background-color: var(--color-drawer-danger-bg);
		border: var(--border-width) solid var(--color-drawer-danger-border);
		color: var(--color-drawer-danger-text);
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
	}

	/* Danger zone */
	.danger-zone {
		border: var(--border-width) solid var(--color-drawer-danger-border);
		border-radius: var(--radius-md);
		padding: var(--space-4);
		background-color: var(--color-drawer-danger-bg);
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.danger-zone-header {
		margin: 0;
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-semibold);
		color: var(--color-drawer-danger-text);
	}

	.danger-zone-actions {
		display: flex;
		gap: var(--space-2);
	}

	/* Links section */
	.links-section {
		padding: 0 24px 12px;
		border-top: var(--border-width) solid var(--color-drawer-border);
	}

	.links-toggle {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		width: 100%;
		padding: 10px 0;
		border: none;
		background: none;
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-primary);
		cursor: pointer;
	}

	.toggle-arrow {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		transition: transform 150ms ease;
	}

	.toggle-arrow[data-expanded='true'] {
		transform: rotate(180deg);
	}

	.links-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		padding-bottom: var(--space-2);
	}

	.link-item {
		display: flex;
		align-items: center;
		gap: var(--space-1-5);
		width: 100%;
		padding: var(--space-1-5) var(--space-2);
		border: none;
		background: none;
		cursor: pointer;
		border-radius: var(--radius-icon);
		text-align: left;
	}

	.link-item:hover {
		background-color: var(--color-hover-bg);
	}

	.link-title {
		font-size: var(--font-size-body);
		color: var(--color-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.links-empty {
		margin: 0;
		font-size: var(--font-size-body);
		color: var(--color-text-muted);
		padding: var(--space-1) var(--space-2);
	}

	/* Footer */
	.footer {
		position: sticky;
		bottom: 0;
		display: flex;
		justify-content: flex-end;
		gap: var(--space-2);
		padding: 12px 24px;
		border-top: var(--border-width) solid var(--color-drawer-border);
		background-color: var(--color-drawer-bg);
	}

	.btn-outline {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1-5) var(--space-4);
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-control);
		background: none;
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-body);
		cursor: pointer;
	}

	.btn-outline:hover {
		background-color: var(--color-hover-bg);
	}

	.btn-primary {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1-5) var(--space-4);
		border: none;
		border-radius: var(--radius-control);
		background-color: var(--color-brand-primary);
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-on-filled);
		cursor: pointer;
	}

	.btn-primary:hover {
		background-color: var(--color-brand-hover);
	}

	.btn-danger {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1-5) var(--space-4);
		border: var(--border-width) solid var(--color-drawer-danger-text);
		border-radius: var(--radius-control);
		background: none;
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
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

	.btn-danger-outline {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1-5) var(--space-4);
		border: var(--border-width) solid var(--color-warning-text);
		border-radius: var(--radius-control);
		background: none;
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
		color: var(--color-warning-text);
		cursor: pointer;
	}

	.btn-danger-outline:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-danger-outline:hover:not(:disabled) {
		background-color: var(--color-warning-bg);
	}
</style>