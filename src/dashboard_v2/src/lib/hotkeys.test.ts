import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { attachCommandPaletteHotkey } from '$lib/hotkeys.js';

describe('attachCommandPaletteHotkey', () => {
	let cleanup: () => void;

	afterEach(() => {
		cleanup?.();
	});

	function fire(key: string, options: Partial<KeyboardEventInit> = {}) {
		const event = new KeyboardEvent('keydown', { key, bubbles: true, ...options });
		window.dispatchEvent(event);
		return event;
	}

	it('calls onOpen on ⌘K (metaKey)', () => {
		// Simulate macOS
		vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k', { metaKey: true });

		expect(onOpen).toHaveBeenCalledOnce();
	});

	it('calls onOpen on Ctrl+K (non-Mac)', () => {
		vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k', { ctrlKey: true });

		expect(onOpen).toHaveBeenCalledOnce();
	});

	it('does NOT call onOpen on bare K', () => {
		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k');

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('does NOT call onOpen on ⌘J', () => {
		vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('j', { metaKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('removes listener after cleanup is called', () => {
		vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');

		const onOpen = vi.fn();
		const teardown = attachCommandPaletteHotkey(onOpen);
		teardown();

		fire('k', { metaKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('does NOT call onOpen on Mac when ctrlKey is used (not meta)', () => {
		vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k', { ctrlKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});
});
