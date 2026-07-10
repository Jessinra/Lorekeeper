<script lang="ts">
	let {
		label,
		active = false,
		count,
		onToggle,
	}: {
		label: string;
		active?: boolean;
		count?: number;
		onToggle?: () => void;
	} = $props();
</script>

<button
	class="inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-150"
	data-active={active}
	onclick={() => onToggle?.()}
	aria-pressed={active}
>
	{label}
	{#if count !== undefined}
		<span class="ml-0.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium"
			data-active={active}
		>{count}</span>
	{/if}
</button>

<style>
	button {
		border-color: var(--color-chip-border);
		color: var(--color-chip-text);
		background-color: var(--color-chip-bg);
	}

	button[data-active='true'] {
		border-color: var(--color-chip-active-border);
		color: var(--color-chip-active-text);
		background-color: var(--color-chip-active-bg);
	}

	button:hover:not([data-active='true']) {
		background-color: var(--color-chip-hover-bg);
	}

	span {
		background-color: var(--color-chip-count-bg);
		color: var(--color-chip-count-text);
	}

	span[data-active='true'] {
		background-color: var(--color-chip-count-active-bg);
		color: var(--color-chip-count-text);
	}
</style>