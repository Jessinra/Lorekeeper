<script lang="ts">
	import { RELATION_DRAWER_STRINGS as S } from '$lib/constants/strings';
	import { NAMESPACE_COLORS } from '$lib/constants/primitives';
	import type { MemoryData } from './types';
	import ScorePill from '../../../components/ui/ScorePill.svelte';
	import NamespaceDot from '../../../components/ui/NamespaceDot.svelte';

	interface Props {
		memory: MemoryData;
		conflictTint: boolean;
		onClick: () => void;
	}

	let { memory, conflictTint, onClick }: Props = $props();

	function ns(namespace: string): keyof typeof NAMESPACE_COLORS {
		return namespace as keyof typeof NAMESPACE_COLORS;
	}
</script>

<button
	type="button"
	class="memory-card"
	class:deleted={memory.soft_deleted}
	class:conflict-tint={conflictTint}
	onclick={onClick}
>
	<div class="card-badge" class:visible={memory.soft_deleted}>
		<span class="deleted-badge">{S.deletedBadge}</span>
	</div>
	<h3 class="card-title" class:strikethrough={memory.soft_deleted}>
		{memory.title}
	</h3>
	<div class="card-meta">
		<NamespaceDot namespace={ns(memory.namespace)} />
		<ScorePill score={memory.score} />
	</div>
	<div class="card-content">
		{memory.content || S.noContent}
	</div>
	<p class="card-desc">
		{memory.description || S.noDescription}
	</p>
	{#if memory.content.length > 180}
		<span class="show-full">{S.showFull} →</span>
	{/if}
</button>

<style>
	.memory-card {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-4);
		border: var(--border-width) solid var(--color-drawer-border);
		border-radius: var(--radius-md);
		background-color: var(--color-surface);
		text-align: left;
		font-family: inherit;
		font-size: inherit;
		color: inherit;
		cursor: pointer;
		position: relative;
		overflow: hidden;
		transition: border-color 120ms ease, box-shadow 120ms ease;
		min-width: 0;
	}

	.memory-card:hover {
		border-color: var(--color-brand);
		box-shadow: 0 2px 8px rgba(124, 92, 255, 0.12);
	}

	.memory-card.deleted {
		border-color: var(--color-drawer-danger-border);
		opacity: 0.85;
	}

	.memory-card.conflict-tint {
		border-color: var(--color-drawer-danger-border);
		background-color: var(--color-drawer-danger-bg);
	}

	.card-badge {
		display: none;
	}

	.card-badge.visible {
		display: flex;
		justify-content: flex-end;
		margin-bottom: -4px;
	}

	.deleted-badge {
		display: inline-flex;
		align-items: center;
		padding: 1px 6px;
		border-radius: var(--radius-pill);
		background-color: var(--color-drawer-danger-bg);
		color: var(--color-drawer-danger-text);
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-medium);
		white-space: nowrap;
	}

	.card-title {
		margin: 0;
		font-size: var(--font-size-ui);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.card-title.strikethrough {
		text-decoration: line-through;
	}

	.card-meta {
		display: flex;
		align-items: center;
		gap: var(--space-1-5);
		font-size: var(--font-size-micro);
	}

	.card-content {
		font-family: ui-monospace, SFMono-Regular, monospace;
		font-size: var(--font-size-sub);
		line-height: var(--line-height-normal);
		color: var(--color-text-body);
		background-color: var(--color-drawer-code-bg);
		border: var(--border-width) solid var(--color-drawer-code-border);
		border-radius: var(--radius-kbd);
		padding: var(--space-2);
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		max-height: 4.5em;
	}

	.card-desc {
		margin: 0;
		font-size: var(--font-size-sub);
		font-style: italic;
		color: var(--color-text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.show-full {
		font-size: var(--font-size-micro);
		color: var(--color-brand);
		font-weight: var(--font-weight-medium);
		cursor: pointer;
	}

	.show-full:hover {
		text-decoration: underline;
	}
</style>