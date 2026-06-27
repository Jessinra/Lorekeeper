// ── Runs tab ──
import { api } from "./api.js";
import { registerTab } from "./tab-registry.js";
import { esc, fmtDate } from "./utils.js";

// ── Self-register ──

registerTab("runs", { load: () => loadRuns(false) });

// ── Event listeners ──

document.addEventListener("app:runs:load", () => loadRuns(true));
document.addEventListener("app:runs:detail-toggle", (e) => {
	toggleRunDetail(e.detail.id);
});

let _runs = [];
let _loaded = false;

export async function loadRuns(force = false) {
	if (_loaded && !force) {
		renderRuns();
		return;
	}
	_runs = await api("GET", "/api/runs?limit=50");
	_loaded = true;
	renderRuns();
}

function renderRuns() {
	const runs = _runs;

	const totalInserted = runs.reduce(
		(s, r) => s + (r.lore_inserted?.length ?? 0),
		0,
	);
	const totalUpdated = runs.reduce(
		(s, r) => s + (r.lore_updated?.length ?? 0),
		0,
	);
	document.getElementById("run-met-total").textContent = runs.length || "—";
	document.getElementById("run-met-inserted").textContent =
		totalInserted || "—";
	document.getElementById("run-met-updated").textContent = totalUpdated || "—";
	document.getElementById("run-met-last").textContent = runs.length
		? fmtDate(runs[0].completed_at)
		: "—";
	document.getElementById("runs-status").textContent = runs.length
		? `${runs.length} runs recorded`
		: "";

	document.getElementById("run-rows").innerHTML =
		runs.length === 0
			? '<tr><td colspan="7" class="run-empty">No runs yet — invoke <code>/recap-sessions</code> in Claude Code to start</td></tr>'
			: runs.map((r, i) => renderRow(r, i)).join("");
}

function renderRow(r, i) {
	const ins = r.lore_inserted?.length ?? 0;
	const upd = r.lore_updated?.length ?? 0;
	const del = r.lore_soft_deleted?.length ?? 0;
	const logs = r.new_logs?.length ?? 0;
	const stubs = r.stubs ?? 0;
	const skip = r.skipped ?? "—";
	const topics = (r.new_logs ?? []).join(", ") || "—";
	const detId = `run-detail-${i}`;
	const hasDetail = ins || upd || del;

	const insList = (r.lore_inserted ?? [])
		.map((m) => `<div class="run-mem-row run-mem-ins">+ ${esc(m.title)}</div>`)
		.join("");
	const updList = (r.lore_updated ?? [])
		.map((m) => `<div class="run-mem-row run-mem-upd">~ ${esc(m.title)}</div>`)
		.join("");
	const delList = (r.lore_soft_deleted ?? [])
		.map((m) => `<div class="run-mem-row run-mem-del">× ${esc(m.title)}</div>`)
		.join("");

	return `
    <tr class="${hasDetail ? "run-row-clickable" : ""}" ${hasDetail ? `data-run-detail="${detId}"` : ""}>
      <td>
        <div class="col-date-primary">${esc(fmtDate(r.completed_at))}</div>
        <div class="col-date-secondary">${esc(r.trigger ?? "manual")}</div>
      </td>
      <td class="col-num">${logs}${stubs ? `<span class="run-hint"> +${stubs} stubs</span>` : ""}</td>
      <td class="col-num">${skip}</td>
      <td class="col-num">${ins ? `<span class="run-stat-good">${ins}</span>` : "0"}</td>
      <td class="col-num">${upd ? `<span class="run-stat-info">${upd}</span>` : "0"}</td>
      <td class="col-num">${del ? `<span class="run-stat-warn">${del}</span>` : "0"}</td>
      <td class="col-topics" title="${esc(topics)}">${esc(topics)}</td>
    </tr>
    ${
			hasDetail
				? `<tr id="${detId}" class="run-detail-row hidden">
      <td colspan="7"><div class="run-detail-body">${insList}${updList}${delList}</div></td>
    </tr>`
				: ""
		}
  `;
}

export function toggleRunDetail(id) {
	const el = document.getElementById(id);
	if (el) el.classList.toggle("hidden");
}
