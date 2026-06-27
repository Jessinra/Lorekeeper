// ── Sessions tab ──
import { api } from "./api.js";
import { updateSortHeaders } from "./memories.js";
import { registerTab } from "./tab-registry.js";
import {
	clientSort,
	esc,
	fmtDatePlus8,
	fmtRelative,
	htmlSection,
} from "./utils.js";

// ── Self-register ──

registerTab("sessions", { load: () => loadSessions(false) });

// ── Event listeners ──

document.addEventListener("app:sessions:load", () => loadSessions(true));
document.addEventListener("app:sessions:toggle-stubs", () => toggleHideStubs());
document.addEventListener("app:sessions:filter-task", (e) => {
	const task = e.detail.task;
	// Find the matching chip button to pass to filterByTask (for UI state)
	const btn = document.querySelector(`.sess-chip[data-task="${task}"]`);
	filterByTask(btn, task);
});
document.addEventListener("app:sessions:filter-session-id", (e) => {
	filterBySessionId(e.detail.value);
});
document.addEventListener("app:sessions:toggle-date-sort", () =>
	toggleDateSort(),
);
document.addEventListener("app:sessions:clear-session-id", () => {
	const input = document.getElementById("sess-id-search");
	if (input) input.value = "";
	filterBySessionId("");
});
document.addEventListener("app:sessions:detail-toggle", (e) => {
	toggleSessDetail(e.detail.id);
});

let _sessions = [];
let _loaded = false;
let _hideStubs = true;
let _filterTask = "";
let _filterSessId = "";
let _sortDate = "desc"; // 'asc' | 'desc'

export async function loadSessions(force = false) {
	if (_loaded && !force) {
		renderSessions();
		return;
	}
	_sessions = await api("GET", "/api/sessions");
	_loaded = true;
	renderSessions();
}

function renderSessions() {
	const all = _sessions;
	const nonStubs = all.filter((s) => s.what_was_done);
	const sessIdLower = _filterSessId.toLowerCase();
	const visible = clientSort(
		(_hideStubs ? nonStubs : all).filter(
			(s) =>
				(!_filterTask || s.task_type === _filterTask) &&
				(!_filterSessId ||
					(s.session_id || "").toLowerCase().includes(sessIdLower)),
		),
		"reviewed_at",
		_sortDate,
	);

	const stubCount = all.length - nonStubs.length;

	// Table header count
	document.getElementById("sess-status").textContent = all.length
		? `${all.length} sessions processed`
		: "";

	// Filter label
	const lbl = document.getElementById("sess-filter-label");
	if (lbl) lbl.textContent = _filterTask ? `Filtered: ${_filterTask}` : "";

	// Hide-stubs button state
	const btn = document.getElementById("sess-hide-stubs-btn");
	if (btn) {
		btn.classList.toggle("active", _hideStubs);
		btn.title = _hideStubs
			? `Showing substantive only — ${stubCount} stub${stubCount !== 1 ? "s" : ""} hidden. Click to show all.`
			: `Showing all sessions (${stubCount} stub${stubCount !== 1 ? "s" : ""}). Click to hide stubs.`;
	}

	updateSortHeaders("th-sess-", { field: "date", dir: _sortDate }, ["date"]);

	renderTaskDist(nonStubs);

	document.getElementById("session-rows").innerHTML =
		visible.length === 0
			? `<tr><td colspan="5" class="run-empty">${
					_hideStubs && stubCount > 0
						? `All ${stubCount} sessions are stubs — <a href="#" data-action="sessions:toggle-stubs">show them</a> or invoke <code>/reflect</code> to process sessions`
						: _filterTask
							? `No ${_filterTask} sessions found`
							: "No sessions yet — invoke <code>/reflect</code> to create one"
				}</td></tr>`
			: visible.map((s, i) => renderRow(s, i)).join("");
}

// ── Task distribution bars ──
function renderTaskDist(sessions) {
	const counts = {};
	const order = ["build", "debug", "review", "design"];
	for (const s of sessions) {
		const t = s.task_type || "other";
		counts[t] = (counts[t] || 0) + 1;
	}
	const total = sessions.length || 1;
	const types = [
		...order.filter((t) => counts[t]),
		...Object.keys(counts).filter((t) => !order.includes(t)),
	];
	const el = document.getElementById("sess-task-dist");
	if (!el) return;
	el.innerHTML = types
		.map((t) => {
			const n = counts[t] || 0;
			const pct = Math.round((n / total) * 100);
			return `
      <div class="sess-dist-row sess-dist-${esc(t)}" data-task="${esc(t)}" title="Filter by ${esc(t)}">
        <div class="sess-dist-meta">
          <span class="sess-dist-name">${esc(t)}</span>
          <span class="sess-dist-count">${n}</span>
        </div>
        <div class="sess-dist-bar"><div class="sess-dist-bar-fill" style="width:${pct}%"></div></div>
      </div>`;
		})
		.join("");
	// No manual addEventListener needed — the delegation handler catches data-task clicks
}

// ── Row rendering ──
function renderRow(s, i) {
	const detId = `sess-det-${i}`;
	const isStub = !s.what_was_done;
	const shortId = s.session_id ? s.session_id.slice(0, 8) : "—";
	const taskBadge = s.task_type
		? `<span class="task-badge task-${esc(s.task_type)}">${esc(s.task_type)}</span>`
		: "";
	const summary = s.what_was_done
		? esc(s.what_was_done.replace(/\n/g, " ").slice(0, 130)) +
			(s.what_was_done.length > 130 ? "…" : "")
		: '<span class="sess-stub-label">stub</span>';

	const dateStr = s.reviewed_at
		? fmtDatePlus8(s.reviewed_at)
		: esc(s.session_date || "");
	const relStr = s.reviewed_at ? fmtRelative(s.reviewed_at) : "";

	return `
    <tr class="run-row-clickable${isStub ? " sess-row-stub" : ""}" data-sess-detail="${detId}">
      <td class="col-date-primary">
        ${dateStr}
        ${relStr ? `<div class="col-date-secondary">${relStr}</div>` : ""}
      </td>
      <td class="col-sess-id"><span class="sess-id-chip" title="${esc(s.session_id || "")}">${esc(shortId)}</span></td>
      <td class="sess-topic">${esc(s.topic || "—")}</td>
      <td>${taskBadge}</td>
      <td class="sess-summary-col">${summary}</td>
    </tr>
    <tr id="${detId}" class="run-detail-row hidden">
      <td colspan="5">
        <div class="run-detail-body sess-detail-body">${renderDetail(s)}</div>
      </td>
    </tr>
  `;
}

function renderDetail(s) {
	if (
		!s.what_was_done &&
		!s.decisions &&
		!s.lessons_learnt &&
		!s.good_patterns &&
		!s.user_profile &&
		!s.discoveries
	) {
		return '<div class="sess-stub-detail">Short session — no substantive content captured.</div>';
	}
	return [
		htmlSection("What was done", s.what_was_done),
		htmlSection("Decisions", s.decisions),
		htmlSection("Lessons Learnt", s.lessons_learnt),
		htmlSection("Good Patterns", s.good_patterns),
		htmlSection("User Profile", s.user_profile),
		htmlSection("Discoveries", s.discoveries),
	].join("");
}

export function toggleSessDetail(detId) {
	const el = document.getElementById(detId);
	if (el) el.classList.toggle("hidden");
}

export function toggleHideStubs() {
	_hideStubs = !_hideStubs;
	renderSessions();
}

export function filterByTask(btn, task) {
	_filterTask = task;
	document.querySelectorAll(".sess-chip").forEach((c) => {
		c.classList.remove("active");
	});
	if (btn) btn.classList.add("active");
	renderSessions();
}

export function filterBySessionId(val) {
	_filterSessId = val;
	renderSessions();
}

export function toggleDateSort() {
	_sortDate = _sortDate === "desc" ? "asc" : "desc";
	renderSessions();
}
