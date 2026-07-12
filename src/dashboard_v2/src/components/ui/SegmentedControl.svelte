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

	let tablistEl: HTMLDivElement | undefined = $state();

	function handleKeydown(e: KeyboardEvent) {
		const buttons = Array.from(tablistEl?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? []);
		if (buttons.length === 0) return;
		const currentIdx = buttons.indexOf(document.activeElement as HTMLButtonElement);
		if (currentIdx === -1) {
			const selectedIdx = options.findIndex((o) => o.value === value);
			if (selectedIdx !== -1) buttons[selectedIdx]?.focus();
			return;
		}
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			const next = (currentIdx + 1) % buttons.length;
			buttons[next].focus();
			onChange?.(options[next].value);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			const prev = (currentIdx - 1 + buttons.length) % buttons.length;
			buttons[prev].focus();
			onChange?.(options[prev].value);
		}
	}
</script>

<div
	bind:this={tablistEl}
	class="inline-flex rounded-lg p-0.5"
	role="tablist"
	tabindex="0"
	style="background-color: var(--color-seg-bg);"
	onkeydown={handleKeydown}
>
	{#each options as opt (opt.value)}
		<button
			type="button"
			class="rounded-md px-3.5 py-1 text-sm font-medium transition-colors duration-150"
			role="tab"
			aria-selected={opt.value === value}
			tabindex={opt.value === value ? 0 : -1}
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

	button[aria-selected='true'] {
		background-color: var(--color-seg-active-bg);
		color: var(--color-seg-active-text);
		font-weight: 600;
	}
</style>