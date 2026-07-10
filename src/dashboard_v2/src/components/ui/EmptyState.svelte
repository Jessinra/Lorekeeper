<script lang="ts">
	import { EMPTY_STATE_STRINGS } from '$lib/constants/strings';

	interface Action {
		label: string;
		onClick: () => void;
	}

	let {
		icon,
		title,
		message,
		action,
	}: {
		icon?: string;
		title: string;
		message: string;
		action?: Action;
	} = $props();
</script>

<div class="flex flex-col items-center justify-center px-6 py-16">
	{#if icon}
		<!-- svelte-ignore a11y_no_svg_title -->
		<div class="mb-4 h-12 w-12" aria-hidden={EMPTY_STATE_STRINGS.iconAriaHidden} style="color: var(--color-empty-icon);">{@html icon}</div>
	{/if}

	<h3 class="text-base font-semibold" style="color: var(--color-empty-title);">{title}</h3>
	<p class="mt-1 max-w-xs text-center text-sm" style="color: var(--color-empty-message);">{message}</p>

	{#if action}
		<button
			class="mt-4 rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors duration-150"
			style="background-color: var(--color-empty-action-bg);"
			onclick={action.onClick}
		>
			{action.label}
		</button>
	{/if}
</div>