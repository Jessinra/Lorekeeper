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
	/** Symbol displayed in Mac kbd hints (e.g. ⌘) */
	macModifierDisplay: string;
	/** Text displayed in Win/Linux kbd hints (e.g. Ctrl) */
	otherModifierDisplay: string;
	/**
	 * WAI-ARIA aria-keyshortcuts value for Mac.
	 * Uses KeyboardEvent.key names (Meta, Control, etc.), lowercase key.
	 * https://www.w3.org/TR/wai-aria-1.2/#aria-keyshortcuts
	 */
	macAriaKeyshortcuts: string;
	/** WAI-ARIA aria-keyshortcuts value for Win/Linux. */
	otherAriaKeyshortcuts: string;
}

/** ⌘K / Ctrl+K — opens the Command Palette. */
export const COMMAND_PALETTE_HOTKEY: HotkeyConfig = {
	key: 'k',
	keyDisplay: 'K',
	macModifier: 'metaKey',
	otherModifier: 'ctrlKey',
	macModifierDisplay: '⌘',
	otherModifierDisplay: 'Ctrl',
	macAriaKeyshortcuts: 'Meta+k',
	otherAriaKeyshortcuts: 'Control+k',
} as const;
