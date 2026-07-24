<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import NavRail from '$lib/components/shell/NavRail.svelte';
	import TopBar from '$lib/components/shell/TopBar.svelte';
	import Toast from '$lib/components/overlays/Toast.svelte';
	import CommandPalette from '$lib/components/overlays/CommandPalette.svelte';
	import { attachCommandPaletteHotkey } from '$lib/hotkeys.js';
	import { buildCommands } from '$lib/commands.js';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	// ─── Command Palette ──────────────────────────────────────────────────────
	// Commands are built here — the composition root that knows about SvelteKit
	// routing. CommandPalette.svelte is a pure UI component and receives them
	// as a prop, keeping it framework-agnostic and independently testable.
	const paletteCommands = buildCommands({
		navigate: (href) => {
			goto(href);
		},
		openQuery: () => {
			goto('/query');
		},
		openSettings: () => {
			goto('/settings');
		}
	});

	let paletteOpen = $state(false);

	function openPalette() {
		paletteOpen = true;
	}

	function closePalette() {
		paletteOpen = false;
	}

	onMount(() => {
		const cleanup = attachCommandPaletteHotkey(openPalette);
		return cleanup;
	});
</script>

<div class="app-frame">
	<NavRail />
	<div class="main-column">
		<TopBar onOpenPalette={openPalette} />
		<main class="page-body">
			{@render children()}
		</main>
	</div>
	<Toast />
	<CommandPalette open={paletteOpen} commands={paletteCommands} onClose={closePalette} />
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
