<script lang="ts">
	import { page } from '$app/stores';

	interface NavItem {
		href: string;
		label: string;
		icon: string; // SVG path data (viewBox="0 0 24 24")
		badge?: number;
	}

	const navItems: NavItem[] = [
		{
			href: '/',
			label: 'Home',
			icon: 'M3 11l9-8 9 8M5 10v10h14V10'
		},
		{
			href: '/memories',
			label: 'Memories',
			icon: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'
		},
		{
			href: '/links',
			label: 'Links',
			icon: 'M5 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M19 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M12 19m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M7 7.3L10.2 16.5M17 7.3L13.8 16.5M7.5 6H16.5'
		},
		{
			href: '/query',
			label: 'Query',
			icon: 'M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0M21 21l-4.3-4.3'
		},
		{
			href: '/review',
			label: 'Review',
			icon: 'M4 4h16v12H8l-4 4V4zM4 12h5l2 3h2l2-3h5',
			badge: 8
		},
		{
			href: '/sessions',
			label: 'Sessions',
			icon: 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M12 7v5l4 2'
		},
		{
			href: '/metrics',
			label: 'Metrics',
			icon: 'M4 20V10M12 20V4M20 20v-7'
		}
	];

	$: currentPath = $page.url.pathname;

	function isActive(href: string): boolean {
		if (href === '/') return currentPath === '/';
		return currentPath.startsWith(href);
	}
</script>

<nav aria-label="Primary navigation">
	<!-- Brand mark -->
	<div class="brand">
		<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
			<path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z" />
		</svg>
	</div>

	<!-- Primary nav items -->
	<div class="nav-items">
		{#each navItems as item}
			<a
				href={item.href}
				class="rail-item"
				class:active={isActive(item.href)}
				aria-label={item.label}
				aria-current={isActive(item.href) ? 'page' : undefined}
			>
				<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d={item.icon} />
				</svg>
				<span class="label">{item.label}</span>
				{#if item.badge}
					<span class="badge" aria-label="{item.badge} pending">{item.badge}</span>
				{/if}
			</a>
		{/each}
	</div>

	<!-- Spacer -->
	<div class="spacer" aria-hidden="true"></div>

	<!-- Settings + health dot -->
	<div class="bottom-section">
		<a
			href="/settings"
			class="rail-item"
			class:active={isActive('/settings')}
			aria-label="Settings"
			aria-current={isActive('/settings') ? 'page' : undefined}
		>
			<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
				<circle cx="12" cy="12" r="3.2" />
				<path d="M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
			</svg>
			<span class="label">Settings</span>
		</a>
		<div class="health-dot" title="System healthy" aria-label="System status: healthy"></div>
	</div>
</nav>

<style>
	nav {
		width: var(--nav-rail-width);
		flex-shrink: 0;
		background: #fff;
		border-right: 1px solid var(--color-border);
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 16px 0 12px;
		position: fixed;
		top: 0;
		bottom: 0;
		left: 0;
		z-index: 40;
	}

	.brand {
		width: 36px;
		height: 36px;
		border-radius: 8px;
		background: var(--color-brand);
		color: #fff;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 24px;
		flex-shrink: 0;
	}

	.nav-items {
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		align-items: center;
	}

	.rail-item {
		width: 58px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 7px 2px 8px;
		border: none;
		background: transparent;
		border-radius: 8px;
		color: var(--color-text-muted);
		font-size: 10.5px;
		font-weight: 500;
		position: relative;
		cursor: pointer;
		text-decoration: none;
		transition: background 0.1s, color 0.1s;
	}

	.rail-item:hover {
		background: #f4f4f6;
		color: var(--color-text-primary);
	}

	.rail-item.active {
		background: var(--color-brand-tint);
		color: var(--color-brand);
		font-weight: 600;
	}

	.label {
		font-size: 10.5px;
		line-height: 1;
	}

	.badge {
		position: absolute;
		top: 2px;
		right: 6px;
		background: var(--color-danger-text);
		color: #fff;
		font-size: 9px;
		font-weight: 700;
		min-width: 15px;
		height: 15px;
		border-radius: 999px;
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
