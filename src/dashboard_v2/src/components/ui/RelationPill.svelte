<script lang="ts">
	import { RELATION_STYLES, RELATION_FALLBACK_STYLE, readableLabel } from '$lib/constants/primitives';

	let { type, label = readableLabel(type) }: { type: string; label?: string } = $props();

	const style = $derived(RELATION_STYLES[type] ?? RELATION_FALLBACK_STYLE);
</script>

<span
	class="inline-flex items-center rounded-full py-1.5 text-micro font-medium leading-none pill"
	style="background-color: {style.bg}; color: {style.text}"
>
	{label}
</span>

<style>
	.pill {
		padding-inline: 10px;
	}
</style>