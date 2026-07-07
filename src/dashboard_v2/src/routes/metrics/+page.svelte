<script lang="ts">
	// Metrics page — stub for LKPR-135
	import PageShell from '$lib/components/ui/PageShell.svelte';
</script>

<PageShell title="Metrics">
	<div class="placeholder">
		<p>Full implementation coming in LKPR-135.</p>
	</div>
</PageShell>

<style>
	.placeholder {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		padding: 40px;
		color: var(--color-text-muted);
		font-size: var(--font-size-body);
	}
</style>
