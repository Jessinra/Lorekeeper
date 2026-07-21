/**
 * API helpers for sweep control.
 */

export interface SweepStatus {
	last_run: string | null;
	next_run: string | null;
}

export async function fetchSweepStatus(): Promise<SweepStatus> {
	const res = await fetch('/api/sweep/status');
	if (!res.ok) throw new Error(`Failed to fetch sweep status: ${res.status}`);
	return res.json() as Promise<SweepStatus>;
}

export async function triggerSweep(): Promise<void> {
	const res = await fetch('/api/sweep/trigger', { method: 'POST' });
	if (!res.ok) throw new Error(`Failed to trigger sweep: ${res.status}`);
}
