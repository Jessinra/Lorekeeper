<script lang="ts">
	import { onMount } from 'svelte';
	import PageShell from '$lib/components/ui/PageShell.svelte';
	import Icon from '$lib/components/ui/Icon.svelte';
	import { SETTINGS_STRINGS as S } from '$lib/constants/strings';
	import { ICON_REFRESH, ICON_DOWNLOAD, ICON_UPLOAD } from '$lib/constants/icons';
	import { fetchConfig, patchConfig, type ConfigData, type ConfigUpdates } from '$lib/api/config';
	import { fetchSweepStatus, triggerSweep, type SweepStatus } from '$lib/api/sweep';
	import { showToast } from '$lib/toast';

	// ── Data state ──────────────────────────────────────────────────────────────

	let config = $state<ConfigData | null>(null);
	let sweep = $state<SweepStatus | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// ── Draft state (editable copies per section) ───────────────────────────────

	// §1 Search weights
	let draftWeights = $state({ w_semantic: 0, w_keyword: 0, w_memory: 0, w_usage: 0 });
	// §2 Scoring
	let draftScoring = $state({
		score_bump_up: 0,
		score_bump_down: 0,
		score_min: 0,
		score_max: 0,
		new_memory_default_score: 0,
		duplicate_threshold: 0,
	});
	// §3 Search & links
	let draftSearchLinks = $state({
		search_limit: 0,
		max_links_per_memory: 0,
		usage_normalisation_cap: 0,
		decay_lambda: 0,
		auto_link_enabled: false,
		auto_link_k: 0,
		auto_link_threshold: 0,
	});
	// §4 Memory lifecycle
	let draftLifecycle = $state({
		soft_delete_confidence_threshold: 0,
		confidence_window_size: 0,
	});

	// ── Saving state ────────────────────────────────────────────────────────────

	let savingWeights = $state(false);
	let savingScoring = $state(false);
	let savingSearchLinks = $state(false);
	let savingLifecycle = $state(false);

	// ── Import state ────────────────────────────────────────────────────────────

	interface ImportPreview {
		added: number;
		skipped: number;
		links: number;
		file: File;
	}
	let importPreview = $state<ImportPreview | null>(null);
	let importLoading = $state(false);
	let importConfirming = $state(false);
	let sweepTriggering = $state(false);

	// ── Load ────────────────────────────────────────────────────────────────────

	async function load() {
		loading = true;
		error = null;
		try {
			const [cfg, sw] = await Promise.all([fetchConfig(), fetchSweepStatus()]);
			config = cfg;
			sweep = sw;
			syncDrafts(cfg);
		} catch {
			error = S.loadError;
		} finally {
			loading = false;
		}
	}

	function syncDrafts(cfg: ConfigData) {
		draftWeights = {
			w_semantic: cfg.w_semantic,
			w_keyword: cfg.w_keyword,
			w_memory: cfg.w_memory,
			w_usage: cfg.w_usage,
		};
		draftScoring = {
			score_bump_up: cfg.score_bump_up,
			score_bump_down: cfg.score_bump_down,
			score_min: cfg.score_min,
			score_max: cfg.score_max,
			new_memory_default_score: cfg.new_memory_default_score,
			duplicate_threshold: cfg.duplicate_threshold,
		};
		draftSearchLinks = {
			search_limit: cfg.search_limit,
			max_links_per_memory: cfg.max_links_per_memory,
			usage_normalisation_cap: cfg.usage_normalisation_cap,
			decay_lambda: cfg.decay_lambda,
			auto_link_enabled: cfg.auto_link_enabled,
			auto_link_k: cfg.auto_link_k,
			auto_link_threshold: cfg.auto_link_threshold,
		};
		draftLifecycle = {
			soft_delete_confidence_threshold: cfg.soft_delete_confidence_threshold,
			confidence_window_size: cfg.confidence_window_size,
		};
	}

	onMount(() => void load());

	// ── Dirty detection ─────────────────────────────────────────────────────────

	let dirtyWeights = $derived(
		config !== null &&
			(draftWeights.w_semantic !== config.w_semantic ||
				draftWeights.w_keyword !== config.w_keyword ||
				draftWeights.w_memory !== config.w_memory ||
				draftWeights.w_usage !== config.w_usage),
	);

	let dirtyScoring = $derived(
		config !== null &&
			(draftScoring.score_bump_up !== config.score_bump_up ||
				draftScoring.score_bump_down !== config.score_bump_down ||
				draftScoring.score_min !== config.score_min ||
				draftScoring.score_max !== config.score_max ||
				draftScoring.new_memory_default_score !== config.new_memory_default_score ||
				draftScoring.duplicate_threshold !== config.duplicate_threshold),
	);

	let dirtySearchLinks = $derived(
		config !== null &&
			(draftSearchLinks.search_limit !== config.search_limit ||
				draftSearchLinks.max_links_per_memory !== config.max_links_per_memory ||
				draftSearchLinks.usage_normalisation_cap !== config.usage_normalisation_cap ||
				draftSearchLinks.decay_lambda !== config.decay_lambda ||
				draftSearchLinks.auto_link_enabled !== config.auto_link_enabled ||
				draftSearchLinks.auto_link_k !== config.auto_link_k ||
				draftSearchLinks.auto_link_threshold !== config.auto_link_threshold),
	);

	let dirtyLifecycle = $derived(
		config !== null &&
			(draftLifecycle.soft_delete_confidence_threshold !==
				config.soft_delete_confidence_threshold ||
				draftLifecycle.confidence_window_size !== config.confidence_window_size),
	);

	let anyDirty = $derived(dirtyWeights || dirtyScoring || dirtySearchLinks || dirtyLifecycle);

	// ── Weight sum warning ──────────────────────────────────────────────────────

	let weightSum = $derived(
		+(
			draftWeights.w_semantic +
			draftWeights.w_keyword +
			draftWeights.w_memory +
			draftWeights.w_usage
		).toFixed(6),
	);
	let weightSumOk = $derived(Math.abs(weightSum - 1.0) < 0.001);

	// ── Save helpers ────────────────────────────────────────────────────────────

	async function saveSection(
		updates: ConfigUpdates,
		setSaving: (v: boolean) => void,
	): Promise<boolean> {
		setSaving(true);
		try {
			await patchConfig(updates);
			config = await fetchConfig();
			if (config) syncDrafts(config);
			showToast(S.saveSuccess, 'success');
			return true;
		} catch {
			showToast(S.saveError, 'error');
			return false;
		} finally {
			setSaving(false);
		}
	}

	async function saveWeights() {
		await saveSection({ ...draftWeights }, (v) => (savingWeights = v));
	}

	async function saveScoring() {
		await saveSection({ ...draftScoring }, (v) => (savingScoring = v));
	}

	async function saveSearchLinks() {
		await saveSection({ ...draftSearchLinks }, (v) => (savingSearchLinks = v));
	}

	async function saveLifecycle() {
		await saveSection({ ...draftLifecycle }, (v) => (savingLifecycle = v));
	}

	// ── Export ──────────────────────────────────────────────────────────────────

	async function handleExport() {
		try {
			const res = await fetch('/api/export');
			if (!res.ok) throw new Error();
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			const cd = res.headers.get('Content-Disposition') ?? '';
			const match = cd.match(/filename="([^"]+)"/);
			a.download = match?.[1] ?? 'lorekeeper-export.json';
			a.href = url;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			showToast(S.exportError, 'error');
		}
	}

	// ── Import ──────────────────────────────────────────────────────────────────

	async function handleImportFile(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		importLoading = true;
		importPreview = null;
		try {
			const form = new FormData();
			form.append('file', file);
			const res = await fetch('/api/import/preview', { method: 'POST', body: form });
			if (!res.ok) throw new Error();
			const data = (await res.json()) as { added: number; skipped: number; links?: number };
			importPreview = { added: data.added, skipped: data.skipped, links: data.links ?? 0, file };
		} catch {
			showToast(S.importPreviewError, 'error');
		} finally {
			importLoading = false;
			input.value = '';
		}
	}

	async function handleImportConfirm() {
		if (!importPreview) return;
		importConfirming = true;
		try {
			const form = new FormData();
			form.append('file', importPreview.file);
			const res = await fetch('/api/import/confirm', { method: 'POST', body: form });
			if (!res.ok) throw new Error();
			showToast('Import complete.', 'success');
			importPreview = null;
		} catch {
			showToast(S.importConfirmError, 'error');
		} finally {
			importConfirming = false;
		}
	}

	function handleImportCancel() {
		importPreview = null;
	}

	// ── Sweep ───────────────────────────────────────────────────────────────────

	async function handleTriggerSweep() {
		sweepTriggering = true;
		try {
			await triggerSweep();
			showToast(S.sweepTriggered, 'success');
			sweep = await fetchSweepStatus();
		} catch {
			showToast(S.sweepError, 'error');
		} finally {
			sweepTriggering = false;
		}
	}

	async function refreshSweepStatus() {
		try {
			sweep = await fetchSweepStatus();
		} catch {
			/* ignore */
		}
	}

	// ── Helpers ─────────────────────────────────────────────────────────────────

	function isOverridden(key: string): boolean {
		return config?._overridden_keys.includes(key) ?? false;
	}

	function formatTimestamp(ts: string | null | undefined): string {
		if (!ts) return S.sweepNever;
		try {
			return new Date(ts).toLocaleString();
		} catch {
			return ts;
		}
	}
</script>

<PageShell title={S.pageTitle} subtitle={S.pageSubtitle}>
	{#if loading}
		<div class="settings-loading" aria-busy="true">Loading…</div>
	{:else if error}
		<div class="settings-error" role="alert">{error}</div>
	{:else if config}
		<!-- Unsaved banner -->
		{#if anyDirty}
			<div class="unsaved-banner" role="status" aria-live="polite">
				<span class="unsaved-dot" aria-hidden="true">●</span>
				{S.unsavedBanner}
			</div>
		{/if}

		<div class="settings-layout">
			<!-- §1 Search Weights -->
			<section class="settings-section" aria-labelledby="section-weights-title">
				<div class="section-header">
					<div>
						<h2 id="section-weights-title" class="section-title">{S.sectionWeights}</h2>
						<p class="section-desc">{S.sectionWeightsDesc}</p>
					</div>
					{#if dirtyWeights}
						<span class="dirty-dot" aria-label={S.unsavedBanner}>●</span>
					{/if}
				</div>

				<div class="fields-grid">
					{#each [['w_semantic', S.labelWSemantic], ['w_keyword', S.labelWKeyword], ['w_memory', S.labelWMemory], ['w_usage', S.labelWUsage]] as [key, label] (key)}
						<label class="field-row">
							<span class="field-label">
								{label}
								{#if isOverridden(key)}
									<span
										class="override-dot"
										title={S.overriddenIndicatorAriaLabel}
										aria-label={S.overriddenIndicatorAriaLabel}>●</span
									>
								{/if}
							</span>
							<input
								type="number"
								min="0"
								max="1"
								step="0.01"
								class="field-input"
								bind:value={draftWeights[key as keyof typeof draftWeights]}
							/>
						</label>
					{/each}
				</div>

				{#if !weightSumOk}
					<p class="weight-warning" role="status">{S.weightSumWarning(weightSum)}</p>
				{/if}

				<div class="section-footer">
					<button
						class="btn-primary"
						onclick={saveWeights}
						disabled={!dirtyWeights || savingWeights}
					>
						{savingWeights ? 'Saving…' : S.saveButton}
					</button>
				</div>
			</section>

			<!-- §2 Scoring -->
			<section class="settings-section" aria-labelledby="section-scoring-title">
				<div class="section-header">
					<div>
						<h2 id="section-scoring-title" class="section-title">{S.sectionScoring}</h2>
						<p class="section-desc">{S.sectionScoringDesc}</p>
					</div>
					{#if dirtyScoring}
						<span class="dirty-dot" aria-label={S.unsavedBanner}>●</span>
					{/if}
				</div>

				<div class="fields-grid">
					{#each ([['score_bump_up', S.labelScoreBumpUp, 0, 1, 0.01], ['score_bump_down', S.labelScoreBumpDown, 0, 1, 0.01], ['score_min', S.labelScoreMin, 0, 10, 0.1], ['score_max', S.labelScoreMax, 0, 10, 0.1], ['new_memory_default_score', S.labelNewMemoryDefaultScore, 0, 10, 0.1], ['duplicate_threshold', S.labelDuplicateThreshold, 0, 1, 0.01]] as const) as [key, label, min, max, step] (key)}
						<label class="field-row">
							<span class="field-label">
								{label}
								{#if isOverridden(key)}
									<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
								{/if}
							</span>
							<input
								type="number"
								{min}
								{max}
								{step}
								class="field-input"
								bind:value={draftScoring[key as keyof typeof draftScoring]}
							/>
						</label>
					{/each}
				</div>

				<div class="section-footer">
					<button
						class="btn-primary"
						onclick={saveScoring}
						disabled={!dirtyScoring || savingScoring}
					>
						{savingScoring ? 'Saving…' : S.saveButton}
					</button>
				</div>
			</section>

			<!-- §3 Search & Links -->
			<section class="settings-section" aria-labelledby="section-search-links-title">
				<div class="section-header">
					<div>
						<h2 id="section-search-links-title" class="section-title">{S.sectionSearchLinks}</h2>
						<p class="section-desc">{S.sectionSearchLinksDesc}</p>
					</div>
					{#if dirtySearchLinks}
						<span class="dirty-dot" aria-label={S.unsavedBanner}>●</span>
					{/if}
				</div>

				<div class="fields-grid">
					<label class="field-row">
						<span class="field-label">
							{S.labelSearchLimit}
							{#if isOverridden('search_limit')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="1" step="1" class="field-input" bind:value={draftSearchLinks.search_limit} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelMaxLinksPerMemory}
							{#if isOverridden('max_links_per_memory')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="0" step="1" class="field-input" bind:value={draftSearchLinks.max_links_per_memory} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelUsageNormalisationCap}
							{#if isOverridden('usage_normalisation_cap')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="1" step="1" class="field-input" bind:value={draftSearchLinks.usage_normalisation_cap} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelDecayLambda}
							{#if isOverridden('decay_lambda')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="0" step="0.001" class="field-input" bind:value={draftSearchLinks.decay_lambda} />
					</label>
					<label class="field-row field-row--full">
						<span class="field-label">
							{S.labelAutoLinkEnabled}
							{#if isOverridden('auto_link_enabled')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="checkbox" class="field-checkbox" bind:checked={draftSearchLinks.auto_link_enabled} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelAutoLinkK}
							{#if isOverridden('auto_link_k')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="1" step="1" class="field-input" bind:value={draftSearchLinks.auto_link_k} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelAutoLinkThreshold}
							{#if isOverridden('auto_link_threshold')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="0" max="1" step="0.01" class="field-input" bind:value={draftSearchLinks.auto_link_threshold} />
					</label>
				</div>

				<div class="section-footer">
					<button
						class="btn-primary"
						onclick={saveSearchLinks}
						disabled={!dirtySearchLinks || savingSearchLinks}
					>
						{savingSearchLinks ? 'Saving…' : S.saveButton}
					</button>
				</div>
			</section>

			<!-- §4 Memory Lifecycle -->
			<section class="settings-section" aria-labelledby="section-lifecycle-title">
				<div class="section-header">
					<div>
						<h2 id="section-lifecycle-title" class="section-title">{S.sectionLifecycle}</h2>
						<p class="section-desc">{S.sectionLifecycleDesc}</p>
					</div>
					{#if dirtyLifecycle}
						<span class="dirty-dot" aria-label={S.unsavedBanner}>●</span>
					{/if}
				</div>

				<div class="fields-grid">
					<label class="field-row">
						<span class="field-label">
							{S.labelSoftDeleteThreshold}
							{#if isOverridden('soft_delete_confidence_threshold')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="0" step="1" class="field-input" bind:value={draftLifecycle.soft_delete_confidence_threshold} />
					</label>
					<label class="field-row">
						<span class="field-label">
							{S.labelConfidenceWindowSize}
							{#if isOverridden('confidence_window_size')}
								<span class="override-dot" title={S.overriddenIndicatorAriaLabel} aria-label={S.overriddenIndicatorAriaLabel}>●</span>
							{/if}
						</span>
						<input type="number" min="1" step="1" class="field-input" bind:value={draftLifecycle.confidence_window_size} />
					</label>
				</div>

				<div class="section-footer">
					<button
						class="btn-primary"
						onclick={saveLifecycle}
						disabled={!dirtyLifecycle || savingLifecycle}
					>
						{savingLifecycle ? 'Saving…' : S.saveButton}
					</button>
				</div>
			</section>

			<!-- §5 Data -->
			<section class="settings-section" aria-labelledby="section-data-title">
				<div class="section-header">
					<div>
						<h2 id="section-data-title" class="section-title">{S.sectionData}</h2>
						<p class="section-desc">{S.sectionDataDesc}</p>
					</div>
				</div>

				<!-- Read-only info -->
				<div class="readonly-fields">
					<div class="readonly-row">
						<span class="field-label">{S.labelDataDir}</span>
						<span class="readonly-value" title={S.readOnlyHint}>{config.data_dir}</span>
					</div>
					<div class="readonly-row">
						<span class="field-label">{S.labelEmbeddingModel}</span>
						<span class="readonly-value" title={S.readOnlyHint}>{config.embedding_model}</span>
					</div>
				</div>

				<div class="data-actions">
					<button class="btn-secondary" onclick={handleExport}>
						<Icon path={ICON_DOWNLOAD} size={14} />
						{S.exportButton}
					</button>

					<label class="btn-secondary file-btn">
						<Icon path={ICON_UPLOAD} size={14} />
						{importLoading ? 'Reading…' : S.importChooseFile}
						<input
							type="file"
							accept=".json"
							class="file-input-hidden"
							onchange={handleImportFile}
							disabled={importLoading}
						/>
					</label>
				</div>

				<!-- Import preview modal -->
				{#if importPreview}
					<div class="import-preview" role="region" aria-label={S.importPreviewTitle}>
						<p class="import-preview-title">{S.importPreviewTitle}</p>
						<ul class="import-preview-counts">
							<li>{S.importPreviewAdded(importPreview.added)}</li>
							<li>{S.importPreviewSkipped(importPreview.skipped)}</li>
							<li>{S.importPreviewLinks(importPreview.links)}</li>
						</ul>
						<div class="import-preview-actions">
							<button
								class="btn-primary"
								onclick={handleImportConfirm}
								disabled={importConfirming}
							>
								{importConfirming ? 'Importing…' : S.importConfirmButton}
							</button>
							<button class="btn-ghost" onclick={handleImportCancel}>{S.importCancelButton}</button>
						</div>
					</div>
				{/if}
			</section>

			<!-- §6 Maintenance -->
			<section class="settings-section" aria-labelledby="section-maintenance-title">
				<div class="section-header">
					<div>
						<h2 id="section-maintenance-title" class="section-title">{S.sectionMaintenance}</h2>
						<p class="section-desc">{S.sectionMaintenanceDesc}</p>
					</div>
				</div>

				{#if sweep}
					<div class="sweep-status">
						<div class="sweep-row">
							<span class="field-label">{S.sweepLastRun}</span>
							<span class="sweep-value">{formatTimestamp(sweep.last_run)}</span>
						</div>
						<div class="sweep-row">
							<span class="field-label">{S.sweepNextRun}</span>
							<span class="sweep-value">{formatTimestamp(sweep.next_run)}</span>
						</div>
					</div>
				{/if}

				<div class="section-footer">
					<button class="btn-primary" onclick={handleTriggerSweep} disabled={sweepTriggering}>
						{sweepTriggering ? 'Triggering…' : S.sweepTriggerButton}
					</button>
					<button class="btn-ghost" onclick={refreshSweepStatus}>
						<Icon path={ICON_REFRESH} size={14} />
						{S.refreshSweepButton}
					</button>
				</div>
			</section>
		</div>
	{/if}
</PageShell>

<style>
	.settings-loading,
	.settings-error {
		padding: 2rem;
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}
	.settings-error {
		color: var(--color-danger-text);
	}

	/* Unsaved banner */
	.unsaved-banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		margin-bottom: 1rem;
		background: var(--color-warning-bg);
		color: var(--color-warning-text);
		border-radius: 6px;
		font-size: 0.8125rem;
		font-weight: 500;
	}
	.unsaved-dot {
		font-size: 0.625rem;
	}

	/* Layout */
	.settings-layout {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* Section card */
	.settings-section {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: 1.25rem 1.5rem;
	}

	.section-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.section-title {
		font-size: 0.9375rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin: 0 0 0.25rem;
	}

	.section-desc {
		font-size: 0.8125rem;
		color: var(--color-text-muted);
		margin: 0;
	}

	.dirty-dot {
		font-size: 0.625rem;
		color: var(--color-warning-text);
		margin-top: 0.25rem;
	}

	/* Fields grid */
	.fields-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.75rem 1.25rem;
		margin-bottom: 1rem;
	}

	.field-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.field-row--full {
		grid-column: 1 / -1;
		flex-direction: row;
		align-items: center;
		gap: 0.75rem;
	}

	.field-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: var(--color-text-muted);
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.override-dot {
		font-size: 0.5rem;
		color: var(--color-warning-text);
		cursor: help;
	}

	.field-input {
		padding: 0.375rem 0.5rem;
		border: 1px solid var(--color-border);
		border-radius: 5px;
		font-size: 0.8125rem;
		color: var(--color-text-primary);
		background: var(--color-background);
		width: 100%;
		transition: border-color 0.15s;
	}

	.field-input:focus {
		outline: none;
		border-color: var(--color-brand);
	}

	.field-checkbox {
		width: 1rem;
		height: 1rem;
		accent-color: var(--color-brand);
	}

	/* Weight warning */
	.weight-warning {
		font-size: 0.8rem;
		color: var(--color-warning-text);
		background: var(--color-warning-bg);
		border-radius: 5px;
		padding: 0.4rem 0.75rem;
		margin-bottom: 0.75rem;
	}

	/* Section footer */
	.section-footer {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	/* Read-only */
	.readonly-fields {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.readonly-row {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
	}

	.readonly-value {
		font-size: 0.8125rem;
		color: var(--color-text-muted);
		font-family: monospace;
	}

	/* Data actions */
	.data-actions {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}

	.file-btn {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.375rem;
	}

	.file-input-hidden {
		display: none;
	}

	/* Import preview */
	.import-preview {
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: 1rem;
		background: var(--color-background);
	}

	.import-preview-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin: 0 0 0.5rem;
	}

	.import-preview-counts {
		list-style: none;
		padding: 0;
		margin: 0 0 0.75rem;
		font-size: 0.8125rem;
		color: var(--color-text-body);
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.import-preview-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* Sweep */
	.sweep-status {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.sweep-row {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
	}

	.sweep-value {
		font-size: 0.8125rem;
		color: var(--color-text-body);
	}

	/* Buttons */
	.btn-primary {
		padding: 0.375rem 0.875rem;
		background: var(--color-brand);
		color: #fff;
		border: none;
		border-radius: 5px;
		font-size: 0.8125rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--color-brand-hover);
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		padding: 0.375rem 0.75rem;
		background: var(--color-background);
		color: var(--color-text-body);
		border: 1px solid var(--color-border);
		border-radius: 5px;
		font-size: 0.8125rem;
		font-weight: 500;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.375rem;
		transition: border-color 0.15s;
	}

	.btn-secondary:hover {
		border-color: var(--color-border-strong);
	}

	.btn-ghost {
		padding: 0.375rem 0.625rem;
		background: transparent;
		color: var(--color-text-muted);
		border: none;
		border-radius: 5px;
		font-size: 0.8125rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.375rem;
	}

	.btn-ghost:hover {
		background: var(--color-hover-bg);
	}
</style>
