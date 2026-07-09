/**
 * Keyboard shortcut listener for the Command Palette.
 *
 * Registers a global `keydown` handler that opens the palette on:
 *  - macOS: ⌘K
 *  - Windows/Linux: Ctrl+K
 *
 * Returns a cleanup function — call it in `onDestroy` / `$effect` teardown.
 */

/**
 * Attach the ⌘K / Ctrl+K listener.
 *
 * @param onOpen  Called when the shortcut fires. Receives the triggering event.
 * @returns       Teardown function that removes the listener.
 */
export function attachCommandPaletteHotkey(onOpen: () => void): () => void {
	function handleKeydown(e: KeyboardEvent): void {
		const isMac = navigator.platform.toUpperCase().startsWith('MAC');
		const modifierHeld = isMac ? e.metaKey : e.ctrlKey;

		if (modifierHeld && e.key === 'k') {
			e.preventDefault();
			onOpen();
		}
	}

	window.addEventListener('keydown', handleKeydown);
	return () => window.removeEventListener('keydown', handleKeydown);
}
