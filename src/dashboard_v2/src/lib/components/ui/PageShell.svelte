<script lang="ts">
	interface Props {
		title: string;
		subtitle?: string;
		children: import('svelte').Snippet;
	}

	let { title, subtitle, children }: Props = $props();
</script>

<div class="page-header">
	<h1>{title}</h1>
	{#if subtitle}
		<p class="subtitle">{subtitle}</p>
	{/if}
</div>

{@render children()}

<style>
	.page-header {
		margin-bottom: 24px;
	}

	h1 {
		font-size: var(--font-size-heading);
		font-weight: 700;
		color: var(--color-text-primary);
		margin: 0 0 4px;
	}

	.subtitle {
		font-size: var(--font-size-body);
		color: var(--color-text-muted);
		margin: 0;
	}
</style>
