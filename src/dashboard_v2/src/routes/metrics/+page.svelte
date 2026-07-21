<script lang="ts">
	import { onMount } from 'svelte';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import ToolBreakdownCard from '$lib/components/ui/ToolBreakdownCard.svelte';
	import { METRICS_STRINGS as S } from '$lib/constants/strings';
	import { ICON_REFRESH } from '$lib/constants/icons';
	import { defaultColorScale } from '$lib/constants/primitives';
	import { fetchToolCalls } from '$lib/api/metrics';
	import type { ToolCallsResponse, HeatmapCell } from '$lib/api/metrics';

	// ── Data state ─────────────────────────────────────────────────────────────

	let data = $state<ToolCallsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Load ───────────────────────────────────────────────────────────────────

	async function load() {
		loading = true;
		error = null;
		try {
			data = await fetchToolCalls(168);
		} catch (e) {
			error = (e as Error).message;
		} finally {
			loading = false;
		}
	}

	onMount(() => void load());

	// ── Heatmap helpers ────────────────────────────────────────────────────────

	const HOURS = Array.from({ length: 24 }, (_, i) => i);

	let maxCellTotal = $derived.by(() => {
		if (!data) return 1;
		let m = 0;
		for (const day of data.days) {
			for (let h = 0; h < 24; h++) {
				const v = data.heatmap[day]?.[String(h)]?.total ?? 0;
				if (v > m) m = v;
			}
		}
		return m || 1;
	});

	function cellTotal(day: string, hour: number): number {
		return data?.heatmap[day]?.[String(hour)]?.total ?? 0;
	}

	function cellData(day: string, hour: number): HeatmapCell | null {
		return data?.heatmap[day]?.[String(hour)] ?? null;
	}

	function dayLabel(day: string): string {
		return new Date(day + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' });
	}

	// ── Tooltip state ──────────────────────────────────────────────────────────

	interface TooltipInfo {
		day: string;
		hour: number;
		cell: HeatmapCell;
		x: number;
		y: number;
	}

	let tooltip = $state<TooltipInfo | null>(null);

	function showTooltip(e: MouseEvent, day: string, hour: number) {
		const cell = cellData(day, hour);
		if (!cell || cell.total === 0) {
			tooltip = null;
			return;
		}
		tooltip = { day, hour, cell, x: e.clientX, y: e.clientY };
	}

	function hideTooltip() {
		tooltip = null;
	}

	// ── Tool colors ────────────────────────────────────────────────────────────

	const TOOL_COLORS: Record<string, string> = {
		lore_insert: 'var(--color-task-build-text, #16a34a)',
		lore_processed_sessions: 'var(--color-task-review-text, #7c3aed)',
		lore_recommend_links: '#0d9488',
		lore_reflect: 'var(--color-task-debug-text, #dc2626)',
		lore_search: 'var(--color-brand, #6366f1)',
	};

	function toolColor(name: string): string {
		return TOOL_COLORS[name] ?? 'var(--color-text-muted)';
	}
</script>

<PageShell title={S.pageTitle}>
	<!-- Header bar -->
	<div class="page-header">
		<div class="header-text">
			<h1 class="page-title">{S.pageTitle}</h1>
			<p class="page-subtitle">{S.pageSubtitle}</p>
		</div>
		<button
			class="refresh-btn"
			onclick={() => void load()}
			disabled={loading}
			aria-label={S.refreshAriaLabel}
		>
			<Icon path={ICON_REFRESH} size={14} />
			Refresh
		</button>
	</div>

	{#if loading}
		<div class="loading-state" aria-live="polite">Loading…</div>
	{:else if error}
		<div class="error-banner" role="alert">{error}</div>
	{:else if !data || data.total_calls === 0}
		<div class="empty-state" aria-live="polite">{S.emptyState}</div>
	{:else}
		<!-- Top section: stat card + main heatmap -->
		<div class="top-section">
			<!-- Total volume card -->
			<div class="stat-card">
				<span class="stat-card-title">{S.totalVolumeTitle}</span>
				<span class="stat-value">{data.total_calls.toLocaleString()}</span>
				<span class="stat-label">{S.totalCallsLabel}</span>
				<div class="stat-divider"></div>
				<span class="stat-value stat-value--secondary">{data.avg_calls_per_day}</span>
				<span class="stat-label">{S.avgCallsLabel}</span>
			</div>

			<!-- Main heatmap -->
			<div class="heatmap-card">
				<div class="heatmap-header">
					<span class="heatmap-title">{S.heatmapTitle}</span>
					<span class="heatmap-tz">{data.timezone}</span>
				</div>

				<div class="heatmap-grid">
					<!-- Hour axis labels (0, 6, 12, 18, 23) -->
					<div class="hm-axis-row">
						<span class="hm-row-label"></span>
						<div class="hm-hour-labels">
							{#each HOURS as h (h)}
								<span class="hour-tick" class:hour-tick--visible={h % 6 === 0}>
									{h % 6 === 0 ? h : ''}
								</span>
							{/each}
						</div>
					</div>

					<!-- Data rows: one per day -->
					{#each data.days as day (day)}
						<div class="hm-row">
							<span class="hm-row-label">{dayLabel(day)}</span>
							<div class="hm-cells">
								{#each HOURS as h (h)}
									{@const v = cellTotal(day, h)}
									<!-- svelte-ignore a11y_mouse_events_have_key_events -->
									<div
										class="hm-cell"
										style:background={defaultColorScale(v, maxCellTotal)}
										aria-label="{day} {h}:00 — {v} calls"
										onmouseover={(e) => showTooltip(e, day, h)}
										onmouseleave={hideTooltip}
									></div>
								{/each}
							</div>
						</div>
					{/each}
				</div>

				<!-- Legend -->
				<div class="heatmap-legend" aria-hidden="true">
					<span class="legend-label">{S.heatmapFewerLabel}</span>
					<div class="legend-cells">
						{#each [0, 0.1, 0.4, 0.7, 1] as frac (frac)}
							<div
								class="legend-cell"
								style:background={defaultColorScale(
									Math.round(frac * maxCellTotal),
									maxCellTotal
								)}
							></div>
						{/each}
					</div>
					<span class="legend-label">{S.heatmapMoreLabel}</span>
				</div>
			</div>
		</div>

		<!-- Per-tool breakdown -->
		<div class="breakdown-section">
			<h2 class="section-heading">{S.perToolTitle}</h2>
			<div class="breakdown-grid">
				{#each data.tools as tool (tool)}
					<ToolBreakdownCard
						toolName={tool}
						totalCalls={data.tool_totals[tool] ?? 0}
						days={data.days}
						heatmap={data.heatmap}
						color={toolColor(tool)}
					/>
				{/each}
			</div>
		</div>
	{/if}
</PageShell>

<!-- Hover tooltip (fixed position) -->
{#if tooltip}
	<div
		class="tooltip"
		role="tooltip"
		style:left="{tooltip.x + 12}px"
		style:top="{tooltip.y - 8}px"
	>
		<div class="tooltip-header">{tooltip.day} · {tooltip.hour}:00</div>
		{#each Object.entries(tooltip.cell).filter(([k]) => k !== 'total') as [tool, count] (tool)}
			<div class="tooltip-row">
				<span class="tooltip-dot" style:background={toolColor(tool)}></span>
				<span class="tooltip-tool">{tool}</span>
				<span class="tooltip-count">{count}</span>
			</div>
		{/each}
		<div class="tooltip-total">
			<span>{S.tooltipTotal}</span>
			<span>{tooltip.cell.total}</span>
		</div>
	</div>
{/if}

<style>
	/* ── Page header ──────────────────────────────────────────────────────────── */

	.page-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		padding: var(--space-6) var(--space-6) var(--space-4);
		gap: var(--space-4);
	}

	.header-text {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.page-title {
		font-size: var(--font-size-heading);
		font-weight: var(--font-weight-bold);
		color: var(--color-text);
		margin: 0;
	}

	.page-subtitle {
		font-size: var(--font-size-body);
		color: var(--color-text-muted);
		margin: 0;
	}

	.refresh-btn {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2) var(--space-3);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-input);
		background: var(--color-surface);
		color: var(--color-text-muted);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: border-color 150ms, color 150ms;
		flex-shrink: 0;
	}

	.refresh-btn:hover:not(:disabled) {
		border-color: var(--color-brand);
		color: var(--color-brand);
	}

	.refresh-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* ── Loading / error / empty ──────────────────────────────────────────────── */

	.loading-state,
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 80px var(--space-6);
		color: var(--color-text-muted);
		font-size: var(--font-size-body);
	}

	.error-banner {
		margin: var(--space-3) var(--space-6);
		padding: var(--space-3) var(--space-4);
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border-radius: var(--radius-card);
		font-size: var(--font-size-body);
	}

	/* ── Top section: stat + heatmap ──────────────────────────────────────────── */

	.top-section {
		display: grid;
		grid-template-columns: 200px 1fr;
		gap: var(--space-4);
		padding: 0 var(--space-6) var(--space-4);
		align-items: start;
	}

	/* ── Stat card ────────────────────────────────────────────────────────────── */

	.stat-card {
		background: var(--color-card-bg, var(--color-surface));
		border: var(--border-width) solid var(--color-card-border, var(--color-border));
		border-radius: var(--radius-card);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.stat-card-title {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-bold);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-muted);
		margin-bottom: var(--space-2);
	}

	.stat-value {
		font-size: 28px;
		font-weight: var(--font-weight-bold);
		color: var(--color-text);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	.stat-value--secondary {
		font-size: 22px;
		color: var(--color-text-muted);
	}

	.stat-label {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
	}

	.stat-divider {
		height: 1px;
		background: var(--color-border);
		margin: var(--space-2) 0;
	}

	/* ── Main heatmap ─────────────────────────────────────────────────────────── */

	.heatmap-card {
		background: var(--color-card-bg, var(--color-surface));
		border: var(--border-width) solid var(--color-card-border, var(--color-border));
		border-radius: var(--radius-card);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		overflow: hidden;
	}

	.heatmap-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.heatmap-title {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-bold);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-muted);
	}

	.heatmap-tz {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		background: var(--color-chip-bg);
		padding: 2px var(--space-2);
		border-radius: var(--radius-pill);
	}

	.heatmap-grid {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.hm-axis-row {
		display: flex;
		align-items: center;
	}

	.hm-row {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.hm-row-label {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		width: 32px;
		text-align: right;
		flex-shrink: 0;
		line-height: 1;
	}

	.hm-hour-labels {
		display: flex;
		flex: 1;
		gap: 3px;
	}

	.hour-tick {
		flex: 1;
		font-size: 9px;
		color: var(--color-text-muted);
		text-align: center;
		line-height: 1;
		min-width: 0;
	}

	.hm-cells {
		display: flex;
		flex: 1;
		gap: 3px;
	}

	.hm-cell {
		flex: 1;
		height: 14px;
		border-radius: 2px;
		cursor: default;
		min-width: 0;
		transition: opacity 100ms;
	}

	.hm-cell:hover {
		opacity: 0.8;
	}

	/* ── Legend ───────────────────────────────────────────────────────────────── */

	.heatmap-legend {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		justify-content: flex-end;
	}

	.legend-label {
		font-size: 9px;
		color: var(--color-text-muted);
	}

	.legend-cells {
		display: flex;
		gap: 2px;
	}

	.legend-cell {
		width: 12px;
		height: 12px;
		border-radius: 2px;
	}

	/* ── Per-tool breakdown ───────────────────────────────────────────────────── */

	.breakdown-section {
		padding: var(--space-2) var(--space-6) var(--space-6);
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.section-heading {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-bold);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--color-text-muted);
		margin: 0;
	}

	.breakdown-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-4);
	}

	@media (max-width: 900px) {
		.breakdown-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.top-section {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 600px) {
		.breakdown-grid {
			grid-template-columns: 1fr;
		}
	}

	/* ── Tooltip ──────────────────────────────────────────────────────────────── */

	.tooltip {
		position: fixed;
		z-index: 1000;
		background: var(--color-surface-elevated, var(--color-surface));
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-card);
		padding: var(--space-3);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
		min-width: 180px;
		pointer-events: none;
		display: flex;
		flex-direction: column;
		gap: var(--space-1-5);
	}

	.tooltip-header {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text);
		padding-bottom: var(--space-1);
		border-bottom: 1px solid var(--color-border);
		margin-bottom: var(--space-1);
	}

	.tooltip-row {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
	}

	.tooltip-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.tooltip-tool {
		flex: 1;
		font-family: var(--font-mono, monospace);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tooltip-count {
		font-variant-numeric: tabular-nums;
		font-weight: var(--font-weight-semibold);
		color: var(--color-text);
	}

	.tooltip-total {
		display: flex;
		justify-content: space-between;
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text);
		padding-top: var(--space-1);
		border-top: 1px solid var(--color-border);
		margin-top: var(--space-1);
	}
</style>
