<script lang="ts">
	import { page } from '$app/state';
	import { labelFromPath } from '$lib/constants/routes.js';
	import { COMMAND_PALETTE_HOTKEY } from '$lib/constants/keybindings.js';
	import { TOP_BAR_STRINGS } from '$lib/constants/strings.js';
	import { ICON_SEARCH } from '$lib/constants/icons.js';
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		onOpenPalette: () => void;
	}

	let { onOpenPalette }: Props = $props();

	const currentLabel = $derived(labelFromPath(page.url.pathname));

	// Derive the correct modifier symbol from config — stays in sync with hotkeys.ts
	// navigator.platform is deprecated; prefer userAgentData.platform (Chrome 90+)
	// with a userAgent fallback for Firefox/Safari.
	// Cast needed because userAgentData is not yet in the lib.dom typings.
	const ua = typeof navigator !== 'undefined'
		? (navigator as Navigator & { userAgentData?: { platform: string } })
		: null;
	const isMac = ua
		? (ua.userAgentData
			? ua.userAgentData.platform === 'macOS'
			: /Mac|iPhone|iPad|iPod/.test(navigator.userAgent))
		: false;
	const modifierDisplay = isMac
		? COMMAND_PALETTE_HOTKEY.macModifierDisplay
		: COMMAND_PALETTE_HOTKEY.otherModifierDisplay;
	const keyDisplay = COMMAND_PALETTE_HOTKEY.keyDisplay;
	const ariaKeyshortcuts = isMac
		? COMMAND_PALETTE_HOTKEY.macAriaKeyshortcuts
		: COMMAND_PALETTE_HOTKEY.otherAriaKeyshortcuts;
</script>

<header>
	<!-- Breadcrumb -->
	<nav class="breadcrumb" aria-label={TOP_BAR_STRINGS.breadcrumbNavAriaLabel}>
		<span class="breadcrumb-root">{TOP_BAR_STRINGS.breadcrumbRoot}</span>
		<span class="breadcrumb-sep" aria-hidden="true">/</span>
		<span class="breadcrumb-current">{currentLabel}</span>
	</nav>

	<!-- ⌘K search trigger -->
	<button
		class="search-trigger"
		type="button"
		aria-label="{TOP_BAR_STRINGS.searchTriggerPlaceholder} ({modifierDisplay}{keyDisplay})"
		aria-keyshortcuts={ariaKeyshortcuts}
		onclick={onOpenPalette}
	>
		<span class="search-icon" aria-hidden="true">
			<Icon path={ICON_SEARCH} size={15} strokeWidth={2} />
		</span>
		<span class="search-placeholder">{TOP_BAR_STRINGS.searchTriggerPlaceholder}</span>
		<span class="kbd-hints" aria-hidden="true">
			<kbd>{modifierDisplay}</kbd><kbd>{keyDisplay}</kbd>
		</span>
	</button>
</header>

<style>
	header {
		height: var(--top-bar-height);
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--space-topbar-x);
		border-bottom: var(--border-width) solid var(--color-border);
		background: var(--color-surface);
		position: sticky;
		top: 0;
		z-index: 30;
	}

	.breadcrumb {
		display: flex;
		gap: 6px;
		align-items: center;
		font-size: var(--font-size-breadcrumb);
	}

	.breadcrumb-root {
		color: var(--color-text-faint);
	}

	.breadcrumb-sep {
		color: var(--color-text-faint);
	}

	.breadcrumb-current {
		color: var(--color-text-primary);
		font-weight: 600;
	}

	.search-trigger {
		display: flex;
		align-items: center;
		gap: 8px;
		border: var(--border-width) solid var(--color-border);
		background: var(--color-background);
		border-radius: var(--radius-control);
		padding: 8px 10px;
		color: var(--color-text-faint);
		font-size: var(--font-size-body);
		width: 230px;
		cursor: pointer;
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
	}

	.search-trigger:hover {
		border-color: var(--color-border-strong);
	}

	.search-trigger:focus-visible {
		outline: none;
		border-color: var(--color-brand);
		box-shadow: 0 0 0 3px var(--color-brand-tint);
	}

	.search-icon {
		display: flex;
		align-items: center;
		flex-shrink: 0;
	}

	.search-placeholder {
		flex: 1;
		text-align: left;
	}

	.kbd-hints {
		display: flex;
		gap: 3px;
	}

	kbd {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-kbd);
		font-size: var(--font-size-label);
		padding: var(--space-kbd-pad);
		color: var(--color-text-muted);
		font-family: inherit;
	}
</style>
