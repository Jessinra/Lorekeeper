<script lang="ts">
	import '../app.css';
	import AppShell from '$lib/components/shell/AppShell.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<AppShell>
	{@render children()}
</AppShell>
