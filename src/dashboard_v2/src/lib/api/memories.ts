/**
 * API helpers for the memories page.
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

export interface MemoryRow {
	lore_id: string;
	title: string;
	namespace: string;
	score: number;
	confidence: number;
	usage_count: number;
	links_count: number;
	updated_at: string;
	created_at: string;
	description: string;
	soft_deleted: boolean;
	source_type: string;
	content: string;
}

export interface PaginatedResponse {
	memories: MemoryRow[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
}

export interface MemoriesParams {
	page?: number;
	per_page?: number;
	q?: string;
	namespace?: string;
	include_deleted?: boolean;
	filter?: string;
	sort?: string;
	sort_dir?: 'asc' | 'desc';
}

export interface MemoryCounts {
	all: number;
	needs_review: number;
	high_confidence: number;
	stale_30d: number;
}

function buildQuery(params: MemoriesParams): string {
	const parts: string[] = [];
	if (params.page !== undefined) parts.push(`page=${params.page}`);
	if (params.per_page !== undefined) parts.push(`per_page=${params.per_page}`);
	if (params.q) parts.push(`q=${encodeURIComponent(params.q)}`);
	if (params.namespace) parts.push(`namespace=${encodeURIComponent(params.namespace)}`);
	if (params.include_deleted) parts.push('include_deleted=true');
	if (params.filter) parts.push(`filter=${encodeURIComponent(params.filter)}`);
	if (params.sort) parts.push(`sort=${encodeURIComponent(params.sort)}`);
	if (params.sort_dir) parts.push(`sort_dir=${params.sort_dir}`);
	return parts.length ? '?' + parts.join('&') : '';
}

export async function fetchMemories(
	params: MemoriesParams & { page: number } = { page: 1 },
): Promise<PaginatedResponse> {
	const qs = buildQuery(params);
	return api<PaginatedResponse>('GET', `/api/memories${qs}`);
}

export async function fetchMemoryCounts(): Promise<MemoryCounts> {
	return api<MemoryCounts>('GET', '/api/memories/counts');
}

export async function fetchNamespaces(): Promise<string[]> {
	return api<string[]>('GET', '/api/namespaces');
}

export async function fetchMemoryDetail(id: string): Promise<{ memory: MemoryRow; links: unknown[] }> {
	return api('GET', `/api/memories/${id}`);
}