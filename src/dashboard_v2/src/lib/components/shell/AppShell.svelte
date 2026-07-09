<script lang="ts">
	import NavRail from '$lib/components/shell/NavRail.svelte';
	import TopBar from '$lib/components/shell/TopBar.svelte';
	import Toast from '$lib/components/overlays/Toast.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="app-frame">
	<NavRail />
	<div class="main-column">
		<TopBar />
		<main class="page-body">
			{@render children()}
		</main>
	</div>
	<Toast />
</div>

<style>
	.app-frame {
		display: flex;
		min-height: 100vh;
	}

	/* Offset main column past the fixed nav rail */
	.main-column {
		margin-left: var(--nav-rail-width);
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.page-body {
		flex: 1;
		padding: var(--space-page-y-top) var(--space-page-x) var(--space-page-y-bottom);
	}
</style>
