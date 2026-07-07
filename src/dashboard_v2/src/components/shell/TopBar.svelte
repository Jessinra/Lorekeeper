<script lang="ts">
	import { page } from '$app/stores';

	// Derive current page label from pathname
	const pageLabels: Record<string, string> = {
		'/': 'Home',
		'/memories': 'Memories',
		'/links': 'Links',
		'/query': 'Query',
		'/review': 'Review',
		'/sessions': 'Sessions',
		'/metrics': 'Metrics',
		'/settings': 'Settings'
	};

	$: currentLabel = (() => {
		const path = $page.url.pathname;
		// Match exact first, then prefix
		if (pageLabels[path]) return pageLabels[path];
		const match = Object.entries(pageLabels).find(
			([k]) => k !== '/' && path.startsWith(k)
		);
		return match ? match[1] : 'Home';
	})();
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
		<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
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
		padding: 0 28px;
		border-bottom: 1px solid var(--color-border);
		background: #fff;
		position: sticky;
		top: 0;
		z-index: 30;
	}

	.breadcrumb {
		display: flex;
		gap: 6px;
		align-items: center;
		font-size: 14px;
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
		border-radius: 6px;
		padding: 8px 10px;
		color: var(--color-text-faint);
		font-size: 13px;
		width: 230px;
		cursor: pointer;
		transition: border-color 0.15s, box-shadow 0.15s;
	}

	.search-trigger:hover {
		border-color: #c5c5d8;
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
		background: #fff;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		font-size: 10.5px;
		padding: 1px 5px;
		color: var(--color-text-muted);
		font-family: inherit;
	}
</style>
