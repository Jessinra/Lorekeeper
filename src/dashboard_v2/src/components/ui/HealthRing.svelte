<script lang="ts">
	import { HEALTH_RING_DEFAULTS } from '$lib/constants/primitives';

	let {
		percent,
		size = HEALTH_RING_DEFAULTS.size,
		strokeWidth = HEALTH_RING_DEFAULTS.strokeWidth,
		color = HEALTH_RING_DEFAULTS.color,
		label,
	}: {
		percent: number;
		size?: number;
		strokeWidth?: number;
		color?: string;
		label?: string;
	} = $props();

	const radius = $derived((size - strokeWidth) / 2);
	const circumference = $derived(2 * Math.PI * radius);
	const clampedPercent = $derived(Math.min(100, Math.max(0, percent)));
	const dashOffset = $derived(circumference - (clampedPercent / 100) * circumference);
	const center = $derived(size / 2);
	const labelFontSize = HEALTH_RING_DEFAULTS.labelFontSize;
	const labelFontWeight = HEALTH_RING_DEFAULTS.labelFontWeight;
</script>

<svg width={size} height={size} viewBox="0 0 {size} {size}" aria-label={label ? `${label}: ${clampedPercent}%` : `${clampedPercent}%`}>
	<circle
		cx={center}
		cy={center}
		r={radius}
		fill="none"
		stroke="var(--color-ring-bg)"
		stroke-width={strokeWidth}
	/>
	<circle
		cx={center}
		cy={center}
		r={radius}
		fill="none"
		stroke={color}
		stroke-width={strokeWidth}
		stroke-linecap="round"
		stroke-dasharray={circumference}
		stroke-dashoffset={dashOffset}
		transform="rotate(-90 {center} {center})"
		style="transition: stroke-dashoffset 300ms ease"
	/>
	{#if label}
		<text
			x={center}
			y={center}
			text-anchor="middle"
			dominant-baseline="central"
			font-size={labelFontSize}
			font-weight={labelFontWeight}
			fill="var(--color-ring-label)"
		>
			{label}
		</text>
	{/if}
</svg>