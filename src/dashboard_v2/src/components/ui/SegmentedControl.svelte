<script lang="ts">
	interface Option {
		value: string;
		label: string;
	}

	let {
		options,
		value,
		onChange,
	}: {
		options: Option[];
		value: string;
		onChange?: (val: string) => void;
	} = $props();
</script>

<div class="inline-flex rounded-lg p-0.5" role="tablist" style="background-color: var(--color-seg-bg);">
	{#each options as opt}
		<button
			class="rounded-md px-3.5 py-1 text-sm font-medium transition-colors duration-150"
			data-active={opt.value === value}
			role="tab"
			aria-selected={opt.value === value}
			onclick={() => onChange?.(opt.value)}
		>
			{opt.label}
		</button>
	{/each}
</div>

<style>
	button {
		background-color: transparent;
		color: var(--color-seg-inactive-text);
	}

	button[data-active='true'] {
		background-color: var(--color-seg-active-bg);
		color: var(--color-seg-active-text);
		font-weight: 600;
	}
</style>