/**
 * API client for /api/metrics/tool-calls
 */

export interface HeatmapCell {
	[tool: string]: number; // includes "total" key
	total: number;
}

export interface ToolCallsResponse {
	hours: number;
	timezone: string;
	total_calls: number;
	avg_calls_per_day: number;
	tools: string[];
	tool_totals: Record<string, number>;
	days: string[]; // YYYY-MM-DD, oldest first
	heatmap: Record<string, Record<string, HeatmapCell>>; // day → hour_str → cell
}

export async function fetchToolCalls(hours: number = 168): Promise<ToolCallsResponse> {
	const res = await fetch(`/api/metrics/tool-calls?hours=${hours}`);
	if (!res.ok) throw new Error(`Failed to fetch metrics: ${res.status}`);
	return res.json() as Promise<ToolCallsResponse>;
}
