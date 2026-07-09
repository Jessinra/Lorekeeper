import { describe, it, expect, vi, afterEach } from 'vitest';
import { attachCommandPaletteHotkey } from '$lib/hotkeys.js';

// Helper to mock platform detection.
// hotkeys.ts reads navigator.userAgentData.platform (Chrome 90+) with a
// navigator.userAgent fallback, so we mock via userAgent which jsdom exposes.
function mockMac() {
	vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
		'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
	);
	// Ensure userAgentData is absent so userAgent fallback is used
	Object.defineProperty(navigator, 'userAgentData', { value: undefined, configurable: true });
}

function mockWindows() {
	vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
	);
	Object.defineProperty(navigator, 'userAgentData', { value: undefined, configurable: true });
}

describe('attachCommandPaletteHotkey', () => {
	let cleanup: () => void;

	afterEach(() => {
		cleanup?.();
		vi.restoreAllMocks();
	});

	function fire(key: string, options: Partial<KeyboardEventInit> = {}) {
		const event = new KeyboardEvent('keydown', { key, bubbles: true, ...options });
		window.dispatchEvent(event);
		return event;
	}

	it('calls onOpen on ⌘K (metaKey) on Mac', () => {
		mockMac();

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k', { metaKey: true });

		expect(onOpen).toHaveBeenCalledOnce();
	});

	it('calls onOpen on Ctrl+K (non-Mac)', () => {
		mockWindows();

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
		mockMac();

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('j', { metaKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('removes listener after cleanup is called', () => {
		mockMac();

		const onOpen = vi.fn();
		const teardown = attachCommandPaletteHotkey(onOpen);
		teardown();

		fire('k', { metaKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('does NOT call onOpen on Mac when ctrlKey is used (not meta)', () => {
		mockMac();

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		fire('k', { ctrlKey: true });

		expect(onOpen).not.toHaveBeenCalled();
	});

	it('calls onOpen on ⌘K with Caps Lock on (key="K")', () => {
		mockMac();

		const onOpen = vi.fn();
		cleanup = attachCommandPaletteHotkey(onOpen);

		// Caps Lock causes e.key to be uppercase 'K'
		fire('K', { metaKey: true });

		expect(onOpen).toHaveBeenCalledOnce();
	});
});
