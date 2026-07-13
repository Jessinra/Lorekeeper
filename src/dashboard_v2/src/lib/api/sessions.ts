/**
 * API helpers for the sessions page.
 */

const BASE = '';

async function api<T>(method: string, path: string): Promise<T> {
	const res = await fetch(`${BASE}${path}`, { method });
	if (!res.ok) {
		throw new Error(`API ${method} ${path}: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export interface SessionRow {
	session_id: string;
	session_date: string | null;
	topic: string | null;
	task_type: string | null;
	reviewed_at: string;
	reflection_id: string | null;
	what_was_done: string | null;
	summary?: string | null;
}

export interface SessionMemory {
	lore_id: string;
	title: string;
	description: string;
	score: number;
	namespace: string;
	source_type: string;
}

export interface SessionDetail {
	session: SessionRow;
	reflection: { id: string; created_at: string; summary: string } | null;
	memories: SessionMemory[];
}

export interface SessionsResponse {
	sessions: SessionRow[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
	task_counts: Record<string, number>;
}

export interface SessionsParams {
	q?: string;
	task?: string;
	page?: number;
	page_size?: number;
}

function buildQuery(params: SessionsParams): string {
	const p = new URLSearchParams();
	if (params.q) p.set('q', params.q);
	if (params.task) p.set('task', params.task);
	if (params.page) p.set('page', String(params.page));
	if (params.page_size) p.set('page_size', String(params.page_size));
	const s = p.toString();
	return s ? `?${s}` : '';
}

export function fetchSessions(params: SessionsParams = {}): Promise<SessionsResponse> {
	return api<SessionsResponse>('GET', `/api/sessions${buildQuery(params)}`);
}

export function fetchSessionDetail(sessionId: string): Promise<SessionDetail> {
	return api<SessionDetail>('GET', `/api/sessions/${encodeURIComponent(sessionId)}`);
}
