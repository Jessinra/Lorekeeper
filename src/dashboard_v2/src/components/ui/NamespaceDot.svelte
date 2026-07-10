<script lang="ts">
	import { namespaceColor } from '$lib/constants/primitives';
	import { NAMESPACE_DOT_STRINGS } from '$lib/constants/strings';
	import { NAMESPACE_COLORS } from '$lib/constants/primitives';

	let { namespace }: { namespace: keyof typeof NAMESPACE_COLORS } = $props();

	const color = $derived(namespaceColor(namespace));
</script>

<span
	class="inline-block h-2 w-2 rounded-full"
	style="background-color: {color}"
	aria-hidden={NAMESPACE_DOT_STRINGS.ariaHidden}
></span>