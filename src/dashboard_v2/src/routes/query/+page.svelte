<script lang="ts">
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import ScorePill from '../../components/ui/ScorePill.svelte';
	import NamespaceDot from '../../components/ui/NamespaceDot.svelte';
	import ToggleSwitch from '../../components/ui/ToggleSwitch.svelte';
	import { runDebugQuery } from '$lib/api/query.js';
	import type { DebugResult, DebugQueryResponse } from '$lib/api/query.js';
	import { ICON_SEARCH } from '$lib/constants/icons.js';

	// ── Signal colors ─────────────────────────────────────────────────────────
	const SIGNAL_COLORS = {
		semantic: '#7c5cff',
		keyword: '#d97706',
		memory: '#16a34a',
		usage: '#6b7280',
	} as const;

	// ── State ─────────────────────────────────────────────────────────────────
	let queryText = $state('');
	let limit = $state(10);
	let minScore = $state(0.1);
	let includeDeleted = $state(false);

	let loading = $state(false);
	let error = $state<string | null>(null);
	let response = $state<DebugQueryResponse | null>(null);
	let selectedResult = $state<DebugResult | null>(null);

	// ── Derived ───────────────────────────────────────────────────────────────
	const hasResults = $derived((response?.results.length ?? 0) > 0);
	const summaryText = $derived(
		response
			? `Returns ${response.total_results} ${response.total_results === 1 ? 'memory' : 'memories'} + ${response.total_linked} linked · ${response.elapsed_ms}ms`
			: '',
	);

	// ── Query execution ───────────────────────────────────────────────────────
	async function runQuery() {
		if (!queryText.trim() || loading) return;
		loading = true;
		error = null;
		selectedResult = null;

		try {
			response = await runDebugQuery({
				query: queryText.trim(),
				limit,
				min_score: minScore,
				include_deleted: includeDeleted,
			});
			// Auto-select first result
			if (response.results.length > 0) {
				selectedResult = response.results[0];
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Query failed';
			response = null;
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			runQuery();
		}
	}

	// ── Stacked bar helpers ───────────────────────────────────────────────────
	function segmentWidth(signalScore: number, combined: number): string {
		if (combined === 0) return '0%';
		return `${(signalScore / combined) * 100}%`;
	}

	function progressWidth(signalScore: number): string {
		// Progress bars in inspector: signal score as fraction of 1.0
		return `${Math.min(signalScore * 100, 100)}%`;
	}
</script>

<PageShell title="Query">
	<!-- Composer bar -->
	<div class="composer-bar">
		<div class="input-row">
			<input
				type="text"
				class="query-input"
				placeholder="Enter a search query to debug relevance…"
				bind:value={queryText}
				onkeydown={handleKeydown}
				autofocus
			/>
			<button
				class="run-btn"
				onclick={runQuery}
				disabled={loading || !queryText.trim()}
				aria-label="Run query"
			>
				{#if loading}
					Running…
				{:else}
					Run
				{/if}
			</button>
		</div>

		<div class="controls-row">
			<label class="control-item">
				<span class="control-label">Limit:</span>
				<select class="control-select" bind:value={limit}>
					<option value={5}>5</option>
					<option value={10}>10</option>
					<option value={20}>20</option>
					<option value={50}>50</option>
				</select>
			</label>

			<label class="control-item">
				<span class="control-label">Min score:</span>
				<input
					type="number"
					class="control-number"
					bind:value={minScore}
					min={0}
					max={1}
					step={0.05}
				/>
			</label>

			<ToggleSwitch
				checked={includeDeleted}
				label="Include deleted"
				onChange={(val) => (includeDeleted = val)}
			/>

			{#if summaryText}
				<span class="result-summary">{summaryText}</span>
			{/if}
		</div>

		{#if error}
			<p class="error-text">{error}</p>
		{/if}
	</div>

	<!-- Split panel -->
	<div class="split-panel">
		<!-- Left 42% — ranked result list -->
		<div class="left-panel">
			{#if response === null && !loading}
				<div class="pre-query-hint">
					<Icon path={ICON_SEARCH} size={32} />
					<p>Run a query to see results</p>
				</div>
			{:else if loading}
				<div class="pre-query-hint"><p>Running…</p></div>
			{:else if !hasResults}
				<EmptyState
					icon={ICON_SEARCH}
					message="No results"
					description="Try lowering the min score or searching for a different term."
				/>
			{:else}
				<ul class="result-list" role="listbox" aria-label="Query results">
					{#each response!.results as result (result.memory.id)}
						<li
							class="result-row"
							class:selected={selectedResult?.memory.id === result.memory.id}
							role="option"
							aria-selected={selectedResult?.memory.id === result.memory.id}
							onclick={() => (selectedResult = result)}
							onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectedResult = result; }}}
							tabindex="0"
						>
							<div class="result-header">
								<span class="rank">#{result.rank}</span>
								<span class="result-title">{result.memory.title}</span>
								<ScorePill score={result.combined_score * 10} />
							</div>

							<!-- Stacked bar -->
							<div class="stacked-bar" aria-hidden="true" title="Signal breakdown">
								{#if result.combined_score > 0}
									<div class="bar-segment" style="width: {segmentWidth(result.semantic_score, result.combined_score)}; background-color: {SIGNAL_COLORS.semantic};"></div>
									<div class="bar-segment" style="width: {segmentWidth(result.keyword_score, result.combined_score)}; background-color: {SIGNAL_COLORS.keyword};"></div>
									<div class="bar-segment" style="width: {segmentWidth(result.memory_score, result.combined_score)}; background-color: {SIGNAL_COLORS.memory};"></div>
									<div class="bar-segment" style="width: {segmentWidth(result.usage_score, result.combined_score)}; background-color: {SIGNAL_COLORS.usage};"></div>
								{/if}
							</div>

							<div class="result-meta">
								<span class="uses-count">{result.memory.usage_count} uses</span>
								<span class="link-count">+{result.memory.link_count} linked</span>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<!-- Right 58% — inspector -->
		<div class="right-panel">
			{#if selectedResult === null}
				<div class="inspector-empty">
					{#if !hasResults && response !== null}
						<p>No results — try lowering the min score or searching for a different term.</p>
					{:else}
						<p>Run a query to see results</p>
					{/if}
				</div>
			{:else}
				<div class="inspector">
					<!-- Header -->
					<div class="inspector-header">
						<h2 class="inspector-title">{selectedResult.memory.title}</h2>
						<div class="inspector-meta">
							<NamespaceDot namespace={selectedResult.memory.namespace} />
							<span class="ns-label">{selectedResult.memory.namespace}</span>
							<span class="sep">·</span>
							<span class="uses-label">{selectedResult.memory.usage_count} uses</span>
						</div>
					</div>

					<!-- Big score badge -->
					<div class="score-badge">
						<ScorePill score={selectedResult.combined_score * 10} />
					</div>

					<!-- Content snippet -->
					<p class="inspector-snippet">
						{selectedResult.memory.content.slice(0, 200)}{selectedResult.memory.content.length > 200 ? '…' : ''}
					</p>

					<!-- Why it ranked here -->
					<div class="breakdown">
						<h3 class="breakdown-title">Why it ranked here:</h3>

						{#each [
							{ label: 'Semantic', value: selectedResult.semantic_score, color: SIGNAL_COLORS.semantic },
							{ label: 'Keyword', value: selectedResult.keyword_score, color: SIGNAL_COLORS.keyword },
							{ label: 'Mem Score', value: selectedResult.memory_score, color: SIGNAL_COLORS.memory },
							{ label: 'Usage', value: selectedResult.usage_score, color: SIGNAL_COLORS.usage },
						] as signal (signal.label)}
							<div class="signal-row">
								<span class="signal-label">{signal.label}</span>
								<div class="progress-track">
									<div
										class="progress-fill"
										style="width: {progressWidth(signal.value)}; background-color: {signal.color};"
									></div>
								</div>
								<span class="signal-value">{signal.value.toFixed(4)}</span>
							</div>
						{/each}

						<div class="combined-row">
							<span class="combined-label">Combined:</span>
							<span class="combined-value">{selectedResult.combined_score.toFixed(4)}</span>
							<div class="combined-bar-track">
								<div
									class="combined-bar-fill"
									style="width: {progressWidth(selectedResult.combined_score)};"
								></div>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</PageShell>

<style>
	/* ── Composer bar ───────────────────────────────────────────────────────── */
	.composer-bar {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		background: var(--color-surface);
		margin-bottom: 1rem;
	}

	.input-row {
		display: flex;
		gap: 0.5rem;
	}

	.query-input {
		flex: 1;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-bg);
		color: var(--color-text);
		font-size: 0.875rem;
	}

	.query-input:focus {
		outline: 2px solid var(--color-accent);
		outline-offset: 1px;
	}

	.run-btn {
		padding: 0.5rem 1rem;
		border-radius: var(--radius-sm);
		background: var(--color-accent);
		color: #fff;
		font-size: 0.875rem;
		font-weight: 500;
		border: none;
		cursor: pointer;
		white-space: nowrap;
	}

	.run-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.controls-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.control-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.8125rem;
		color: var(--color-text-muted);
	}

	.control-label {
		white-space: nowrap;
	}

	.control-select,
	.control-number {
		padding: 0.25rem 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-bg);
		color: var(--color-text);
		font-size: 0.8125rem;
	}

	.control-number {
		width: 5rem;
	}

	.result-summary {
		font-size: 0.8125rem;
		color: var(--color-text-muted);
		margin-left: auto;
	}

	.error-text {
		font-size: 0.8125rem;
		color: var(--color-danger, #ef4444);
	}

	/* ── Split panel ────────────────────────────────────────────────────────── */
	.split-panel {
		display: grid;
		grid-template-columns: 42fr 58fr;
		gap: 0;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		overflow: hidden;
		min-height: 480px;
		flex: 1;
	}

	/* ── Left panel ─────────────────────────────────────────────────────────── */
	.left-panel {
		border-right: 1px solid var(--color-border);
		overflow-y: auto;
		background: var(--color-surface);
	}

	.pre-query-hint {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 0.5rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
		text-align: center;
		padding: 2rem;
	}

	.result-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.result-row {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--color-border);
		cursor: pointer;
		transition: background 100ms ease;
	}

	.result-row:hover,
	.result-row:focus {
		background: var(--color-hover, rgba(0,0,0,0.04));
		outline: none;
	}

	.result-row.selected {
		background: var(--color-selected, rgba(124,92,255,0.08));
	}

	.result-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.375rem;
	}

	.rank {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--color-text-muted);
		min-width: 1.75rem;
	}

	.result-title {
		flex: 1;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Stacked bar */
	.stacked-bar {
		display: flex;
		height: 6px;
		border-radius: 3px;
		overflow: hidden;
		background: var(--color-border);
		margin-bottom: 0.375rem;
	}

	.bar-segment {
		height: 100%;
		flex-shrink: 0;
	}

	.result-meta {
		display: flex;
		gap: 0.75rem;
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}

	/* ── Right panel ────────────────────────────────────────────────────────── */
	.right-panel {
		overflow-y: auto;
		background: var(--color-bg);
	}

	.inspector-empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: 2rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
		text-align: center;
	}

	.inspector {
		padding: 1.25rem 1.5rem;
	}

	.inspector-header {
		margin-bottom: 0.75rem;
	}

	.inspector-title {
		font-size: 1.0625rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0 0 0.375rem;
		line-height: 1.3;
	}

	.inspector-meta {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.8125rem;
		color: var(--color-text-muted);
	}

	.sep { color: var(--color-border); }

	.score-badge {
		display: flex;
		justify-content: center;
		margin: 0.75rem 0;
	}

	.inspector-snippet {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		line-height: 1.5;
		margin: 0 0 1.25rem;
		word-break: break-word;
	}

	/* ── Breakdown ──────────────────────────────────────────────────────────── */
	.breakdown {
		border-top: 1px solid var(--color-border);
		padding-top: 0.875rem;
	}

	.breakdown-title {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--color-text-muted);
		margin: 0 0 0.625rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.signal-row {
		display: grid;
		grid-template-columns: 6rem 1fr 4rem;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.signal-label {
		font-size: 0.8125rem;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	.progress-track {
		height: 8px;
		background: var(--color-border);
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 200ms ease;
	}

	.signal-value {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.combined-row {
		display: grid;
		grid-template-columns: 6rem 4rem 1fr;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border);
	}

	.combined-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--color-text);
		white-space: nowrap;
	}

	.combined-value {
		font-size: 0.8125rem;
		font-weight: 600;
		color: var(--color-text);
		font-variant-numeric: tabular-nums;
	}

	.combined-bar-track {
		height: 10px;
		background: var(--color-border);
		border-radius: 5px;
		overflow: hidden;
	}

	.combined-bar-fill {
		height: 100%;
		background: var(--color-accent);
		border-radius: 5px;
		transition: width 200ms ease;
	}
</style>
