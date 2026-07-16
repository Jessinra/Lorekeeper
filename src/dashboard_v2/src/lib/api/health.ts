/**
 * API helpers for the home page health overview.
 */

async function api<T>(method: string, path: string): Promise<T> {
	const res = await fetch(path, { method });
	if (!res.ok) {
		throw new Error(`API ${method} ${path}: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
}

export interface ActivityItem {
	id: string;
	topic: string;
	task_type: string;
	session_date: string;
	session_count: number;
}

export interface HealthData {
	health_percent: number;
	total_memories: number;
	high_confidence: number;
	needs_review: number;
	stale_30d: number;
	total_links: number;
	pending_suggestions: number;
	recent_activity: ActivityItem[];
}

export async function fetchHealth(): Promise<HealthData> {
	return api<HealthData>('GET', '/api/health');
}
