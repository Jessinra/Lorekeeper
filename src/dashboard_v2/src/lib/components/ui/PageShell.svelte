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

	/*
	 * Shared placeholder block — used by every route stub while full
	 * implementation is pending. Avoids duplicating these styles across
	 * 8 route files.
	 */
	:global(.placeholder) {
		background: var(--color-surface);
		border: var(--border-width) solid var(--color-border);
		border-radius: var(--radius-card);
		padding: var(--space-placeholder-pad);
		color: var(--color-text-muted);
		font-size: var(--font-size-body);
	}
</style>
