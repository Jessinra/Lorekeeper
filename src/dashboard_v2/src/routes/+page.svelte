<script lang="ts">
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import HealthRing from '../components/ui/HealthRing.svelte';
	import StatTile from '../components/ui/StatTile.svelte';
	import ActivityFeed from '../components/ui/ActivityFeed.svelte';
	import { fetchHealth, type HealthData } from '$lib/api/health';
	import { HOME_STRINGS as S } from '$lib/constants/strings';
	import { ICON_MEMORIES, ICON_LINKS, ICON_REVIEW, ICON_SESSIONS } from '$lib/constants/icons';
	import { onMount } from 'svelte';

	// Build inline SVG string for StatTile icon prop
	function svgIcon(path: string): string {
		return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}" /></svg>`;
	}

	let health = $state<HealthData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			health = await fetchHealth();
		} catch (e) {
			error = S.loadError;
		} finally {
			loading = false;
		}
	});
</script>

<PageShell title={S.pageTitle} subtitle={S.pageSubtitle}>
	{#if loading}
		<div class="home-loading" aria-busy="true">Loading…</div>
	{:else if error}
		<div class="home-error" role="alert">{error}</div>
	{:else if health}
		<div class="home-layout">
			<!-- Health card -->
			<section class="health-card" aria-labelledby="health-card-title">
				<h2 id="health-card-title" class="section-title">{S.healthCardTitle}</h2>
				<div class="health-card-inner">
					<HealthRing
						percent={health.health_percent}
						size={96}
						strokeWidth={10}
						label="{health.health_percent}%"
					/>
					<div class="health-sub-metrics">
						<div class="sub-metric">
							<span class="sub-metric-value">{health.high_confidence}</span>
							<span class="sub-metric-label">High confidence</span>
						</div>
						<div class="sub-metric">
							<span class="sub-metric-value">{health.needs_review}</span>
							<span class="sub-metric-label">Needs review</span>
						</div>
						<div class="sub-metric">
							<span class="sub-metric-value">{health.stale_30d}</span>
							<span class="sub-metric-label">Stale (30d)</span>
						</div>
					</div>
				</div>
			</section>

			<!-- Stat tiles -->
			<div class="stat-grid">
				<a href="/memories" class="stat-link">
					<StatTile
						icon={svgIcon(ICON_MEMORIES)}
						value={String(health.total_memories)}
						label={S.statMemoriesLabel}
					/>
				</a>
				<a href="/links" class="stat-link">
					<StatTile
						icon={svgIcon(ICON_LINKS)}
						value={String(health.total_links)}
						label={S.statLinksLabel}
					/>
				</a>
				<a href="/memories?filter=needs_review" class="stat-link">
					<StatTile
						icon={svgIcon(ICON_REVIEW)}
						value={String(health.needs_review)}
						label={S.statNeedsReviewLabel}
						statusPill={health.needs_review > 0
							? { text: 'Action needed', color: 'var(--color-score-low)' }
							: undefined}
					/>
				</a>
				<a href="/review" class="stat-link">
					<StatTile
						icon={svgIcon(ICON_SESSIONS)}
						value={String(health.pending_suggestions)}
						label={S.statPendingSuggestionsLabel}
						statusPill={health.pending_suggestions > 0
							? { text: 'Pending', color: 'var(--color-score-mid)' }
							: undefined}
					/>
				</a>
			</div>

			<!-- Activity feed -->
			<section class="activity-section" aria-labelledby="activity-heading">
				<h2 id="activity-heading" class="section-title">{S.activityHeading}</h2>
				<ActivityFeed items={health.recent_activity} emptyLabel={S.activityEmptyState} />
			</section>
		</div>
	{/if}
</PageShell>

<style>
	.home-loading,
	.home-error {
		padding: 2rem;
		text-align: center;
		color: var(--color-text-muted, #64748b);
		font-size: 0.875rem;
	}

	.home-error {
		color: var(--color-score-low, #ef4444);
	}

	.home-layout {
		display: grid;
		grid-template-columns: 1fr 1fr;
		grid-template-rows: auto auto;
		gap: 1.5rem;
	}

	.health-card {
		grid-column: 1;
		grid-row: 1;
		border-radius: 1rem;
		border: 1px solid var(--color-stat-border, #e2e8f0);
		background: var(--color-stat-bg, #fff);
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-stat-label, #64748b);
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.health-card-inner {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.health-sub-metrics {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.sub-metric {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
	}

	.sub-metric-value {
		font-size: 1rem;
		font-weight: 700;
		color: var(--color-stat-value, #1e293b);
	}

	.sub-metric-label {
		font-size: 0.75rem;
		color: var(--color-stat-label, #64748b);
	}

	.stat-grid {
		grid-column: 2;
		grid-row: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
	}

	.stat-link {
		text-decoration: none;
		display: block;
		border-radius: 0.75rem;
		transition: opacity 150ms ease;
	}

	.stat-link:hover {
		opacity: 0.85;
	}

	.activity-section {
		grid-column: 1 / -1;
		grid-row: 2;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
</style>
