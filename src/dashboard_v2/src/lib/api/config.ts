/**
 * API helpers for the settings/config page.
 */

export interface ConfigData {
	data_dir: string;
	embedding_model: string;
	duplicate_threshold: number;
	w_semantic: number;
	w_keyword: number;
	w_memory: number;
	w_usage: number;
	score_bump_up: number;
	score_bump_down: number;
	score_min: number;
	score_max: number;
	soft_delete_confidence_threshold: number;
	confidence_window_size: number;
	search_limit: number;
	max_links_per_memory: number;
	usage_normalisation_cap: number;
	decay_lambda: number;
	new_memory_default_score: number;
	auto_link_enabled: boolean;
	auto_link_k: number;
	auto_link_threshold: number;
	_overridden_keys: string[];
}

export type ConfigUpdates = Partial<Omit<ConfigData, 'data_dir' | 'embedding_model' | '_overridden_keys'>>;

export async function fetchConfig(): Promise<ConfigData> {
	const res = await fetch('/api/config');
	if (!res.ok) throw new Error(`Failed to fetch config: ${res.status}`);
	return res.json() as Promise<ConfigData>;
}

export async function patchConfig(updates: ConfigUpdates): Promise<void> {
	const res = await fetch('/api/config', {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(updates),
	});
	if (!res.ok) {
		const detail = await res.text().catch(() => res.statusText);
		throw new Error(`Failed to save config: ${detail}`);
	}
}
