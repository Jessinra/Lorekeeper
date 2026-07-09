/**
 * Keyboard shortcut configuration.
 *
 * Single source of truth — hotkeys.ts, TopBar.svelte, and any future
 * keybinding hints all import from here so they stay in sync automatically.
 *
 * Adding a new shortcut: add an entry here, wire the listener in hotkeys.ts,
 * and display the hint wherever the UI calls for it.
 */

export interface HotkeyConfig {
	/** Logical key value (matches KeyboardEvent.key, lowercase) */
	key: string;
	/** Uppercase display form shown in kbd hints */
	keyDisplay: string;
	/** Modifier property on macOS */
	macModifier: 'metaKey' | 'ctrlKey';
	/** Modifier property on Windows / Linux */
	otherModifier: 'metaKey' | 'ctrlKey';
	/** Symbol displayed in Mac kbd hints */
	macModifierDisplay: string;
	/** Text displayed in Win/Linux kbd hints */
	otherModifierDisplay: string;
}

/** ⌘K / Ctrl+K — opens the Command Palette. */
export const COMMAND_PALETTE_HOTKEY: HotkeyConfig = {
	key: 'k',
	keyDisplay: 'K',
	macModifier: 'metaKey',
	otherModifier: 'ctrlKey',
	macModifierDisplay: '⌘',
	otherModifierDisplay: 'Ctrl',
} as const;
