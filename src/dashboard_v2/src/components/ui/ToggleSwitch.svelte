<script lang="ts">
	import { TOGGLE_DEFAULTS } from '$lib/constants/primitives';

	let {
		checked,
		onChange,
		label,
		ariaLabel,
	}: {
		checked: boolean;
		onChange?: (val: boolean) => void;
		label?: string;
		ariaLabel?: string;
	} = $props();

	const accessibleLabel = $derived(ariaLabel ?? (label ? `${label}, toggle` : 'Toggle switch'));

	function toggle() {
		onChange?.(!checked);
	}</script>

	<div
		class="inline-flex items-center gap-2 cursor-pointer"
		role="switch"
		aria-checked={checked}
		aria-label={accessibleLabel}
		onclick={toggle}
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }}}
		tabindex="0"
	>
	<div
		class="track"
		data-on={checked}
		style="width: {TOGGLE_DEFAULTS.trackWidth}px; height: {TOGGLE_DEFAULTS.trackHeight}px; border-radius: {TOGGLE_DEFAULTS.trackRadius}px;"
	>
		<div
			class="thumb"
			data-on={checked}
			style="width: {TOGGLE_DEFAULTS.thumbSize}px; height: {TOGGLE_DEFAULTS.thumbSize}px; top: {TOGGLE_DEFAULTS.thumbOffset}px; left: {TOGGLE_DEFAULTS.thumbOffset}px; transform: {checked ? `translateX(${TOGGLE_DEFAULTS.thumbTranslate}px)` : 'none'};"
		></div>
	</div>
	{#if label}
		<span class="text-sm select-none" style="color: var(--color-text-muted);">{label}</span>
	{/if}
</div>

<style>
	.track {
		background-color: var(--color-toggle-off-bg);
		position: relative;
		transition: background-color 150ms ease;
	}

	.track[data-on='true'] {
		background-color: var(--color-toggle-on-bg);
	}

	.thumb {
		border-radius: 50%;
		background-color: var(--color-toggle-thumb-bg);
		position: absolute;
		transition: transform 150ms ease;
	}
</style>