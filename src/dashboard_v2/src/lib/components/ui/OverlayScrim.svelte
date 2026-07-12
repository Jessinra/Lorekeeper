<script lang="ts">
	interface Props {
		onclick: () => void;
	}

	let { onclick }: Props = $props();
</script>

<div class="scrim" {onclick} aria-hidden="true"></div>

<style>
	.scrim {
		position: fixed;
		inset: 0;
		z-index: 800;
		background: var(--color-scrim);
		animation: fade-in 200ms ease forwards;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to   { opacity: 1; }
	}
</style>
