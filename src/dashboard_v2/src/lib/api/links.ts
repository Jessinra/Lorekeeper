export interface LinkRow {
	id: string;
	source_memory_id: string;
	target_memory_id: string;
	relation_type: string;
	reason: string;
	score: number;
	created_at: string;
	updated_at: string;
	usage_count: number;
	confidence: number | null;
	confidence_count: number;
	source_title: string;
	target_title: string;
}

export async function fetchLinks(includeDeleted = false): Promise<LinkRow[]> {
	const params = new URLSearchParams();
	if (includeDeleted) params.set('include_deleted', 'true');
	const res = await fetch(`/api/links?${params.toString()}`);
	if (!res.ok) throw new Error(`Failed to fetch links: ${res.statusText}`);
	return res.json() as Promise<LinkRow[]>;
}

export async function deleteLink(linkId: string): Promise<boolean> {
	const res = await fetch(`/api/links/${encodeURIComponent(linkId)}`, { method: 'DELETE' });
	return res.ok;
}
