<script lang="ts">
	import { SESSIONS_STRINGS as S } from '$lib/constants/strings';
	import ScorePill from '../../../components/ui/ScorePill.svelte';
	import type { SessionMemory } from '$lib/api/sessions.js';

	interface Props {
		memories: SessionMemory[];
		onOpen: (mem: SessionMemory) => void;
	}

	let { memories, onOpen }: Props = $props();
</script>

<section class="section">
	<h3 class="section-heading">{S.memoriesHeading} ({memories.length})</h3>
	{#if memories.length === 0}
		<p class="empty-memories">{S.noMemories}</p>
	{:else}
		<ul class="memory-list" role="list">
			{#each memories as mem (mem.lore_id)}
				<li>
					<button class="memory-card" onclick={() => onOpen(mem)}>
						<div class="memory-card-top">
							<span class="memory-title">{mem.title}</span>
							<ScorePill score={mem.score} />
						</div>
						{#if mem.description}
							<p class="memory-desc">{mem.description}</p>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.section {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.section-heading {
		font-size: var(--font-size-label);
		font-weight: var(--font-weight-semibold);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--color-text-muted);
		margin: 0;
	}

	.memory-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.memory-card {
		width: 100%;
		text-align: left;
		background: var(--color-card-bg, var(--color-chip-bg));
		border: var(--border-width) solid var(--color-card-border, var(--color-chip-border));
		border-radius: var(--radius-md);
		padding: var(--space-3);
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
		transition: background-color 150ms;
	}

	.memory-card:hover {
		background-color: var(--color-chip-hover-bg);
	}

	.memory-card-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-2);
	}

	.memory-title {
		font-size: var(--font-size-xs);
		font-weight: var(--font-weight-medium);
		color: var(--color-text);
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.memory-desc {
		font-size: var(--font-size-micro);
		color: var(--color-text-muted);
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.empty-memories {
		font-size: var(--font-size-xs);
		color: var(--color-text-muted);
		margin: 0;
	}
</style>
