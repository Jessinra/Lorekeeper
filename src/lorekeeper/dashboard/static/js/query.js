// ── Query tab ──
import { api } from "./api.js";
import { esc, fmt2 } from "./utils.js";

// Cross-module callback — wired by app.js.
let _selectMemory = () => {};
export function registerQuerySelectMemory(fn) {
	_selectMemory = fn;
}

export async function runQuery() {
	const query = document.getElementById("q-text").value.trim();
	if (!query) return;
	const limit = parseInt(document.getElementById("q-limit").value, 10) || 10;
	const minScore = parseFloat(document.getElementById("q-min").value) || 0.1;
	const el = document.getElementById("query-results");
	el.innerHTML = '<div class="no-results">Searching…</div>';
	try {
		const results = await api("POST", "/api/search", {
			query,
			limit,
			min_score: minScore,
		});
		if (!results.length) {
			el.innerHTML = '<div class="no-results">No results.</div>';
			return;
		}
		el.innerHTML = results
			.map((r, i) => {
				const rel = r.relevance;
				const barW = Math.round(rel.combined_score * 100);
				return `
        <div class="result-card" onclick="selectMemory('${r.memory.id}')">
          <span class="result-rank">#${i + 1}</span>
          <div class="result-title">${esc(r.memory.title)}</div>
          <div class="score-bar-wrap"><div class="score-bar" style="width:${barW}%"></div></div>
          <div class="result-scores">
            <span class="score-pill ${rel.combined_score >= 0.5 ? "hi" : ""}">combined ${rel.combined_score.toFixed(3)}</span>
            <span class="score-pill">semantic ${rel.semantic_score.toFixed(3)}</span>
            <span class="score-pill">keyword ${rel.keyword_score.toFixed(3)}</span>
            <span class="score-pill">mem ${fmt2(r.memory.score)}</span>
            <span class="score-pill">uses ${r.memory.usage_count}</span>
            ${r.memory.soft_deleted ? '<span class="badge badge-deleted">deleted</span>' : ""}
          </div>
          <div class="result-preview">${esc(r.memory.content.slice(0, 300))}${r.memory.content.length > 300 ? "…" : ""}</div>
        </div>`;
			})
			.join("");
	} catch (e) {
		el.innerHTML = `<div class="no-results" style="color:var(--danger)">${esc(e.message)}</div>`;
	}
}

window.runQuery = runQuery;
