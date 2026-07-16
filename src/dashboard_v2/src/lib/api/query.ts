/**
 * API helpers for the Query (debug relevance) page.
 */

const BASE = '';

class EndpointNotFoundError extends Error {
	constructor(path: string) {
		super(`Endpoint not found: ${path}`);
	}
}

async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		method,
		headers: body ? { 'Content-Type': 'application/json' } : undefined,
		body: body ? JSON.stringify(body) : undefined,
	});
	if (!res.ok) {
		if (res.status === 404) {
			throw new EndpointNotFoundError(path);
		}
		throw new Error(`API ${method} ${path}: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export interface DebugMemory {
	id: string;
	title: string;
	namespace: string;
	score: number;
	usage_count: number;
	content: string;
	link_count: number;
	soft_deleted: boolean;
}

export interface DebugResult {
	rank: number;
	memory: DebugMemory;
	combined_score: number;
	semantic_score: number;
	keyword_score: number;
	memory_score: number;
	usage_score: number;
}

export interface DebugQueryResponse {
	results: DebugResult[];
	total_results: number;
	total_linked: number;
	elapsed_ms: number;
}

export interface DebugQueryParams {
	query: string;
	limit?: number;
	min_score?: number;
	include_deleted?: boolean;
}

/**
 * Run a debug query against the relevance engine.
 *
 * Calls POST /api/query/debug. Falls back to POST /api/search if the endpoint
 * is unavailable, deriving mock per-signal scores from the combined score.
 */
export async function runDebugQuery(params: DebugQueryParams): Promise<DebugQueryResponse> {
	try {
		return await api<DebugQueryResponse>('POST', '/api/query/debug', {
			query: params.query,
			limit: params.limit ?? 10,
			min_score: params.min_score ?? 0.1,
			include_deleted: params.include_deleted ?? false,
		});
	} catch (err) {
		// Only fall back to /api/search when the debug endpoint is absent (404).
		// Any other failure (500, network error, etc.) is a real problem — re-throw.
		if (!(err instanceof EndpointNotFoundError)) {
			throw err;
		}
		// Fallback: use /api/search and derive mock per-signal scores
		const searchRes = await api<
			Array<{
				memory: { lore_id: string; title: string; namespace: string; score: number; usage_count: number; content: string };
				relevance: { combined_score: number };
			}>
		>('POST', '/api/search', {
			query: params.query,
			limit: params.limit ?? 10,
			min_score: params.min_score ?? 0.1,
		});

		const results: DebugResult[] = searchRes.map((item, index) => {
			const combined = item.relevance.combined_score;
			return {
				rank: index + 1,
				memory: {
					id: item.memory.lore_id,
					title: item.memory.title,
					namespace: item.memory.namespace,
					score: item.memory.score,
					usage_count: item.memory.usage_count,
					content: item.memory.content,
					link_count: 0,
					soft_deleted: false,
				},
				combined_score: combined,
				semantic_score: combined * 0.55,
				keyword_score: combined * 0.3,
				memory_score: combined * 0.1,
				usage_score: combined * 0.05,
			};
		});

		return {
			results,
			total_results: results.length,
			total_linked: 0,
			elapsed_ms: 0,
		};
	}
}
