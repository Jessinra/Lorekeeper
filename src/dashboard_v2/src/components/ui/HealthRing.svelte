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
	const dashOffset = $derived(circumference - (percent / 100) * circumference);
	const center = $derived(size / 2);
	const labelFontSize = HEALTH_RING_DEFAULTS.labelFontSize;
</script>

<svg width={size} height={size} viewBox="0 0 {size} {size}" aria-label={label ? `${label}: ${percent}%` : `${percent}%`}>
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
			font-weight="700"
			fill="var(--color-ring-label)"
		>
			{label}
		</text>
	{/if}
</svg>