// ── Memories tab ──
import { api } from "./api.js";
import * as state from "./state.js";
import {
	clientSort,
	esc,
	fmt2,
	fmtDate,
	isToday,
	scoreClass,
} from "./utils.js";

// Cross-module callback — wired by app.js to avoid circular imports.
// memories.js needs to call selectMemory (lives in detail.js).
let _selectMemory = () => {};
export function registerSelectMemory(fn) {
	_selectMemory = fn;
}

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
	updateStats();
	renderList();
	updateHeaderMeta();
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
export function onFilterInput() {
	state.setFilterText(document.getElementById("mem-filter").value);
	document
		.getElementById("mem-filter-clear")
		.classList.toggle("hidden", !state.filterText);
	clearTimeout(_filterTimer);
	_filterTimer = setTimeout(renderList, 150);
}

export function clearFilter() {
	state.setFilterText("");
	document.getElementById("mem-filter").value = "";
	document.getElementById("mem-filter-clear").classList.add("hidden");
	renderList();
}

export function setTimeFilter(btn, days) {
	// days: '' = all, 0 = today, 3 = 3d, 7 = 1w
	state.setTimeFilterDays(days === "" ? null : Number(days));
	document
		.querySelectorAll(".time-filter-btn")
		.forEach((b) => b.classList.remove("active"));
	btn.classList.add("active");
	renderList();
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

	if (state.timeFilterDays !== null) {
		const cutoff = new Date();
		cutoff.setDate(cutoff.getDate() - state.timeFilterDays);
		cutoff.setHours(0, 0, 0, 0);
		filtered = filtered.filter(
			(m) => m.created_at && new Date(m.created_at) >= cutoff,
		);
	}

	const countLabel =
		ft || state.timeFilterDays !== null
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
			return `<tr class="${cls}" onclick="selectMemory('${m.id}')">
      <td class="col-status">${m.soft_deleted ? '<span class="badge badge-deleted">del</span>' : ""}</td>
      <td class="col-title"><div class="col-title-main" title="${esc(m.title)}">${newDot}${esc(m.title)}</div>${sub}</td>
      <td class="col-score"><span class="score-badge ${scoreClass(m.score)}">${fmt2(m.score)}</span></td>
      <td class="col-conf">${conf}</td>
      <td class="col-usage">${m.usage_count}</td>
      <td class="col-links">${m.link_count ?? 0}</td>
      <td class="col-date"><div class="col-date-primary">${fmtDate(m.updated_at)}</div><div class="col-date-secondary">${fmtDate(m.created_at)}</div></td>
    </tr>`;
		})
		.join("");
}

// Expose onclick targets on window
window.toggleShowDeleted = toggleShowDeleted;
window.loadMemories = loadMemories;
window.onFilterInput = onFilterInput;
window.clearFilter = clearFilter;
window.setMemSort = setMemSort;
window.setTimeFilter = setTimeFilter;
