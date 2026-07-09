import { describe, it, expect, vi } from 'vitest';
import { buildCommands, filterCommands, GROUP_ORDER } from '$lib/commands.js';
import type { Command } from '$lib/commands.js';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeOpts() {
	return {
		navigate: vi.fn(),
		openQuery: vi.fn(),
		openSettings: vi.fn()
	};
}

// ─── buildCommands ────────────────────────────────────────────────────────────

describe('buildCommands', () => {
	it('returns an array of Command objects', () => {
		const commands = buildCommands(makeOpts());
		expect(Array.isArray(commands)).toBe(true);
		expect(commands.length).toBeGreaterThan(0);
	});

	it('every command has id, label, group, and action', () => {
		const commands = buildCommands(makeOpts());
		for (const cmd of commands) {
			expect(cmd.id).toBeTruthy();
			expect(cmd.label).toBeTruthy();
			expect(['recent', 'jump', 'actions']).toContain(cmd.group);
			expect(typeof cmd.action).toBe('function');
		}
	});

	it('ids are unique', () => {
		const commands = buildCommands(makeOpts());
		const ids = commands.map((c) => c.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('jump commands are generated from NAV_ROUTES', () => {
		const commands = buildCommands(makeOpts());
		const jumpCmds = commands.filter((c) => c.group === 'jump');
		expect(jumpCmds.length).toBeGreaterThan(0);
		// All jump commands should have an href-style hint
		for (const cmd of jumpCmds) {
			expect(cmd.hint).toMatch(/^\//);
		}
	});

	it('action commands include openQuery and openSettings', () => {
		const opts = makeOpts();
		const commands = buildCommands(opts);
		const actions = commands.filter((c) => c.group === 'actions');
		expect(actions.some((c) => c.id === 'action:open-query')).toBe(true);
		expect(actions.some((c) => c.id === 'action:open-settings')).toBe(true);
	});

	it('calling jump action triggers navigate with the correct href', () => {
		const opts = makeOpts();
		const commands = buildCommands(opts);
		const memoriesCmd = commands.find((c) => c.id === 'jump:/memories');
		expect(memoriesCmd).toBeDefined();
		memoriesCmd!.action();
		expect(opts.navigate).toHaveBeenCalledWith('/memories');
	});

	it('calling action:open-query triggers openQuery callback', () => {
		const opts = makeOpts();
		const commands = buildCommands(opts);
		const queryCmd = commands.find((c) => c.id === 'action:open-query');
		queryCmd!.action();
		expect(opts.openQuery).toHaveBeenCalledOnce();
	});

	it('calling action:open-settings triggers openSettings callback', () => {
		const opts = makeOpts();
		const commands = buildCommands(opts);
		const settingsCmd = commands.find((c) => c.id === 'action:open-settings');
		settingsCmd!.action();
		expect(opts.openSettings).toHaveBeenCalledOnce();
	});
});

// ─── filterCommands ───────────────────────────────────────────────────────────

describe('filterCommands', () => {
	const cmds: Command[] = [
		{ id: 'a', label: 'Memories', hint: '/memories', group: 'jump', action: vi.fn() },
		{ id: 'b', label: 'Open query', hint: 'Query', group: 'actions', action: vi.fn() },
		{ id: 'c', label: 'Settings', hint: '/settings', group: 'jump', action: vi.fn() },
		{ id: 'd', label: 'Links', hint: '/links', group: 'jump', action: vi.fn() }
	];

	it('returns all commands on empty query', () => {
		expect(filterCommands(cmds, '').length).toBe(4);
	});

	it('returns all commands on whitespace-only query', () => {
		expect(filterCommands(cmds, '   ').length).toBe(4);
	});

	it('filters by label (case-insensitive)', () => {
		const results = filterCommands(cmds, 'MEM');
		expect(results.map((c) => c.id)).toEqual(['a']);
	});

	it('filters by hint (case-insensitive)', () => {
		const results = filterCommands(cmds, '/settings');
		expect(results.map((c) => c.id)).toEqual(['c']);
	});

	it('returns empty array on no match', () => {
		expect(filterCommands(cmds, 'zzz')).toHaveLength(0);
	});

	it('matches multiple items with a broad query', () => {
		// "s" matches "Memories" (no), "Settings" (yes), "Links" (no), "Open query" (no), hint /settings (yes for Settings)
		const results = filterCommands(cmds, 's');
		// "Memories" has no 's' in label or hint '/memories' -> no
		// "Open query" -> no
		// "Settings" label has 's' -> yes
		// "Links" label has 's' -> yes
		expect(results.map((c) => c.id)).toContain('c'); // Settings
		expect(results.map((c) => c.id)).toContain('d'); // Links
	});

	it('preserves command order within a group', () => {
		const results = filterCommands(cmds, '');
		expect(results.map((c) => c.id)).toEqual(['a', 'b', 'c', 'd']);
	});
});

// ─── GROUP_ORDER ──────────────────────────────────────────────────────────────

describe('GROUP_ORDER', () => {
	it('contains recent, jump, and actions', () => {
		expect(GROUP_ORDER).toContain('recent');
		expect(GROUP_ORDER).toContain('jump');
		expect(GROUP_ORDER).toContain('actions');
	});

	it('has length 3', () => {
		expect(GROUP_ORDER).toHaveLength(3);
	});
});
