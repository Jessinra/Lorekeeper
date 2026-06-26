import { getTab } from "./tab-registry.js";

// ── Unified event dispatcher ──

/**
 * Dispatch a namespaced CustomEvent on the document.
 * All cross-module communication flows through this single function.
 *
 * For user actions triggered by DOM interactions: dispatch from the
 * delegation handler below. Each module listens for its own events.
 *
 * For state-change notifications (e.g. "memories:changed" after a
 * save): modules call dispatch() directly.
 */
export function dispatch(name, detail = {}) {
	document.dispatchEvent(new CustomEvent(`app:${name}`, { detail, bubbles: true }));
}

// ── Tab switching via registry ──

export function switchTab(name) {
	document.querySelectorAll(".tab-pane").forEach((p) => {
		p.classList.remove("active");
	});

	document.querySelectorAll(".tab").forEach((t) => {
		t.classList.toggle("active", t.dataset.tab === name);
	});

	const pane = document.getElementById(`tab-${name}`);
	if (pane) pane.classList.add("active");

	// Lazy load via registry — each tab's load() handles its own gate
	const tab = getTab(name);
	if (tab?.load) tab.load();
}

// ── Event delegation — catches all data-* attribute clicks ──

document.addEventListener("click", (e) => {
	// Tab buttons
	const tabBtn = e.target.closest("[data-tab]");
	if (tabBtn) {
		e.preventDefault();
		switchTab(tabBtn.dataset.tab);
		return;
	}

	// Generic actions — dispatches the action name as event
	const actionEl = e.target.closest("[data-action]");
	if (actionEl) {
		e.preventDefault();
		const detail = { ...actionEl.dataset };
		delete detail.action; // don't duplicate the event name in detail
		dispatch(actionEl.dataset.action, detail);
		return;
	}

	// Memory row clicks → select memory
	const memRow = e.target.closest("[data-memory-id]");
	if (memRow) {
		e.preventDefault();
		dispatch("memory:select", { id: memRow.dataset.memoryId });
		return;
	}

	// Sort header clicks
	const sortBtn = e.target.closest("[data-sort]");
	if (sortBtn) {
		e.preventDefault();
		dispatch("sort:set", {
			field: sortBtn.dataset.sort,
			target: sortBtn.dataset.sortTarget || "mem",
		});
		return;
	}

	// Time filter buttons
	const timeBtn = e.target.closest("[data-time-filter]");
	if (timeBtn) {
		e.preventDefault();
		dispatch("memories:time-filter", { days: timeBtn.dataset.timeFilter });
		return;
	}

	// Session detail toggle
	const sessDetail = e.target.closest("[data-sess-detail]");
	if (sessDetail) {
		e.preventDefault();
		dispatch("sessions:detail-toggle", { id: sessDetail.dataset.sessDetail });
		return;
	}

	// Run detail toggle
	const runDetail = e.target.closest("[data-run-detail]");
	if (runDetail) {
		e.preventDefault();
		dispatch("runs:detail-toggle", { id: runDetail.dataset.runDetail });
		return;
	}

	// Link delete from links tab
	const linkDel = e.target.closest("[data-link-delete]");
	if (linkDel) {
		e.preventDefault();
		dispatch("links:delete", { id: linkDel.dataset.linkDelete });
		return;
	}

	// Session dist-row filter click (data-task)
	const distRow = e.target.closest("[data-task]");
	if (distRow) {
		e.preventDefault();
		dispatch("sessions:filter-task", { task: distRow.dataset.task });
		return;
	}
});

// ── Change / input delegation ──

document.addEventListener("change", (e) => {
	const el = e.target.closest("[data-change]");
	if (el) {
		const detail = { ...el.dataset, value: el.value };
		delete detail.change;
		if (el.type === "checkbox") {
			detail.checked = String(el.checked);
		}
		dispatch(el.dataset.change, detail);
	}
});

document.addEventListener("input", (e) => {
	const el = e.target.closest("[data-input]");
	if (el) {
		dispatch(el.dataset.input, { value: el.value });
	}
});
