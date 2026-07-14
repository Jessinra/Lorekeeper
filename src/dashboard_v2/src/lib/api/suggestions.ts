/**
 * API helpers for the review inbox (suggestions).
 */

const BASE = '';

async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		method,
		headers: body ? { 'Content-Type': 'application/json' } : undefined,
		body: body ? JSON.stringify(body) : undefined,
	});
	if (!res.ok) {
		throw new Error(`API ${method} ${path}: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export interface SuggestionRow {
	id: string;
	source_memory_id: string;
	source_title: string;
	target_memory_id: string;
	target_title: string;
	weighted_score: number;
	cosine_score: number;
	bm25_score: number;
	entity_score: number;
	temporal_score: number;
	confidence: number;
	created_at: string;
}

export interface SuggestionsResponse {
	items: SuggestionRow[];
	total: number;
	offset: number;
}

export interface SuggestionsParams {
	limit?: number;
	offset?: number;
	sort_by?: string;
	sort_dir?: 'asc' | 'desc';
	memory_id?: string;
	status?: 'pending' | 'reviewed';
}

export interface BatchResultItem {
	id: string;
	status: string;
	message: string;
}

export interface BatchResponse {
	results: BatchResultItem[];
	accepted: number;
	rejected: number;
	errors: string[];
}

function buildQuery(params: SuggestionsParams): string {
	const p = new URLSearchParams();
	if (params.limit !== undefined) p.set('limit', String(params.limit));
	if (params.offset !== undefined) p.set('offset', String(params.offset));
	if (params.sort_by) p.set('sort_by', params.sort_by);
	if (params.sort_dir) p.set('sort_dir', params.sort_dir);
	if (params.memory_id) p.set('memory_id', params.memory_id);
	if (params.status) p.set('status', params.status);
	const s = p.toString();
	return s ? `?${s}` : '';
}

export function fetchSuggestions(params: SuggestionsParams = {}): Promise<SuggestionsResponse> {
	return api<SuggestionsResponse>('GET', `/api/suggestions${buildQuery(params)}`);
}

export function fetchSuggestionCount(memory_id?: string): Promise<{ count: number }> {
	const qs = memory_id ? `?memory_id=${encodeURIComponent(memory_id)}` : '';
	return api<{ count: number }>('GET', `/api/suggestions/count${qs}`);
}

export function batchSuggestions(
	suggestion_ids: string[],
	action: 'accept' | 'reject',
): Promise<BatchResponse> {
	return api<BatchResponse>('POST', '/api/suggestions/batch', { suggestion_ids, action });
}
