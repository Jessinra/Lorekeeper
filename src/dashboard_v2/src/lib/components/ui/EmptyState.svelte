<script lang="ts">
	import Icon from '$lib/components/ui/Icon.svelte';

	interface Props {
		icon: string;
		message: string;
		description?: string;
	}

	let { icon, message, description }: Props = $props();
</script>

<div class="empty-state" role="status">
	<span class="icon-wrapper">
		<Icon path={icon} size={48} strokeWidth={1.5} />
	</span>
	<p class="message">{message}</p>
	{#if description}
		<p class="description">{description}</p>
	{/if}
</div>

<style>
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 48px 24px;
		text-align: center;
	}

	.icon-wrapper {
		color: var(--color-text-faint);
		margin-bottom: 12px;
		display: flex;
	}

	.message {
		font-size: var(--font-size-body);
		font-weight: 600;
		color: var(--color-text-muted);
		margin: 0 0 4px;
	}

	.description {
		font-size: var(--font-size-body);
		color: var(--color-text-faint);
		margin: 0;
		max-width: 320px;
		line-height: 1.5;
	}
</style>