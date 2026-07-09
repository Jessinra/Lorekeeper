<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';
	import { toastStore, dismissToast, type Toast } from '$lib/toast.js';

	/** Icon path per toast type (24×24 viewBox, check / x / i-dot) */
	const ICONS: Record<Toast['type'], string> = {
		success: 'M5 13l4 4L19 7',
		error: 'M6 18L18 6M6 6l12 12',
		info: 'M12 8v4m0 4h.01'
	};

	/** CSS variable name per toast type — resolves via design tokens */
	const ICON_COLOR_VAR: Record<Toast['type'], string> = {
		success: 'var(--color-success-text)',
		error: 'var(--color-danger-text)',
		info: 'var(--color-text-muted)'
	};
</script>

{#if $toastStore.length > 0}
	{@const toast = $toastStore[0]}
	<div
		class="toast-pill"
		role="status"
		aria-live="polite"
		aria-atomic="true"
	>
		<span class="swatch" style="color: {ICON_COLOR_VAR[toast.type]}">
			<Icon path={ICONS[toast.type]} size={16} strokeWidth={2.5} />
		</span>
		<span class="message">{toast.message}</span>
		<button
			class="dismiss-btn"
			type="button"
			aria-label="Dismiss notification"
			onclick={() => dismissToast(toast.id)}
		>×</button>
	</div>
{/if}

<style>
	.toast-pill {
		position: fixed;
		bottom: 28px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 900;

		display: flex;
		align-items: center;
		gap: 8px;

		background: rgba(17, 17, 17, 0.9);
		color: #ffffff;
		padding: 10px 18px;
		border-radius: var(--radius-pill);
		max-width: 420px;
		min-width: 200px;

		font-size: var(--font-size-body);
		line-height: 1.4;
		cursor: default;
		user-select: none;

		/* Entrance */
		animation: toast-in 200ms ease forwards;
	}

	.swatch {
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.message {
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.dismiss-btn {
		flex-shrink: 0;
		background: transparent;
		border: none;
		color: rgba(255, 255, 255, 0.6);
		cursor: pointer;
		font-size: 16px;
		line-height: 1;
		padding: 0 0 0 4px;
		display: flex;
		align-items: center;
	}

	.dismiss-btn:hover {
		color: #ffffff;
	}

	@keyframes toast-in {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}
</style>
