import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import CommandPalette from '$lib/components/overlays/CommandPalette.svelte';
import type { Command } from '$lib/commands.js';

// ─── Fixtures ────────────────────────────────────────────────────────────────

function makeCommand(overrides: Partial<Command> = {}): Command {
	return {
		id: 'jump:/home',
		label: 'Home',
		group: 'jump',
		action: vi.fn(),
		...overrides
	};
}

const jumpHome: Command = makeCommand({ id: 'jump:/home', label: 'Home', group: 'jump' });
const jumpMemories: Command = makeCommand({ id: 'jump:/memories', label: 'Memories', group: 'jump' });
const actionSearch: Command = makeCommand({
	id: 'action:open-query',
	label: 'Search memories',
	group: 'actions',
	action: vi.fn()
});

const baseCommands: Command[] = [jumpHome, jumpMemories, actionSearch];

function renderPalette(overrides: { commands?: Command[]; open?: boolean; onClose?: () => void } = {}) {
	const onClose = overrides.onClose ?? vi.fn();
	const utils = render(CommandPalette, {
		props: {
			open: overrides.open ?? true,
			commands: overrides.commands ?? baseCommands,
			onClose
		}
	});
	return { ...utils, onClose };
}

// ─── Rendering ────────────────────────────────────────────────────────────────

describe('CommandPalette — rendering', () => {
	it('renders dialog with role="dialog" and aria-modal when open', () => {
		const { getByRole } = renderPalette();
		const dialog = getByRole('dialog');
		expect(dialog).toBeInTheDocument();
		expect(dialog).toHaveAttribute('aria-modal', 'true');
	});

	it('does not render when open is false', () => {
		const { queryByRole } = renderPalette({ open: false });
		expect(queryByRole('dialog')).not.toBeInTheDocument();
	});

	it('renders all command labels', () => {
		const { getByText } = renderPalette();
		expect(getByText('Home')).toBeInTheDocument();
		expect(getByText('Memories')).toBeInTheDocument();
		expect(getByText('Search memories')).toBeInTheDocument();
	});

	it('renders group headers', () => {
		const { getByText } = renderPalette();
		expect(getByText('Jump to')).toBeInTheDocument();
		expect(getByText('Actions')).toBeInTheDocument();
	});

	it('does not render Recent header when recent group is empty', () => {
		const { queryByText } = renderPalette();
		expect(queryByText('Recent')).not.toBeInTheDocument();
	});

	it('shows empty state when no commands match query', async () => {
		const { getByPlaceholderText, container } = renderPalette();
		const input = getByPlaceholderText(/search/i);
		await fireEvent.input(input, { target: { value: 'zzznomatch' } });
		expect(container.querySelector('.empty-state')).toBeInTheDocument();
	});
});

// ─── Filtering ────────────────────────────────────────────────────────────────

describe('CommandPalette — filtering', () => {
	it('filters commands by label (case-insensitive)', async () => {
		const { getByPlaceholderText, queryByText } = renderPalette();
		const input = getByPlaceholderText(/search/i);
		await fireEvent.input(input, { target: { value: 'mem' } });
		expect(queryByText('Memories')).toBeInTheDocument();
		expect(queryByText('Search memories')).toBeInTheDocument();
		expect(queryByText('Home')).not.toBeInTheDocument();
	});

	it('resets filter on re-open (open toggle)', async () => {
		const { getByPlaceholderText, rerender, queryByText } = renderPalette();
		const input = getByPlaceholderText(/search/i);
		await fireEvent.input(input, { target: { value: 'home' } });
		expect(queryByText('Memories')).not.toBeInTheDocument();

		// Simulate close then re-open
		await rerender({ open: false, commands: baseCommands, onClose: vi.fn() });
		await rerender({ open: true, commands: baseCommands, onClose: vi.fn() });
		// All items should be visible again
		expect(queryByText('Memories')).toBeInTheDocument();
	});
});

// ─── Keyboard navigation ──────────────────────────────────────────────────────

describe('CommandPalette — keyboard navigation', () => {
	beforeEach(() => {
		// Clear mock call counts between tests
		baseCommands.forEach((c) => vi.mocked(c.action).mockClear?.());
	});

	it('ArrowDown highlights the next command', async () => {
		const { container } = renderPalette();
		// Initially, first item should be active
		const items = () => container.querySelectorAll('.palette-item');
		expect(items()[0]).toHaveClass('active');

		await fireEvent.keyDown(window, { key: 'ArrowDown' });
		expect(items()[1]).toHaveClass('active');
		expect(items()[0]).not.toHaveClass('active');
	});

	it('ArrowUp wraps from first to last', async () => {
		const { container } = renderPalette();
		const items = () => container.querySelectorAll('.palette-item');
		// First item active; go up → should wrap to last
		await fireEvent.keyDown(window, { key: 'ArrowUp' });
		const allItems = items();
		expect(allItems[allItems.length - 1]).toHaveClass('active');
	});

	it('ArrowDown wraps from last to first', async () => {
		const { container } = renderPalette();
		const items = () => container.querySelectorAll('.palette-item');
		const total = items().length;
		// Navigate to last item
		for (let i = 0; i < total - 1; i++) {
			await fireEvent.keyDown(window, { key: 'ArrowDown' });
		}
		expect(items()[total - 1]).toHaveClass('active');
		// One more down → wrap to first
		await fireEvent.keyDown(window, { key: 'ArrowDown' });
		expect(items()[0]).toHaveClass('active');
	});

	it('Enter invokes the active command and closes', async () => {
		const onClose = vi.fn();
		const jumpHomeAction = vi.fn();
		const cmds: Command[] = [makeCommand({ id: 'jump:/home', label: 'Home', group: 'jump', action: jumpHomeAction })];
		renderPalette({ commands: cmds, onClose });

		await fireEvent.keyDown(window, { key: 'Enter' });

		expect(jumpHomeAction).toHaveBeenCalledOnce();
		expect(onClose).toHaveBeenCalledOnce();
	});

	it('Enter does not call onClose twice when action also closes', async () => {
		// The command action should NOT call onClose — palette handles that.
		// Verifies the double-close bug is fixed (Copilot comment #3550407439).
		const onClose = vi.fn();
		const action = vi.fn(); // plain action, no onClose call inside
		const cmds: Command[] = [makeCommand({ action })];
		renderPalette({ commands: cmds, onClose });

		await fireEvent.keyDown(window, { key: 'Enter' });
		expect(onClose).toHaveBeenCalledOnce();
	});

	it('Escape closes without invoking any command', async () => {
		const onClose = vi.fn();
		const action = vi.fn();
		renderPalette({ commands: [makeCommand({ action })], onClose });

		await fireEvent.keyDown(window, { key: 'Escape' });

		expect(action).not.toHaveBeenCalled();
		expect(onClose).toHaveBeenCalledOnce();
	});

	it('mouse enter changes active highlight', async () => {
		const { container } = renderPalette();
		const items = () => container.querySelectorAll<HTMLElement>('.palette-item');
		// Hover second item
		await fireEvent.mouseEnter(items()[1]);
		expect(items()[1]).toHaveClass('active');
		expect(items()[0]).not.toHaveClass('active');
	});

	it('click on a command invokes action and closes', async () => {
		const onClose = vi.fn();
		const action = vi.fn();
		const { container } = renderPalette({
			commands: [makeCommand({ action })],
			onClose
		});
		const item = container.querySelector<HTMLElement>('.palette-item');
		expect(item).not.toBeNull();
		await fireEvent.click(item!);

		expect(action).toHaveBeenCalledOnce();
		expect(onClose).toHaveBeenCalledOnce();
	});
});
