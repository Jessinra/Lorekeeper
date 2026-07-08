<script lang="ts">
	interface Props {
		/** SVG path data (24×24 viewBox) */
		path: string;
		size?: number;
		strokeWidth?: number;
	}

	let { path, size = 16, strokeWidth = 2 }: Props = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	<path d={path} />
</svg>
