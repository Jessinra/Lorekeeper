<script lang="ts">
	import { STAT_TILE_STRINGS } from '$lib/constants/strings';

	interface StatusPill {
		text: string;
		color: string;
	}

	let {
		icon,
		value,
		label,
		statusPill,
	}: {
		icon: string;
		value: string;
		label: string;
		statusPill?: StatusPill;
	} = $props();
</script>

<div class="relative flex flex-col rounded-xl border p-4 shadow-sm" style="background-color: var(--color-stat-bg); border-color: var(--color-stat-border);">
	{#if statusPill}
		<span
			class="absolute right-3 top-3 rounded-full px-2 py-0.5 text-xs font-medium leading-none"
			style="background-color: {statusPill.color}; color: var(--color-stat-pill-text);"
		>
			{statusPill.text}
		</span>
	{/if}

	<div class="mb-2 h-6 w-6" aria-hidden={STAT_TILE_STRINGS.iconAriaHidden} style="color: var(--color-stat-icon);">{@html icon}</div>

	<div class="stat-value" style="color: var(--color-stat-value);">{value}</div>
	<div class="mt-0.5 text-xs" style="color: var(--color-stat-label);">{label}</div>
</div>

<style>
	.stat-value {
		font-size: var(--font-size-stat);
		font-weight: var(--font-weight-bold);
	}
</style>