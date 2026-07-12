<script lang="ts">
	import { page } from '$app/state';
	import { NAV_ROUTES, UTILITY_ROUTES, matchRoute, type NavRoute } from '$lib/constants/routes.js';
	import { NAV_RAIL_STRINGS } from '$lib/constants/strings.js';

	function isActive(href: string): boolean {
		return matchRoute(page.url.pathname, href);
	}
</script>

{#snippet railLink(route: NavRoute)}
	<a
		href={route.href} data-sveltekit-preload-data
		class="rail-item"
		class:active={isActive(route.href)}
		aria-label={route.label}
		aria-current={isActive(route.href) ? 'page' : undefined}
	>
		<svg
			width="19"
			height="19"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d={route.icon} />
		</svg>
		<span class="label">{route.label}</span>
		{#if route.badge}
			<span class="badge" aria-label="{route.badge} {NAV_RAIL_STRINGS.badgePendingSuffix}">{route.badge}</span>
		{/if}
	</a>
{/snippet}

<nav aria-label={NAV_RAIL_STRINGS.navAriaLabel}>
	<!-- Brand mark -->
	<div class="brand">
		<img
			src="/logo.svg"
			alt={NAV_RAIL_STRINGS.logoAlt}
			width="36"
			height="36"
		/>
	</div>

	<!-- Primary nav items -->
	<div class="nav-items">
		{#each NAV_ROUTES as item (item.href)}
			{@render railLink(item)}
		{/each}
	</div>

	<!-- Spacer -->
	<div class="spacer" aria-hidden="true"></div>

	<!-- Utility items (settings) + health dot -->
	<div class="bottom-section">
		{#each UTILITY_ROUTES as item (item.href)}
			{@render railLink(item)}
		{/each}
		<div
			class="health-dot"
			title={NAV_RAIL_STRINGS.healthDotTitle}
			aria-label={NAV_RAIL_STRINGS.healthDotAriaLabel}
		></div>
	</div>
</nav>

<style>
	nav {
		width: var(--nav-rail-width);
		flex-shrink: 0;
		background: var(--color-surface);
		border-right: var(--border-width) solid var(--color-border);
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--space-rail-y-top) 0 var(--space-rail-y-bottom);
		position: fixed;
		top: 0;
		bottom: 0;
		left: 0;
		z-index: 40;
	}

	.brand {
		width: var(--brand-mark-size);
		height: var(--brand-mark-size);
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 24px;
		flex-shrink: 0;
	}

	.brand img {
		width: 100%;
		height: 100%;
		border-radius: var(--radius-icon);
	}

	.nav-items {
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		align-items: center;
	}

	.rail-item {
		width: var(--rail-item-width);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 7px 2px 8px;
		border: none;
		background: transparent;
		border-radius: var(--radius-icon);
		color: var(--color-text-muted);
		font-size: var(--font-size-label);
		font-weight: 500;
		position: relative;
		cursor: pointer;
		text-decoration: none;
		transition:
			background 0.1s,
			color 0.1s;
	}

	.rail-item:hover {
		background: var(--color-hover-bg);
		color: var(--color-text-primary);
	}

	.rail-item.active {
		background: var(--color-brand-tint);
		color: var(--color-brand);
		font-weight: 600;
	}

	.label {
		font-size: var(--font-size-label);
		line-height: 1;
	}

	.badge {
		position: absolute;
		top: 2px;
		right: 6px;
		background: var(--color-danger-text);
		color: var(--color-surface);
		font-size: var(--font-size-badge);
		font-weight: 700;
		min-width: 15px;
		height: 15px;
		border-radius: var(--radius-pill);
		text-align: center;
		line-height: 15px;
		padding: 0 3px;
	}

	.spacer {
		flex: 1;
	}

	.bottom-section {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}

	.health-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--color-success-text);
	}
</style>
