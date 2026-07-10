<script lang="ts">
	import { RELATION_STYLES, relationStyle, readableLabel } from '$lib/constants/primitives';

	let { type, label = readableLabel(type) }: { type: keyof typeof RELATION_STYLES; label?: string } = $props();

	const style = $derived(relationStyle(type));
</script>

<span
	class="inline-flex items-center rounded-full px-2.5 py-1.5 text-micro font-medium leading-none"
	style="background-color: {style.bg}; color: {style.text}"
>
	{label}
</span>