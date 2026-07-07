<script lang="ts">
	import { page } from '$app/state';
	import { labelFromPath } from '$lib/constants/routes.js';

	const currentLabel = $derived(labelFromPath(page.url.pathname));
</script>

<header>
	<!-- Breadcrumb -->
	<div class="breadcrumb" aria-label="Breadcrumb">
		<span class="breadcrumb-root">Lorekeeper</span>
		<span class="breadcrumb-sep" aria-hidden="true">/</span>
		<span class="breadcrumb-current">{currentLabel}</span>
	</div>

	<!-- ⌘K search trigger -->
	<button
		class="search-trigger"
		type="button"
		aria-label="Search or jump to… (⌘K)"
		aria-keyshortcuts="Meta+k"
	>
		<svg
			width="15"
			height="15"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			aria-hidden="true"
		>
			<circle cx="11" cy="11" r="7" />
			<path d="M21 21l-4.3-4.3" />
		</svg>
		<span class="search-placeholder">Search or jump to…</span>
		<span class="kbd-hints" aria-hidden="true">
			<kbd>⌘</kbd><kbd>K</kbd>
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
		border-bottom: 1px solid var(--color-border);
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
		border: 1px solid var(--color-border);
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
		border: 1px solid var(--color-border);
		border-radius: var(--radius-kbd);
		font-size: var(--font-size-label);
		padding: 1px 5px;
		color: var(--color-text-muted);
		font-family: inherit;
	}
</style>
