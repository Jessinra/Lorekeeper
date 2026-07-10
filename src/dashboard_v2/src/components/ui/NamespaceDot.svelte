<script lang="ts">
	import { namespaceColor } from '$lib/constants/primitives';
	import { NAMESPACE_DOT_STRINGS } from '$lib/constants/strings';

	let { namespace }: { namespace: string } = $props();

	const color = $derived(namespaceColor(namespace));
</script>

<span
	class="inline-block h-2 w-2 rounded-full"
	style="background-color: {color}"
	aria-hidden={NAMESPACE_DOT_STRINGS.ariaHidden}
></span>