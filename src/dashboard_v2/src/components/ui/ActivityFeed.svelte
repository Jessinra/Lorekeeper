<script lang="ts">
	import { ICON_SESSIONS } from '$lib/constants/icons';
	import Icon from '$lib/components/ui/Icon.svelte';
	import type { ActivityItem } from '$lib/api/health';

	let {
		items,
		emptyLabel = 'No recent activity.',
	}: {
		items: ActivityItem[];
		emptyLabel?: string;
	} = $props();

	function formatDate(dateStr: string): string {
		if (!dateStr) return '';
		try {
			return new Date(dateStr).toLocaleDateString(undefined, {
				month: 'short',
				day: 'numeric',
				year: 'numeric',
			});
		} catch {
			return dateStr;
		}
	}
</script>

<ul class="activity-feed" aria-label="Recent activity">
	{#if items.length === 0}
		<li class="activity-empty">{emptyLabel}</li>
	{:else}
		{#each items as item (item.id)}
			<li class="activity-item">
				<span class="activity-icon" aria-hidden="true">
					<Icon path={ICON_SESSIONS} size={16} />
				</span>
				<div class="activity-body">
					<span class="activity-topic">{item.topic}</span>
					<span class="activity-meta">
						{#if item.task_type}<span class="activity-task">{item.task_type}</span>{/if}
						{#if item.session_date}<span class="activity-date">{formatDate(item.session_date)}</span>{/if}
					</span>
				</div>
				<span class="activity-sessions">{item.session_count} {item.session_count === 1 ? 'session' : 'sessions'}</span>
			</li>
		{/each}
	{/if}
</ul>

<style>
	.activity-feed {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.activity-empty {
		font-size: 0.875rem;
		color: var(--color-text-muted, #888);
		padding: 0.5rem 0;
	}

	.activity-item {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		padding: 0.5rem 0.75rem;
		border-radius: 0.5rem;
		border: 1px solid var(--color-stat-border, #e2e8f0);
		background: var(--color-stat-bg, #fff);
	}

	.activity-icon {
		flex-shrink: 0;
		color: var(--color-stat-icon, #64748b);
		display: flex;
		align-items: center;
	}

	.activity-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.activity-topic {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-stat-value, #1e293b);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.activity-meta {
		display: flex;
		gap: 0.5rem;
		font-size: 0.75rem;
		color: var(--color-stat-label, #64748b);
	}

	.activity-task {
		text-transform: capitalize;
	}

	.activity-sessions {
		flex-shrink: 0;
		font-size: 0.75rem;
		color: var(--color-stat-label, #64748b);
	}
</style>
