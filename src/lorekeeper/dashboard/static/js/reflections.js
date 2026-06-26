// ── Reflections tab ──
import { api } from "./api.js";
import { esc, fmtDate, parseJsonArray } from "./utils.js";
import "./runs.js";

let _reflections = [];
let _loaded = false;

export async function loadReflections(force = false) {
	if (_loaded && !force) {
		renderReflections();
		return;
	}
	_reflections = await api("GET", "/api/reflections");
	_loaded = true;
	renderReflections();
}

function renderReflections() {
	const refs = _reflections;
	const totalSessions = refs.reduce((s, r) => s + (r.session_count ?? 0), 0);

	document.getElementById("ref-met-total").textContent = refs.length || "—";
	document.getElementById("ref-met-sessions").textContent = totalSessions || "—";
	document.getElementById("ref-met-last").textContent = refs.length
		? fmtDate(refs[0].created_at)
		: "—";
	document.getElementById("ref-status").textContent = refs.length
		? `${refs.length} reflections`
		: "";

	document.getElementById("reflection-rows").innerHTML =
		refs.length === 0
			? '<tr><td colspan="4" class="run-empty">No reflections yet — invoke <code>/reflect</code> to create one</td></tr>'
			: refs.map((r, i) => renderRow(r, i)).join("");
}

function renderRow(r, i) {
	const memIds = parseJsonArray(r.memory_ids);
	const detId = `ref-detail-${i}`;
	const summary = r.summary
		? esc(r.summary.slice(0, 120)) + (r.summary.length > 120 ? "…" : "")
		: "—";

	return `
    <tr class="run-row-clickable" onclick="toggleReflectionDetail('${detId}', '${esc(r.id)}')">
      <td class="col-date-primary">${esc(fmtDate(r.created_at))}</td>
      <td class="col-num">${r.session_count ?? 0}</td>
      <td>${summary}</td>
      <td class="col-num">${memIds.length || "—"}</td>
    </tr>
    <tr id="${detId}" class="run-detail-row hidden">
      <td colspan="4">
        <div class="run-detail-body ref-detail-body" id="${detId}-content">
          <div class="ref-loading">Loading…</div>
        </div>
      </td>
    </tr>
  `;
}

window.toggleReflectionDetail = async (detId, reflectionId) => {
	const row = document.getElementById(detId);
	const content = document.getElementById(`${detId}-content`);
	if (!row) return;

	const isOpen = !row.classList.contains("hidden");
	if (isOpen) {
		row.classList.add("hidden");
		return;
	}

	row.classList.remove("hidden");
	if (content.querySelector(".ref-loading")) {
		try {
			const data = await api("GET", `/api/reflections/${reflectionId}`);
			content.innerHTML = renderDetail(data);
		} catch (e) {
			content.innerHTML = `<div class="run-mem-row">Error loading detail: ${esc(String(e))}</div>`;
		}
	}
};

function renderDetail(data) {
	const r = data.reflection;
	const sessions = data.sessions ?? [];
	const memIds = parseJsonArray(r.memory_ids);

	const section = (title, text) => {
		if (!text) return "";
		return `<div class="ref-section"><div class="ref-section-title">${title}</div><div class="ref-section-body">${esc(text)}</div></div>`;
	};

	const memLinks = memIds.length
		? `<div class="ref-section"><div class="ref-section-title">Memories Created</div><div class="ref-section-body">${memIds
				.map(
					(id) =>
						`<span class="ref-mem-link" onclick="window._refGoToMemory('${esc(id)}')">${esc(id.slice(0, 8))}…</span>`,
				)
				.join(" ")}</div></div>`
		: "";

	const sessionList = sessions.length
		? `<div class="ref-section"><div class="ref-section-title">Sessions Covered</div><div class="ref-section-body">${sessions
				.map((s) => {
					const parts = [s.session_date, s.topic, s.task_type].filter(Boolean);
					return `<div>${esc(parts.join(" · ") || s.session_id)}</div>`;
				})
				.join("")}</div></div>`
		: "";

	return `
    ${section("Summary", r.summary)}
    ${section("Lessons Learnt", r.lessons_learnt)}
    ${section("Good Patterns", r.good_patterns)}
    ${section("User Profile Updates", r.user_profile_updates)}
    ${section("Factual Discoveries", r.factual_discoveries)}
    ${sessionList}
    ${memLinks}
  `;
}

// Navigate to Detail tab for a given memory UUID (wired in app.js)
let _goToMemory = null;
export function registerRefGoToMemory(fn) {
	_goToMemory = fn;
}
window._refGoToMemory = (id) => {
	if (_goToMemory) _goToMemory(id);
};

window.loadReflections = loadReflections;
