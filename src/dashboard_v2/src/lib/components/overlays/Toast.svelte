<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';
	import { toastStore, dismissToast, type Toast } from '$lib/toast.js';
	import { ICON_CHECK, ICON_X_CLOSE, ICON_INFO_DOT } from '$lib/constants/icons.js';
	import { TOAST_STRINGS } from '$lib/constants/strings.js';

	/** Icon path per toast type */
	const ICONS: Record<Toast['type'], string> = {
		success: ICON_CHECK,
		error:   ICON_X_CLOSE,
		info:    ICON_INFO_DOT,
	};

	/** CSS variable name per toast type — resolves via design tokens */
	const ICON_COLOR_VAR: Record<Toast['type'], string> = {
		success: 'var(--color-success-text)',
		error:   'var(--color-danger-text)',
		info:    'var(--color-text-muted)',
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
			aria-label={TOAST_STRINGS.dismissAriaLabel}
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
		z-index: var(--z-modal);

		display: flex;
		align-items: center;
		gap: var(--space-2);

		background: var(--color-toast-bg);
		color: var(--color-toast-text);
		padding: 10px 18px;
		border-radius: var(--radius-pill);
		max-width: 420px;
		min-width: 200px;

		font-size: var(--font-size-body);
		line-height: var(--line-height-snug);
		cursor: default;
		user-select: none;

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
		color: var(--color-toast-dismiss);
		cursor: pointer;
		font-size: var(--font-size-title);
		line-height: var(--line-height-tight);
		padding: 0 0 0 4px;
		display: flex;
		align-items: center;
	}

	.dismiss-btn:hover {
		color: var(--color-toast-dismiss-hover);
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
