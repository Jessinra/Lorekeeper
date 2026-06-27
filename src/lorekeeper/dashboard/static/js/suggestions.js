// ── Suggestions tab — accept/reject UI, batch ops, pagination ──
import { api, showToast } from "./api.js";
import { dispatch } from "./tab.js";
import { registerTab } from "./tab-registry.js";
import { esc } from "./utils.js";

// ── Self-register ──

registerTab("suggestions", { load: loadSuggestions });

// ── Module state ──

let _offset = 0;
let _total = 0;
const PAGE_SIZE = 50;
let _memoryFilter = null; // set when navigated from detail badge
let _sortBy = "weighted_score";
let _sortDir = "desc";

// ── Event listeners ──

document.addEventListener("app:suggestions:load", () => loadSuggestions());
document.addEventListener("app:suggestions:refresh", () => loadSuggestions());

document.addEventListener("app:suggestions:navigate", (e) => {
	// Only update filter state here — switchTab() in detail.js fires
	// loadSuggestions() via the tab registry, so no duplicate fetch.
	_memoryFilter = e.detail.memoryId || null;
	_offset = 0;
});

document.addEventListener("app:suggestions:prev-page", () => {
	if (_offset > 0) {
		_offset = Math.max(0, _offset - PAGE_SIZE);
		loadSuggestions();
	}
});

document.addEventListener("app:suggestions:next-page", () => {
	if (_offset + PAGE_SIZE < _total) {
		_offset += PAGE_SIZE;
		loadSuggestions();
	}
});

document.addEventListener("app:suggestions:sort", (e) => {
	const val = e.detail.value || "score-desc";
	if (val === "score-desc") {
		_sortBy = "weighted_score";
		_sortDir = "desc";
	} else if (val === "score-asc") {
		_sortBy = "weighted_score";
		_sortDir = "asc";
	} else if (val === "newest") {
		_sortBy = "created_at";
		_sortDir = "desc";
	}
	_offset = 0;
	loadSuggestions();
});

document.addEventListener("app:suggestions:select-all", (e) => {
	const checked = e.detail?.checked === true || e.detail?.checked === "true";
	document.querySelectorAll(".sug-cb").forEach((cb) => {
		cb.checked = checked;
	});
	_updateBatchButtons();
});

document.addEventListener("app:suggestions:accept-selected", () => {
	_batchAction("accept");
});

document.addEventListener("app:suggestions:reject-selected", () => {
	_batchAction("reject");
});

// ── Core ──

export async function loadSuggestions() {
	const container = document.getElementById("suggestions-container");
	const empty = document.getElementById("suggestions-empty");
	if (!container) return;

	let url = `/api/suggestions?limit=${PAGE_SIZE}&offset=${_offset}&sort_by=${_sortBy}&sort_dir=${_sortDir}`;
	if (_memoryFilter) url += `&memory_id=${encodeURIComponent(_memoryFilter)}`;

	try {
		const data = await api("GET", url);
		_total = data.total;
		_renderList(data.items);
		_renderPagination();
		_renderCount();
	} catch (e) {
		if (empty) {
			empty.style.display = "flex";
			empty.innerHTML = `
        <div class="sug-empty-icon">⚠</div>
        Failed to load suggestions
        <div class="sug-empty-sub">${esc(e.message)}</div>
        <button class="btn btn-ghost btn-sm" data-action="suggestions:load" style="margin-top:12px">↺ Retry</button>`;
		}
	}
}

function _renderList(items) {
	const tbody = document.getElementById("suggestions-rows");
	const empty = document.getElementById("suggestions-empty");
	const pag = document.getElementById("suggestions-pagination");
	if (!tbody) return;

	if (items.length === 0) {
		tbody.innerHTML = "";
		if (empty) empty.style.display = "flex";
		if (pag) pag.style.display = "none";
		return;
	}

	// Hide empty state, show pagination
	if (empty) empty.style.display = "none";
	if (pag) pag.style.display = "flex";

	// Build rows
	// Determine filter label for title click navigation
	tbody.innerHTML = items
		.map(
			(s) => `
    <tr data-id="${esc(s.id)}">
      <td class="col-cb"><input type="checkbox" class="sug-cb"></td>
      <td><span class="mem-name" data-memory-id="${esc(s.source_memory_id)}">${esc(s.source_title)}</span></td>
      <td class="col-arrow">→</td>
      <td><span class="mem-name" data-memory-id="${esc(s.target_memory_id)}">${esc(s.target_title)}</span></td>
      <td class="col-score">
        <span class="score-dot" style="background:${_scoreColor(s.weighted_score)}"></span>
        <span class="score-val" style="color:${_scoreColor(s.weighted_score)}">${s.weighted_score.toFixed(2)}</span>
      </td>
      <td class="col-actions">
        <div class="row-actions">
          <button type="button" class="btn-accept" aria-label="Accept suggestion" data-sug-id="${esc(s.id)}">✓</button>
          <button type="button" class="btn-reject" aria-label="Reject suggestion" data-sug-id="${esc(s.id)}">✗</button>
        </div>
      </td>
    </tr>`,
		)
		.join("");

	// Wire per-row accept/reject
	tbody.querySelectorAll(".btn-accept").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			e.stopPropagation();
			_singleAction(btn.dataset.sugId, "accept", btn.closest("tr"));
		});
	});
	tbody.querySelectorAll(".btn-reject").forEach((btn) => {
		btn.addEventListener("click", (e) => {
			e.stopPropagation();
			_singleAction(btn.dataset.sugId, "reject", btn.closest("tr"));
		});
	});

	// Wire memory title clicks → detail navigation
	tbody.querySelectorAll(".mem-name").forEach((el) => {
		el.addEventListener("click", () => {
			dispatch("memory:select", { id: el.dataset.memoryId });
		});
	});

	// Wire checkbox changes
	tbody.querySelectorAll(".sug-cb").forEach((cb) => {
		cb.addEventListener("change", _updateBatchButtons);
	});

	// Reset select-all state
	const selectAll = document.getElementById("suggestions-select-all");
	if (selectAll) {
		selectAll.checked = false;
		selectAll.indeterminate = false;
	}
	_updateBatchButtons();
}

function _renderPagination() {
	const pageInfo = document.getElementById("suggestions-page-info");
	const prevBtn = document.getElementById("suggestions-prev");
	const nextBtn = document.getElementById("suggestions-next");
	if (!pageInfo) return;

	const from = _offset + 1;
	const to = Math.min(_offset + PAGE_SIZE, _total);
	pageInfo.textContent = `${from}–${to} of ${_total}`;
	if (prevBtn) prevBtn.disabled = _offset === 0;
	if (nextBtn) nextBtn.disabled = _offset + PAGE_SIZE >= _total;
}

function _renderCount() {
	const el = document.getElementById("suggestions-count");
	if (el) el.textContent = `${_total} pending`;
}

function _updateBatchButtons() {
	const checked = document.querySelectorAll(".sug-cb:checked").length;
	const acceptBtn = document.getElementById("suggestions-accept-selected");
	const rejectBtn = document.getElementById("suggestions-reject-selected");
	if (acceptBtn) acceptBtn.disabled = checked === 0;
	if (rejectBtn) rejectBtn.disabled = checked === 0;
}

async function _singleAction(sugId, action, row) {
	row.classList.add("fade-out");
	try {
		const result = await api("POST", "/api/suggestions/batch", {
			suggestion_ids: [sugId],
			action,
		});
		const item = result.results?.[0];
		if (item?.status === "accepted" || item?.status === "rejected") {
			showToast(
				action === "accept"
					? "Suggestion accepted — link created"
					: "Suggestion rejected",
			);
			row.remove();
			_total = Math.max(0, _total - 1);
			_renderCount();
			_renderPagination();
		} else {
			showToast(item?.message || "Operation failed", "error");
			row.classList.remove("fade-out");
		}
	} catch (e) {
		showToast(e.message, "error");
		row.classList.remove("fade-out");
	}
}

async function _batchAction(action) {
	const checked = document.querySelectorAll(".sug-cb:checked");
	if (checked.length === 0) return;
	const rows = [...checked].map((cb) => ({
		row: cb.closest("tr"),
		id: cb.closest("tr").dataset.id,
	}));

	// Fade out selected rows
	rows.forEach(({ row }) => {
		row.classList.add("fade-out");
	});

	try {
		const result = await api("POST", "/api/suggestions/batch", {
			suggestion_ids: rows.map((r) => r.id),
			action,
		});
		const successCount =
			action === "accept" ? result.accepted : result.rejected;
		// Only remove rows that actually succeeded
		const okayIds = new Set(
			(result.results || [])
				.filter((r) => r.status === "accepted" || r.status === "rejected")
				.map((r) => r.id),
		);
		rows.forEach(({ row, id }) => {
			if (okayIds.has(id)) {
				row.remove();
			} else {
				row.classList.remove("fade-out");
			}
		});
		showToast(
			action === "accept"
				? `Accepted ${successCount} suggestion${successCount !== 1 ? "s" : ""}`
				: `Rejected ${successCount} suggestion${successCount !== 1 ? "s" : ""}`,
		);
		_total = Math.max(0, _total - successCount);
		_renderCount();
		_renderPagination();
		_updateBatchButtons();
		const selectAll = document.getElementById("suggestions-select-all");
		if (selectAll) selectAll.checked = false;
	} catch (e) {
		showToast(e.message, "error");
		rows.forEach(({ row }) => {
			row.classList.remove("fade-out");
		});
	}
}

function _scoreColor(score) {
	if (score >= 0.85) return "#16a34a"; // green-600
	if (score >= 0.65) return "#65a30d"; // lime-600
	if (score >= 0.5) return "#ca8a04"; // yellow-600
	return "#a3a3a3"; // neutral-400
}

// Set memory filter when navigating from detail badge
export function setMemoryFilter(memoryId) {
	_memoryFilter = memoryId || null;
	_offset = 0;
}
