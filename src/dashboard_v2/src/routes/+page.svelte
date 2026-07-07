<script lang="ts">
	// Home page — stub for LKPR-134
	import PageShell from '$lib/components/ui/PageShell.svelte';
</script>

<PageShell title="Home" subtitle="Knowledge health at a glance.">
	<div class="placeholder">
		<p>Full implementation coming in LKPR-134.</p>
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
