// ── Entry point ──
// Imports all modules, wires cross-module callbacks, then initialises the app.

import "./api.js";
import "./utils.js";
import { initBackup } from "./backup.js";
import { loadConfig } from "./config.js";
import { registerDetailCallbacks, selectMemory } from "./detail.js";
import { loadLinks, registerLinksSelectMemory } from "./links.js";
import {
	clearFilter,
	loadMemories,
	registerSelectMemory,
	renderList,
	updateSortHeaders,
} from "./memories.js";
import { loadMetrics } from "./metrics.js";
import { registerQuerySelectMemory, runQuery } from "./query.js";
import { loadSessions } from "./sessions.js";
import * as state from "./state.js";
import { registerTabCallbacks } from "./tab.js";

// ── Wire cross-module callbacks to break circular deps ──

registerTabCallbacks({
	onTabLinks: loadLinks,
	onTabConfig: loadConfig,
	onTabSessions: loadSessions,
	onTabMetrics: loadMetrics,
});

// detail.js needs loadMemories, renderList, loadLinks
registerDetailCallbacks({
	loadMemories,
	renderList,
	loadLinks,
});

// links.js needs selectMemory
registerLinksSelectMemory(selectMemory);

// query.js needs selectMemory
registerQuerySelectMemory(selectMemory);

// memories.js renderList calls selectMemory via window.selectMemory (already set
// in detail.js window assignments), but we also register it for any internal use.
registerSelectMemory(selectMemory);

// ── Auto-refresh ──

const AUTO_REFRESH_MS = 30_000;
let _autoRefreshTimer = null;

function activeTabRefresher() {
	const active = document.querySelector(".tab.active");
	if (!active) return loadMemories;
	const tab = active.dataset.tab || active.textContent.trim().toLowerCase();
	if (tab === "sessions") return () => loadSessions(false);
	return loadMemories;
}

async function triggerRefresh() {
	const btn = document.getElementById("btn-refresh-memories");
	const icon = btn?.querySelector(".refresh-icon");
	if (icon) icon.classList.add("spinning");
	btn?.setAttribute("disabled", "");
	try {
		await activeTabRefresher()();
	} finally {
		if (icon) icon.classList.remove("spinning");
		btn?.removeAttribute("disabled");
		scheduleAutoRefresh();
	}
}

function scheduleAutoRefresh() {
	clearTimeout(_autoRefreshTimer);
	_autoRefreshTimer = setTimeout(triggerRefresh, AUTO_REFRESH_MS);
}

window.triggerRefresh = triggerRefresh;
window.loadMetricsFromGlobal = () => loadMetrics();

// ── Init ──

function init() {
	// Keyboard shortcuts
	document.getElementById("q-text").addEventListener("keydown", (e) => {
		if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runQuery();
	});

	document.addEventListener("keydown", (e) => {
		if (e.key === "Escape") clearFilter();
		if (
			e.key === "/" &&
			!["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)
		) {
			const tab = document.getElementById("tab-memories");
			if (tab.classList.contains("active")) {
				e.preventDefault();
				document.getElementById("mem-filter").focus();
			}
		}
	});

	initBackup();

	// Bootstrap the memories tab sort headers and load data
	updateSortHeaders("th-", state.memSort, [
		"title",
		"score",
		"confidence",
		"usage_count",
		"link_count",
		"updated_at",
	]);

	// Inject local timezone label into DATE column header
	const tzOffset = -new Date().getTimezoneOffset() / 60;
	const tzLabel = `GMT${tzOffset >= 0 ? "+" : ""}${tzOffset}`;
	const dateHeader = document.getElementById("th-updated_at");
	if (dateHeader)
		dateHeader.innerHTML = `Date <span class="tz-label">${tzLabel}</span> <span class="sort-arrow">↓</span>`;

	// Load memories + links eagerly so header-meta shows correct link count immediately
	Promise.all([loadMemories(), loadLinks()]).then(scheduleAutoRefresh);
}

init();
