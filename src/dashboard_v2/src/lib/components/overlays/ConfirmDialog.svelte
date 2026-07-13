<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';
	import {
		ICON_INFO_CIRCLE,
		ICON_TRASH,
	} from '$lib/constants/icons.js';
	import { CONFIRM_STRINGS } from '$lib/constants/strings.js';

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		severity?: 'neutral' | 'destructive';
		itemName?: string | null;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open,
		title,
		message,
		confirmLabel = 'Delete',
		severity = 'destructive',
		itemName = null,
		onConfirm,
		onCancel
	}: Props = $props();

	/** Resolves via design tokens — no raw hex in logic */
	const SWATCH_BG_VAR = {
		neutral:     'var(--color-hover-bg)',
		destructive: 'var(--color-danger-bg)',
	} as const;

	const SWATCH_ICON_VAR = {
		neutral:     'var(--color-text-muted)',
		destructive: 'var(--color-danger-text)',
	} as const;

	const SWATCH_PATH = {
		neutral:     ICON_INFO_CIRCLE,
		destructive: ICON_TRASH,
	} as const;

	let dialogEl: HTMLDivElement | null = $state(null);
	let cancelBtn: HTMLButtonElement | null = $state(null);

	/** Focus trap: keep Tab/Shift-Tab inside dialog */
	function trapFocus(e: KeyboardEvent) {
		if (!open || !dialogEl) return;

		if (e.key === 'Escape') {
			onCancel();
			return;
		}

		if (e.key !== 'Tab') return;

		const focusable = Array.from(
			dialogEl.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			)
		).filter((el) => !el.hasAttribute('disabled'));

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

	$effect(() => {
		if (open && cancelBtn) {
			requestAnimationFrame(() => cancelBtn.focus());
		}
	});

	onMount(() => {
		window.addEventListener('keydown', trapFocus);
		return () => window.removeEventListener('keydown', trapFocus);
	});
</script>

{#if open}
	<OverlayScrim onclick={onCancel} />

	<div
		class="dialog-card"
		role="dialog"
		aria-modal="true"
		aria-labelledby="dialog-title"
		aria-describedby="dialog-body"
		bind:this={dialogEl}
	>
		<!-- Icon swatch -->
		<div
			class="icon-swatch"
			style="background: {SWATCH_BG_VAR[severity]}; color: {SWATCH_ICON_VAR[severity]}"
		>
			<Icon path={SWATCH_PATH[severity]} size={22} strokeWidth={2} />
		</div>

		<!-- Text content -->
		<h2 id="dialog-title" class="dialog-title">{title}</h2>
		<p id="dialog-body" class="dialog-body">{message}</p>

		<!-- Optional item chip -->
		{#if itemName}
			<div class="item-chip">{itemName}</div>
		{/if}

		<!-- Actions -->
		<div class="dialog-actions">
			<button class="btn-cancel" type="button" bind:this={cancelBtn} onclick={onCancel}>
				{CONFIRM_STRINGS.cancelLabel}
			</button>
			<button
				class="btn-confirm"
				class:danger={severity === 'destructive'}
				type="button"
				onclick={onConfirm}
			>
				{confirmLabel}
			</button>
		</div>
	</div>
{/if}

<style>
	.dialog-card {
		position: fixed;
		inset: 0;
		z-index: var(--z-drawer-top);
		margin: auto;

		width: min(420px, calc(100vw - 32px));
		height: fit-content;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);

		background: var(--color-surface);
		border-radius: var(--radius-card);
		padding: 28px 28px 24px;
		box-shadow:
			0 4px 6px -1px var(--color-shadow-sm),
			0 20px 40px -8px var(--color-shadow-md);

		display: flex;
		flex-direction: column;
		gap: 0;

		animation: card-in 200ms ease forwards;
	}

	.icon-swatch {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: var(--space-4);
		flex-shrink: 0;
	}

	.dialog-title {
		font-size: var(--font-size-title);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		margin: 0 0 8px;
		line-height: var(--line-height-snug);
	}

	.dialog-body {
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		margin: 0 0 16px;
		line-height: var(--line-height-normal);
	}

	.item-chip {
		display: inline-block;
		background: var(--color-hover-bg);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-control);
		padding: 4px 10px;
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		margin-bottom: var(--space-5);
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-2);
		margin-top: var(--space-1);
	}

	/* Shared button base */
	button {
		padding: 8px 16px;
		border-radius: var(--radius-control);
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
		border: none;
		line-height: var(--line-height-tight);
		transition: background 120ms ease;
	}

	.btn-cancel {
		background: var(--color-hover-bg);
		color: var(--color-text-body);
	}

	.btn-cancel:hover {
		background: var(--color-border);
	}

	.btn-confirm {
		background: var(--color-brand);
		color: var(--color-text-on-filled);
	}

	.btn-confirm:hover {
		background: var(--color-brand-hover);
	}

	.btn-confirm.danger {
		background: var(--color-danger-text);
	}

	.btn-confirm.danger:hover {
		background: var(--color-danger-hover);
	}

	@keyframes card-in {
		from {
			opacity: 0;
			transform: translate(-50%, calc(-50% + 8px)) scale(0.97);
		}
		to {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1);
		}
	}
</style>
