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
		padding: var(--empty-state-padding);
		text-align: center;
	}

	.icon-wrapper {
		color: var(--color-text-faint);
		margin-bottom: var(--empty-state-icon-margin-bottom);
		display: flex;
	}

	.message {
		font-size: var(--font-size-body);
		font-weight: var(--empty-state-message-font-weight);
		color: var(--color-text-muted);
		margin: var(--empty-state-message-margin);
	}

	.description {
		font-size: var(--font-size-body);
		color: var(--color-text-faint);
		margin: 0;
		max-width: var(--empty-state-description-max-width);
		line-height: var(--empty-state-description-line-height);
	}
</style>