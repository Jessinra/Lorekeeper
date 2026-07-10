<script lang="ts">
	import { scoreColor } from '$lib/constants/primitives';

	let { score }: { score: number } = $props();

	const bgColor = $derived(scoreColor(score));
</script>

<span
	class="inline-flex h-7 items-center rounded-full text-xs font-medium leading-none text-white pill"
	style="background-color: {bgColor}"
>
	{score}
</span>

<style>
	.pill {
		padding-inline: 10px;
	}
</style>