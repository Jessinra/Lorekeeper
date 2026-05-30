// ── Memories tab ──
import { api } from "./api.js";
import * as state from "./state.js";
import { registerTab } from "./tab-registry.js";
import {
	clientSort,
	esc,
	fmt2,
	fmtDate,
	isToday,
	scoreClass,
} from "./utils.js";

// ── Self-register ──

registerTab("memories", { load: loadMemories });

// ── Event listeners ──

document.addEventListener("app:memory:selected", () => renderList());

document.addEventListener("app:memories:changed", () => loadMemories());

document.addEventListener("app:refresh", () => loadMemories());

// ── UI action listeners (from delegation handler) ──

document.addEventListener("app:memories:clear-filter", () => clearFilter());

document.addEventListener("app:memories:toggle-deleted", () =>
	toggleShowDeleted(),
);

document.addEventListener("app:memories:time-filter", (e) => {
	const daysStr = e.detail.days;
	setTimeFilterByValue(daysStr === "" ? null : Number(daysStr));
});

document.addEventListener("app:memories:namespace-filter", (e) => {
	setNamespaceFilter(e.detail.value);
});

document.addEventListener("app:memories:filter-input", (e) => {
	onFilterInputValue(e.detail.value);
});

document.addEventListener("app:sort:set", (e) => {
	if (e.detail.target === "mem") setMemSort(e.detail.field);
});

// ── Core ──

export function toggleShowDeleted() {
	state.setShowDeleted(!state.showDeleted);
	const btn = document.getElementById("btn-show-deleted");
	btn.textContent = state.showDeleted ? "Hide deleted" : "Show deleted";
	btn.classList.toggle("btn-primary", state.showDeleted);
	btn.classList.toggle("btn-secondary", !state.showDeleted);
	loadMemories();
}

export async function loadMemories() {
	state.setAllMemories(
		await api("GET", `/api/memories?include_deleted=${state.showDeleted}`),
	);
	_populateNamespaceFilter();
	updateStats();
	renderList();
	updateHeaderMeta();
}

export function _populateNamespaceFilter() {
	const sel = document.getElementById("ns-filter");
	const current = sel.value;
	const namespaces = [
		...new Set(state.allMemories.map((m) => m.namespace ?? "shared")),
	].sort();
	sel.innerHTML =
		`<option value="">All namespaces</option>` +
		namespaces
			.map(
				(ns) =>
					`<option value="${esc(ns)}"${ns === current ? " selected" : ""}>${esc(ns)}</option>`,
			)
			.join("");
	// Reconcile state — if the previously-selected namespace no longer exists, reset
	if (current && !namespaces.includes(current)) {
		state.setNamespaceFilter("");
		sel.value = "";
	}
}

export function setNamespaceFilter(ns) {
	state.setNamespaceFilter(ns);
	renderList();
}

export function updateStats() {
	const active = state.allMemories.filter((m) => !m.soft_deleted);
	const avgScore = active.length
		? active.reduce((s, m) => s + m.score, 0) / active.length
		: null;
	const totalUses = active.reduce((s, m) => s + m.usage_count, 0);
	const lastUpdated = active.length
		? fmtDate(
				active.reduce((a, b) => (a.updated_at > b.updated_at ? a : b))
					.updated_at,
			)
		: "—";

	document.getElementById("met-total").textContent = active.length;
	const avgEl = document.getElementById("met-avg");
	avgEl.textContent = avgScore != null ? avgScore.toFixed(1) : "—";
	avgEl.className =
		"metric-value " +
		(avgScore == null
			? ""
			: avgScore >= 6
				? "stat-high"
				: avgScore >= 3
					? "stat-mid"
					: "stat-low");
	document.getElementById("met-uses").textContent = totalUses;
	document.getElementById("met-updated").textContent = lastUpdated;
}

export function updateHeaderMeta() {
	document.getElementById("header-meta").textContent =
		`${state.allMemories.length} memories · ${state.linksLoaded ? state.allLinks.length : "?"} links`;
}

let _filterTimer = null;
export function onFilterInputValue(val) {
	state.setFilterText(val);
	document.getElementById("mem-filter-clear").classList.toggle("hidden", !val);
	clearTimeout(_filterTimer);
	_filterTimer = setTimeout(renderList, 150);
}

export function clearFilter() {
	state.setFilterText("");
	document.getElementById("mem-filter").value = "";
	document.getElementById("mem-filter-clear").classList.add("hidden");
	renderList();
}

export function setTimeFilterByValue(days) {
	state.setTimeFilterDays(days);
	// Update active button state via data-time-filter attributes
	document.querySelectorAll("[data-time-filter]").forEach((b) => {
		const btnDays = b.dataset.timeFilter;
		const match = days === null ? btnDays === "" : Number(btnDays) === days;
		b.classList.toggle("active", match);
	});
	renderList();
}

// Set time filter from button click (kept for compatibility)
export function setTimeFilter(_btn, days) {
	setTimeFilterByValue(days);
}

export function setMemSort(field) {
	state.memSort.dir =
		state.memSort.field === field
			? state.memSort.dir === "desc"
				? "asc"
				: "desc"
			: "desc";
	state.memSort.field = field;
	updateSortHeaders("th-", state.memSort, [
		"title",
		"namespace",
		"score",
		"confidence",
		"usage_count",
		"link_count",
		"updated_at",
	]);
	renderList();
}

export function updateSortHeaders(prefix, sort, fields) {
	fields.forEach((f) => {
		const th = document.getElementById(prefix + f);
		if (!th) return;
		const arrow = th.querySelector(".sort-arrow");
		th.classList.toggle("sort-active", sort.field === f);
		arrow.textContent =
			sort.field === f ? (sort.dir === "desc" ? " ↓" : " ↑") : "";
	});
}

export function renderList() {
	const ft = state.filterText.toLowerCase();
	let filtered = ft
		? state.allMemories.filter(
				(m) =>
					m.title.toLowerCase().includes(ft) ||
					(m.description || "").toLowerCase().includes(ft) ||
					(m.content || "").toLowerCase().includes(ft),
			)
		: state.allMemories;

	if (state.namespaceFilter) {
		filtered = filtered.filter(
			(m) => (m.namespace ?? "shared") === state.namespaceFilter,
		);
	}

	if (state.timeFilterDays !== null) {
		const cutoff = new Date();
		cutoff.setDate(cutoff.getDate() - state.timeFilterDays);
		cutoff.setHours(0, 0, 0, 0);
		filtered = filtered.filter(
			(m) => m.created_at && new Date(m.created_at) >= cutoff,
		);
	}

	const countLabel =
		ft || state.timeFilterDays !== null || state.namespaceFilter
			? `${filtered.length} / ${state.allMemories.length}`
			: `${state.allMemories.length}`;
	document.getElementById("memory-count").textContent = countLabel;

	const sorted = clientSort(filtered, state.memSort.field, state.memSort.dir);
	document.getElementById("memory-rows").innerHTML = sorted
		.map((m) => {
			const cls = [
				state.selectedId === m.id ? "selected" : "",
				m.soft_deleted ? "deleted-row" : "",
			]
				.filter(Boolean)
				.join(" ");
			const conf = m.confidence != null ? fmt2(m.confidence) : "—";
			const newDot = isToday(m.created_at)
				? '<span class="new-dot" title="Created today"></span>'
				: "";
			const sub = m.description
				? `<div class="col-title-sub">${esc(m.description)}</div>`
				: "";
			return `<tr class="${cls}" data-memory-id="${m.id}">
      <td class="col-status">${m.soft_deleted ? '<span class="badge badge-deleted">del</span>' : ""}</td>
      <td class="col-title"><div class="col-title-main" title="${esc(m.title)}">${newDot}${esc(m.title)}</div>${sub}</td>
      <td class="col-ns"><span class="ns-badge">${esc(m.namespace ?? "shared")}</span></td>
      <td class="col-score"><span class="score-badge ${scoreClass(m.score)}">${fmt2(m.score)}</span></td>
      <td class="col-conf">${conf}</td>
      <td class="col-usage">${m.usage_count}</td>
      <td class="col-links">${m.link_count ?? 0}</td>
      <td class="col-date"><div class="col-date-primary">${fmtDate(m.updated_at)}</div><div class="col-date-secondary">${fmtDate(m.created_at)}</div></td>
    </tr>`;
		})
		.join("");
}
