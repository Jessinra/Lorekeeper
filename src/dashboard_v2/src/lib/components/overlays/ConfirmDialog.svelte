<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import OverlayScrim from '$lib/components/ui/OverlayScrim.svelte';

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
		neutral: 'var(--color-hover-bg)',
		destructive: 'var(--color-danger-bg)'
	} as const;

	const SWATCH_ICON_VAR = {
		neutral: 'var(--color-text-muted)',
		destructive: 'var(--color-danger-text)'
	} as const;

	const SWATCH_PATH = {
		neutral:
			'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
		destructive:
			'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16'
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
			// Defer so the DOM is painted
			requestAnimationFrame(() => cancelBtn?.focus());
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
				Cancel
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
		z-index: 801;
		margin: auto;

		/* Center via transform */
		width: min(420px, calc(100vw - 32px));
		height: fit-content;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);

		background: var(--color-surface);
		border-radius: var(--radius-card);
		padding: 28px 28px 24px;
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.08),
			0 20px 40px -8px rgba(0, 0, 0, 0.16);

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
		margin-bottom: 16px;
		flex-shrink: 0;
	}

	.dialog-title {
		font-size: 16px;
		font-weight: 700;
		color: var(--color-text-primary);
		margin: 0 0 8px;
		line-height: 1.3;
	}

	.dialog-body {
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		margin: 0 0 16px;
		line-height: 1.5;
	}

	.item-chip {
		display: inline-block;
		background: var(--color-hover-bg);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-control);
		padding: 4px 10px;
		font-size: var(--font-size-body);
		color: var(--color-text-body);
		margin-bottom: 20px;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 4px;
	}

	/* Shared button base */
	button {
		padding: 8px 16px;
		border-radius: var(--radius-control);
		font-size: var(--font-size-body);
		font-weight: 500;
		cursor: pointer;
		border: none;
		line-height: 1;
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
		color: #ffffff;
	}

	.btn-confirm:hover {
		background: var(--color-brand-hover);
	}

	.btn-confirm.danger {
		background: var(--color-danger-text);
	}

	.btn-confirm.danger:hover {
		background: #b91c1c;
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
