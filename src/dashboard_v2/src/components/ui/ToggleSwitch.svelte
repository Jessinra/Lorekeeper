<script lang="ts">
	import { TOGGLE_DEFAULTS } from '$lib/constants/primitives';

	let {
		checked,
		onChange,
		label,
	}: {
		checked: boolean;
		onChange?: (val: boolean) => void;
		label?: string;
	} = $props();

	function toggle() {
		onChange?.(!checked);
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<label
	class="inline-flex items-center gap-2 cursor-pointer"
	role="switch"
	aria-checked={checked}
	aria-label={label}
	onclick={toggle}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggle(); }}
	tabindex="0"
>
	<div class="track" data-on={checked}>
		<div class="thumb" data-on={checked}></div>
	</div>
	{#if label}
		<span class="text-sm select-none" style="color: var(--color-text-muted);">{label}</span>
	{/if}
</label>

<style>
	.track {
		width: {TOGGLE_DEFAULTS.trackWidth}px;
		height: {TOGGLE_DEFAULTS.trackHeight}px;
		border-radius: {TOGGLE_DEFAULTS.trackRadius}px;
		background-color: var(--color-toggle-off-bg);
		position: relative;
		transition: background-color 150ms ease;
	}

	.track[data-on='true'] {
		background-color: var(--color-toggle-on-bg);
	}

	.thumb {
		width: {TOGGLE_DEFAULTS.thumbSize}px;
		height: {TOGGLE_DEFAULTS.thumbSize}px;
		border-radius: 50%;
		background-color: var(--color-toggle-thumb-bg);
		position: absolute;
		top: {TOGGLE_DEFAULTS.thumbOffset}px;
		left: {TOGGLE_DEFAULTS.thumbOffset}px;
		transition: transform 150ms ease;
	}

	.thumb[data-on='true'] {
		transform: translateX({TOGGLE_DEFAULTS.thumbTranslate}px);
	}
</style>