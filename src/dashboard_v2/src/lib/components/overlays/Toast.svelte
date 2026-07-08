<script lang="ts">
	import { toastStore, dismissToast, type Toast } from '$lib/toast.js';

	/** Icon color per toast type */
	const SWATCH: Record<Toast['type'], string> = {
		success: '#16a34a',
		error: '#dc2626',
		info: '#6b7280'
	};

	/** SVG path per toast type (simple check / x / i) */
	const ICONS: Record<Toast['type'], string> = {
		success: 'M5 13l4 4L19 7',
		error: 'M6 18L18 6M6 6l12 12',
		info: 'M12 8v4m0 4h.01'
	};
</script>

{#if $toastStore.length > 0}
	{@const toast = $toastStore[0]}
	<div
		class="toast-pill"
		role="status"
		aria-live="polite"
		aria-atomic="true"
		onclick={() => dismissToast(toast.id)}
		onkeydown={(e) => e.key === 'Enter' && dismissToast(toast.id)}
		tabindex="0"
	>
		<span class="swatch" style="color: {SWATCH[toast.type]}">
			<svg
				width="16"
				height="16"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2.5"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d={ICONS[toast.type]} />
			</svg>
		</span>
		<span class="message">{toast.message}</span>
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

		background: #1a1a2e;
		color: #ffffff;
		padding: 10px 18px;
		border-radius: var(--radius-pill, 999px);
		max-width: 420px;
		min-width: 200px;

		font-size: var(--font-size-body, 13px);
		line-height: 1.4;
		cursor: pointer;
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
