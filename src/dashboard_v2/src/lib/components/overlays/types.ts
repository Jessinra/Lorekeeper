/**
 * Memory data shape for the MemoryDetailDrawer component.
 * Mirrors the fields returned by the Lorekeeper API.
 */
export interface MemoryData {
	lore_id: string;
	title: string;
	description: string;
	content: string;
	namespace: string;
	source_type: string;
	score: number;
	confidence: number;
	usage_count: number;
	soft_deleted: boolean;
	created_at: string;
	updated_at: string;
}

/**
 * Link data for the linked-memories section of the drawer.
 */
export interface LinkData {
	target_id: string;
	target_title: string;
	relation_type: string;
}

/**
 * Editable fields that can be sent via PATCH /api/memories/{id}.
 */
export interface MemoryEditFields {
	title?: string;
	description?: string;
	content?: string;
	score?: number;
	source_type?: string;
	soft_deleted?: boolean;
}