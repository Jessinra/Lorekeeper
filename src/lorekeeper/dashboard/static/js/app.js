// ── Entry point ──
// Imports all modules (triggers self-registration via tab-registry),
// sets up keyboard shortcuts and auto-refresh, then bootstraps the app.

import "./tab-registry.js";
import "./api.js";
import "./utils.js";
import "./tab.js"; // delegation handler + dispatch()
import "./memories.js"; // self-registers
import "./detail.js";
import "./links.js";
import "./query.js";
import "./sessions.js";
import "./config.js";
import "./backup.js";
import "./metrics.js";
import "./runs.js";
import { initBackup } from "./backup.js";
import { loadLinks } from "./links.js";
import { loadMemories, updateSortHeaders } from "./memories.js";
import { runQuery } from "./query.js";
import * as state from "./state.js";
import { dispatch } from "./tab.js";

// ── Auto-refresh ──

const AUTO_REFRESH_MS = 30_000;
let _autoRefreshTimer = null;

async function triggerRefresh() {
	const btn = document.getElementById("btn-refresh-memories");
	const icon = btn?.querySelector(".refresh-icon");
	if (icon) icon.classList.add("spinning");
	btn?.setAttribute("disabled", "");
	try {
		dispatch("refresh");
		// Give async loads time to settle, then reschedule
		await new Promise((resolve) => setTimeout(resolve, 100));
	} finally {
		if (icon) icon.classList.remove("spinning");
		btn?.removeAttribute("disabled");
		scheduleAutoRefresh();
	}
}

// Hook up the Cmd+Enter listener for the query tab
function _attachRefreshListener() {
	document.addEventListener("keydown", (e) => {
		if (
			e.key === "r" &&
			(e.metaKey || e.ctrlKey) &&
			!["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)
		) {
			e.preventDefault();
			triggerRefresh();
		}
	});
}

function scheduleAutoRefresh() {
	clearTimeout(_autoRefreshTimer);
	_autoRefreshTimer = setTimeout(triggerRefresh, AUTO_REFRESH_MS);
}

// ── Init ──

function init() {
	// Keyboard shortcuts
	document.getElementById("q-text").addEventListener("keydown", (e) => {
		if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runQuery();
	});

	document.addEventListener("keydown", (e) => {
		if (e.key === "Escape") {
			dispatch("memories:clear-filter");
		}
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

	_attachRefreshListener();
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
