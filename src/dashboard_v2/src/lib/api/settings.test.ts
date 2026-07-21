import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchConfig, patchConfig } from '$lib/api/config.js';
import { fetchSweepStatus, triggerSweep } from '$lib/api/sweep.js';

// ── fetchConfig ───────────────────────────────────────────────────────────────

describe('fetchConfig', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});
	afterEach(() => vi.unstubAllGlobals());

	it('returns parsed config on success', async () => {
		const mockConfig = {
			data_dir: '/tmp/.lorekeeper',
			embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
			w_semantic: 0.45,
			w_keyword: 0.3,
			w_memory: 0.15,
			w_usage: 0.1,
			duplicate_threshold: 0.85,
			score_bump_up: 0.5,
			score_bump_down: 0.3,
			score_min: 0.0,
			score_max: 10.0,
			soft_delete_confidence_threshold: 2,
			confidence_window_size: 20,
			search_limit: 200,
			max_links_per_memory: 10,
			usage_normalisation_cap: 100,
			decay_lambda: 0.01,
			new_memory_default_score: 7.0,
			auto_link_enabled: true,
			auto_link_k: 5,
			auto_link_threshold: 0.75,
			_overridden_keys: ['w_semantic'],
		};
		vi.mocked(fetch).mockResolvedValue({
			ok: true,
			json: async () => mockConfig,
		} as Response);

		const result = await fetchConfig();
		expect(result.w_semantic).toBe(0.45);
		expect(result._overridden_keys).toContain('w_semantic');
		expect(fetch).toHaveBeenCalledWith('/api/config');
	});

	it('throws on non-ok response', async () => {
		vi.mocked(fetch).mockResolvedValue({ ok: false, status: 500 } as Response);
		await expect(fetchConfig()).rejects.toThrow('Failed to fetch config: 500');
	});
});

// ── patchConfig ───────────────────────────────────────────────────────────────

describe('patchConfig', () => {
	beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
	afterEach(() => vi.unstubAllGlobals());

	it('sends PATCH with JSON body', async () => {
		vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);
		await patchConfig({ w_semantic: 0.5 });
		expect(fetch).toHaveBeenCalledWith('/api/config', {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ w_semantic: 0.5 }),
		});
	});

	it('throws on non-ok response', async () => {
		vi.mocked(fetch).mockResolvedValue({
			ok: false,
			text: async () => 'validation error',
		} as Response);
		await expect(patchConfig({ w_semantic: 99 })).rejects.toThrow('Failed to save config');
	});
});

// ── fetchSweepStatus ──────────────────────────────────────────────────────────

describe('fetchSweepStatus', () => {
	beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
	afterEach(() => vi.unstubAllGlobals());

	it('returns last_run and next_run', async () => {
		const status = { last_run: '2026-07-21T00:00:00Z', next_run: '2026-07-21T01:00:00Z' };
		vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => status } as Response);
		const result = await fetchSweepStatus();
		expect(result.last_run).toBe(status.last_run);
		expect(result.next_run).toBe(status.next_run);
	});

	it('handles null timestamps', async () => {
		vi.mocked(fetch).mockResolvedValue({
			ok: true,
			json: async () => ({ last_run: null, next_run: null }),
		} as Response);
		const result = await fetchSweepStatus();
		expect(result.last_run).toBeNull();
	});

	it('throws on non-ok response', async () => {
		vi.mocked(fetch).mockResolvedValue({ ok: false, status: 503 } as Response);
		await expect(fetchSweepStatus()).rejects.toThrow('Failed to fetch sweep status: 503');
	});
});

// ── triggerSweep ──────────────────────────────────────────────────────────────

describe('triggerSweep', () => {
	beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
	afterEach(() => vi.unstubAllGlobals());

	it('POSTs to /api/sweep/trigger', async () => {
		vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);
		await triggerSweep();
		expect(fetch).toHaveBeenCalledWith('/api/sweep/trigger', { method: 'POST' });
	});

	it('throws on non-ok response', async () => {
		vi.mocked(fetch).mockResolvedValue({ ok: false, status: 500 } as Response);
		await expect(triggerSweep()).rejects.toThrow('Failed to trigger sweep: 500');
	});
});
