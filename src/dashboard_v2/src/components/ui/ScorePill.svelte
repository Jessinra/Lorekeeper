<script lang="ts">
	import { scoreColor } from '$lib/constants/primitives';

	let { score }: { score: number } = $props();

	const bgColor = $derived(scoreColor(score));
</script>

<span
	class="inline-flex h-7 items-center rounded-full px-2.5 text-xs font-medium leading-none text-white"
	style="background-color: {bgColor}"
>
	{score}
</span>