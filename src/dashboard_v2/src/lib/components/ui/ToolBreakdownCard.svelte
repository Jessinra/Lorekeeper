<script lang="ts">
	import { defaultColorScale } from '$lib/constants/primitives';
	import type { HeatmapCell } from '$lib/api/metrics';

	interface Props {
		toolName: string;
		totalCalls: number;
		days: string[];
		heatmap: Record<string, Record<string, HeatmapCell>>;
		color: string; // CSS color value for accent border + dot
	}

	let { toolName, totalCalls, days, heatmap, color }: Props = $props();

	const HOURS = Array.from({ length: 24 }, (_, i) => i);

	// Compute per-tool max for color scaling
	let maxCell = $derived.by(() => {
		let m = 0;
		for (const day of days) {
			for (let h = 0; h < 24; h++) {
				const cell = heatmap[day]?.[String(h)];
				const v = cell ? (cell[toolName] ?? 0) : 0;
				if (v > m) m = v;
			}
		}
		return m || 1;
	});

	function cellValue(day: string, hour: number): number {
		return heatmap[day]?.[String(hour)]?.[toolName] ?? 0;
	}

	function dayLabel(day: string): string {
		// "2026-07-14" → "Mon"
		return new Date(day + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'short' });
	}
</script>

<div class="tool-card" style:--accent={color}>
	<!-- Card header -->
	<div class="card-header">
		<span class="tool-dot" aria-hidden="true"></span>
		<span class="tool-name">{toolName}</span>
		<span class="calls-badge">{totalCalls.toLocaleString()}</span>
	</div>

	<!-- Mini heatmap (non-interactive) -->
	<div class="mini-heatmap" aria-label="{toolName} activity heatmap" role="img">
		{#each days as day (day)}
			<div class="hm-row">
				<span class="day-label">{dayLabel(day)}</span>
				<div class="hm-cells">
					{#each HOURS as h (h)}
						{@const v = cellValue(day, h)}
						<div
							class="hm-cell"
							style:background={defaultColorScale(v, maxCell)}
							title="{day} {h}:00 — {v} calls"
						></div>
					{/each}
				</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.tool-card {
		background: var(--color-card-bg, var(--color-surface));
		border: var(--border-width) solid var(--color-card-border, var(--color-border));
		border-top: 3px solid var(--accent);
		border-radius: var(--radius-card);
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		overflow: hidden;
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.tool-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--accent);
		flex-shrink: 0;
	}

	.tool-name {
		font-size: var(--font-size-sm);
		font-weight: var(--font-weight-medium);
		color: var(--color-text);
		font-family: var(--font-mono, monospace);
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.calls-badge {
		font-size: var(--font-size-badge);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-muted);
		background: var(--color-chip-bg);
		padding: 2px var(--space-2);
		border-radius: var(--radius-pill);
		flex-shrink: 0;
	}

	.mini-heatmap {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.hm-row {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.day-label {
		font-size: 9px;
		color: var(--color-text-muted);
		width: 24px;
		text-align: right;
		flex-shrink: 0;
		line-height: 1;
	}

	.hm-cells {
		display: flex;
		gap: 2px;
		flex: 1;
	}

	.hm-cell {
		flex: 1;
		height: 10px;
		border-radius: 1px;
		min-width: 0;
	}
</style>
