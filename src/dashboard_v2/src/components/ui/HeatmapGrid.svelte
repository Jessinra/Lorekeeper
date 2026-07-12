<script lang="ts">
	import { HEATMAP_DEFAULTS, defaultColorScale } from '$lib/constants/primitives';
	import { HEATMAP_GRID_STRINGS } from '$lib/constants/strings';

	interface Cell {
		value: number;
		tooltip: string;
	}

	let {
		data,
		rowLabels,
		colLabels,
		colorScale = defaultColorScale,
		cellSize = HEATMAP_DEFAULTS.cellSize,
		gap = HEATMAP_DEFAULTS.gap,
	}: {
		data: Cell[][];
		rowLabels: string[];
		colLabels: string[];
		colorScale?: (value: number, max: number) => string;
		cellSize?: number;
		gap?: number;
	} = $props();

	const numRows = $derived(data.length);
	const numCols = $derived(data[0]?.length ?? 0);
	const maxValue = $derived(Math.max(...data.flat().map((c) => c.value), 1));
	const gridWidth = $derived(numCols * (cellSize + gap) - gap);
	const gridHeight = $derived(numRows * (cellSize + gap) - gap);
	const labelColor = 'var(--color-heatmap-label)';
	const fontSize = HEATMAP_DEFAULTS.labelFontSize;
	const colLabelHeight = HEATMAP_DEFAULTS.colLabelHeight;
	const rowLabelWidth = HEATMAP_DEFAULTS.rowLabelWidth;
	const svgWidth = $derived(rowLabelWidth + gridWidth + 4);
	const svgHeight = $derived(colLabelHeight + gridHeight + 4);
</script>

<svg width={svgWidth} height={svgHeight} role="img" aria-label={HEATMAP_GRID_STRINGS.ariaLabel}>
	<!-- Column labels -->
	{#each colLabels as label, ci (ci)}
		<text
			x={rowLabelWidth + ci * (cellSize + gap) + cellSize / 2}
			y={colLabelHeight - 4}
			text-anchor="middle"
			font-size={fontSize}
			fill={labelColor}
		>
			{label}
		</text>
	{/each}

	<!-- Row labels + cells -->
	{#each data as row, ri (ri)}
		<text
			x={rowLabelWidth - 6}
			y={colLabelHeight + ri * (cellSize + gap) + cellSize / 2 + 1}
			text-anchor="end"
			dominant-baseline="central"
			font-size={fontSize}
			fill={labelColor}
		>
			{rowLabels[ri] ?? ''}
		</text>

		{#each row as cell, ci (ci)}
			<g>
				<rect
					x={rowLabelWidth + ci * (cellSize + gap)}
					y={colLabelHeight + ri * (cellSize + gap)}
					width={cellSize}
					height={cellSize}
					rx={HEATMAP_DEFAULTS.cellRadius}
					fill={colorScale(cell.value, maxValue)}
				/>
				{#if cell.tooltip}
					<title>{cell.tooltip}</title>
				{/if}
			</g>
		{/each}
	{/each}
</svg>