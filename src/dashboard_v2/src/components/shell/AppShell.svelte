<script lang="ts">
	import NavRail from './NavRail.svelte';
	import TopBar from './TopBar.svelte';
</script>

<div class="app-frame">
	<NavRail />
	<div class="main-column">
		<TopBar />
		<main class="page-body">
			<slot />
		</main>
	</div>
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
		padding: 26px 32px 44px;
	}
</style>
