// ── Tab registry ──
// Tab modules self-register on import. tab.js reads the registry for
// tab order and lazy loading instead of hardcoded TAB_ORDER.

const TABS = [];

export function registerTab(name, { load, init }) {
	TABS.push({ name, load, init });
}

export function getTabs() {
	return TABS;
}

export function getTab(name) {
	return TABS.find((t) => t.name === name);
}
