/**
 * Keyboard shortcut listener for the Command Palette.
 *
 * Key identity and modifier symbols are imported from `constants/keybindings.ts`.
 * To change the shortcut, update the config there — nothing else needs touching.
 *
 * Returns a cleanup function — call it in `onDestroy` / `$effect` teardown.
 */

import { COMMAND_PALETTE_HOTKEY } from '$lib/constants/keybindings.js';

/**
 * Attach the global Command Palette hotkey listener (⌘K on Mac, Ctrl+K elsewhere).
 *
 * @param onOpen  Called when the shortcut fires.
 * @returns       Teardown function that removes the listener.
 */
export function attachCommandPaletteHotkey(onOpen: () => void): () => void {
	function handleKeydown(e: KeyboardEvent): void {
		const isMac = navigator.platform.toUpperCase().startsWith('MAC');
		const modifier = isMac
			? COMMAND_PALETTE_HOTKEY.macModifier
			: COMMAND_PALETTE_HOTKEY.otherModifier;

		if (e[modifier] && e.key === COMMAND_PALETTE_HOTKEY.key) {
			e.preventDefault();
			onOpen();
		}
	}

	window.addEventListener('keydown', handleKeydown);
	return () => window.removeEventListener('keydown', handleKeydown);
}
