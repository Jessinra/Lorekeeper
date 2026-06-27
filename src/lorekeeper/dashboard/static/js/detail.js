// ── Detail tab ──
import { api, showToast } from "./api.js";
import * as state from "./state.js";
import { dispatch, switchTab } from "./tab.js";
import { registerTab } from "./tab-registry.js";
import { esc, fmt2, fmtDate, isToday, scoreClass } from "./utils.js";

// ── Self-register ──

registerTab("detail", {});

// ── Event listener: memory selected → load detail ──

document.addEventListener("app:memory:select", (e) => {
	selectMemory(e.detail.id);
});

// ── Detail action listeners (from delegated data-action clicks) ──

document.addEventListener("app:detail:enter-edit", () => enterEditMode());
document.addEventListener("app:detail:cancel-edit", () => cancelEditMode());

document.addEventListener("app:detail:save", (e) => {
	saveMemory(e.detail.id);
});

document.addEventListener("app:detail:soft-delete", (e) => {
	const current = e.detail.current === "true";
	toggleSoftDelete(e.detail.id, current);
});

document.addEventListener("app:detail:hard-delete", (e) => {
	confirmDelete(e.detail.id);
});

document.addEventListener("app:detail:delete-link", (e) => {
	deleteLink(e.detail.linkid, e.detail.memoryid);
});

document.addEventListener("app:detail:add-link", (e) => {
	submitAddLink(e.detail.sourceId);
});

document.addEventListener("app:detail:copy-id", (e) => {
	copyId(e.detail.id);
});

document.addEventListener("app:suggestions:navigate", (e) => {
	// Import dynamically to avoid circular deps.
	// switchTab("suggestions") already calls loadSuggestions() via the tab
	// registry — no extra dispatch needed.
	import("./suggestions.js").then((mod) => {
		mod.setMemoryFilter(e.detail.memoryId);
		switchTab("suggestions");
	});
});

// ── Core ──

export async function selectMemory(id) {
	state.setSelectedId(id);
	state.setDetailEditMode(false);
	switchTab("detail");
	dispatch("memory:selected", { id });

	let data;
	try {
		data = await api("GET", `/api/memories/${id}`);
	} catch (e) {
		showToast(e.message, "error");
		return;
	}

	state.setDetailData(data);
	_renderDetail(data, false);

	// Fetch pending suggestion count and inject badge
	_fetchSuggestionBadge(m.id);
}

export function enterEditMode() {
	state.setDetailEditMode(true);
	_renderDetail(state.detailData, true);
}
export function cancelEditMode() {
	state.setDetailEditMode(false);
	_renderDetail(state.detailData, false);
}

export function _renderDetail(data, editMode) {
	document.getElementById("detail-placeholder").classList.add("hidden");
	document.getElementById("detail-page").classList.remove("hidden");
	document.getElementById("tab-detail").scrollTop = 0;

	const m = data.memory;
	const links = data.links;
	const conf = m.confidence != null ? fmt2(m.confidence) : "—";

	const headerActions = editMode
		? ""
		: `<button class="btn-secondary btn-sm" data-action="detail:enter-edit" data-testid="detail-edit">Edit</button>`;

	// Returns a field-group cell. In edit mode renders editHTML; in view mode renders viewHTML.
	const field = (label, viewHTML, editHTML, spanClass = "") =>
		`<div class="field-group${spanClass ? ` ${spanClass}` : ""}">
      <label>${label}</label>
      ${editMode ? editHTML : viewHTML}
    </div>`;

	const bodyHTML = `
    <div class="detail-grid">
      ${
				editMode
					? field(
							"Title",
							`<div class="field-value fv-prominent">${esc(m.title)}</div>`,
							`<input type="text" id="d-title" value="${esc(m.title)}">`,
							"span-2",
						)
					: ""
			}
      ${field(
				"Description",
				m.description
					? `<div class="field-value fv-secondary">${esc(m.description)}</div>`
					: `<div class="field-value fv-empty">—</div>`,
				`<input type="text" id="d-description" value="${esc(m.description ?? "")}">`,
				"span-2",
			)}
      ${field(
				"Content",
				`<div class="field-value fv-content">${esc(m.content)}</div>`,
				`<textarea id="d-content" rows="8">${esc(m.content)}</textarea>`,
				"span-2",
			)}
      ${field(
				"Namespace",
				`<div class="field-value"><span class="ns-badge">${esc(m.namespace ?? "shared")}</span></div>`,
				`<div class="field-value"><span class="ns-badge">${esc(m.namespace ?? "shared")}</span></div>`,
			)}
      ${field(
				"Score",
				`<div class="field-value"><span class="score-badge ${scoreClass(m.score)}">${fmt2(m.score)}</span></div>`,
				`<input type="number" id="d-score" value="${fmt2(m.score)}" min="0" max="10" step="0.01">`,
			)}
      ${field(
				"Confidence / Samples",
				`<div class="field-value">${conf} / ${m.confidence_count}</div>`,
				`<div class="field-value">${conf} / ${m.confidence_count}</div>`,
			)}
      ${field(
				"Usage count",
				`<div class="field-value">${m.usage_count}</div>`,
				`<div class="field-value">${m.usage_count}</div>`,
			)}
      ${field(
				"Status",
				`<div class="field-value">${m.soft_deleted ? '<span class="badge badge-deleted">soft deleted</span>' : "Active"}</div>`,
				`<div class="field-value">${m.soft_deleted ? '<span class="badge badge-deleted">soft deleted</span>' : "Active"}</div>`,
			)}
      ${field(
				"Updated",
				`<div class="field-value">${fmtDate(m.updated_at)}</div>`,
				`<div class="field-value">${fmtDate(m.updated_at)}</div>`,
			)}
      ${field(
				"Created",
				`<div class="field-value">${fmtDate(m.created_at)}</div>`,
				`<div class="field-value">${fmtDate(m.created_at)}</div>`,
			)}
    </div>
    ${
			editMode
				? `
    <div class="action-bar">
      <button class="btn-primary" data-action="detail:save" data-id="${m.id}">Save</button>
      <button class="btn-secondary" data-action="detail:cancel-edit">Cancel</button>
      <span style="flex:1"></span>
      <button class="btn-warning" data-action="detail:soft-delete" data-id="${m.id}" data-current="${!!m.soft_deleted}">
        ${m.soft_deleted ? "Restore" : "Soft Delete"}
      </button>
      <button class="btn-danger" data-action="detail:hard-delete" data-id="${m.id}" data-testid="detail-hard-delete">Hard Delete</button>
    </div>
    `
				: ""
		}
  `;

	const linksHTML = `
    <div class="links-section">
      <div class="links-section-header">
        <span class="links-section-title">Links</span>
        ${links.length > 0 ? `<span class="links-total-count">${links.length}</span>` : ""}
      </div>
      ${_renderGroupedLinks(links, m.id)}
      <div class="add-link-form">
        <h4>Add Link</h4>
        <div class="add-link-row">
          <select id="link-target">
            <option value="">Target memory…</option>
            ${state.allMemories
							.filter((x) => x.id !== m.id)
							.map(
								(x) =>
									`<option value="${x.id}">${esc(x.title.slice(0, 70))}</option>`,
							)
							.join("")}
          </select>
          <select id="link-relation">
            <option value="related_to">related_to</option>
            <option value="used_in">used_in</option>
            <option value="used_for">used_for</option>
            <option value="used_by">used_by</option>
            <option value="used_as">used_as</option>
          </select>
        </div>
        <textarea id="link-reason" placeholder="Reason for this link…" rows="2"></textarea>
        <button class="btn-primary btn-sm" data-action="detail:add-link" data-source-id="${m.id}">Add Link</button>
      </div>
    </div>
  `;

	document.getElementById("detail-content").innerHTML = `
    <div class="detail-header">
      <button class="btn-ghost btn-sm" data-tab="memories">← Back</button>
      <h2>${isToday(m.created_at) ? '<span class="new-dot"></span>' : ""}${esc(m.title)}</h2>
      <span class="id-badge" title="Click to copy ID" data-action="detail:copy-id" data-id="${m.id}">${m.id.slice(0, 8)}…</span>
      ${headerActions}
    </div>
    <div id="detail-suggestion-badge"></div>
    ${bodyHTML}
    ${linksHTML}
  `;
}

// ── Pending suggestion badge ──

async function _fetchSuggestionBadge(memoryId) {
	const badgeContainer = document.getElementById("detail-suggestion-badge");
	if (!badgeContainer) return;
	try {
		const { count } = await api(
			"GET",
			`/api/suggestions/count?memory_id=${encodeURIComponent(memoryId)}`,
		);
		if (count > 0) {
			badgeContainer.innerHTML = `
        <button class="suggestion-badge" data-action="suggestions:navigate" data-memory-id="${esc(memoryId)}">
          ${count} pending link suggestion${count !== 1 ? "s" : ""} →
        </button>`;
		}
	} catch {
		// Silently fail — badge is a nice-to-have
	}
}

function _renderGroupedLinks(links, memoryId) {
	if (links.length === 0) return '<div class="no-links">No links yet.</div>';

	const groups = {};
	for (const link of links) {
		const rt = link.relation_type;
		if (!groups[rt]) groups[rt] = [];
		groups[rt].push(link);
	}

	return Object.entries(groups)
		.map(
			([relType, groupLinks]) => `
    <details class="link-group">
      <summary>
        <span class="link-group-chevron">›</span>
        <span class="relation-badge link-group-label">${esc(relType)}</span>
        <span class="link-group-count">${groupLinks.length}</span>
      </summary>
      <div class="link-group-items">
        ${groupLinks.map((l) => renderLinkItem(l, memoryId)).join("")}
      </div>
    </details>
  `,
		)
		.join("");
}

export function renderLinkItem(link, currentId) {
	const isSource = link.source_memory_id === currentId;
	const otherId = isSource ? link.target_memory_id : link.source_memory_id;
	const other = state.allMemories.find((m) => m.id === otherId);
	const otherTitle = other ? other.title : `${otherId.slice(0, 12)}…`;
	const reason = (link.reason || "").slice(0, 120);
	return `
    <div class="link-item">
      <span class="link-direction">${isSource ? "→" : "←"}</span>
      <span class="link-target" data-memory-id="${otherId}" title="${esc(otherTitle)}">${esc(otherTitle)}</span>
      <button class="btn-sm btn-danger link-del-btn" data-action="detail:delete-link" data-linkid="${link.id}" data-memoryid="${currentId}">×</button>
      ${reason ? `<span class="link-reason">${esc(reason)}</span>` : ""}
    </div>`;
}

// ── Memory CRUD ──

export async function saveMemory(id) {
	const body = {
		title: document.getElementById("d-title").value,
		description: document.getElementById("d-description").value,
		content: document.getElementById("d-content").value,
		score: parseFloat(document.getElementById("d-score").value),
	};
	try {
		await api("PATCH", `/api/memories/${id}`, body);
		showToast("Saved");
		state.setDetailEditMode(false);
		dispatch("memories:changed");
		dispatch("links:changed");
		selectMemory(id);
	} catch (e) {
		showToast(e.message, "error");
	}
}

export async function toggleSoftDelete(id, current) {
	try {
		await api("PATCH", `/api/memories/${id}`, { soft_deleted: !current });
		showToast(current ? "Restored" : "Soft deleted");
		dispatch("memories:changed");
		selectMemory(id);
	} catch (e) {
		showToast(e.message, "error");
	}
}

export async function confirmDelete(id) {
	if (
		!confirm(
			"Hard-delete this memory and all its links? This cannot be undone.",
		)
	)
		return;
	try {
		await api("DELETE", `/api/memories/${id}`);
		showToast("Deleted");
		state.setSelectedId(null);
		document.getElementById("detail-placeholder").classList.remove("hidden");
		document.getElementById("detail-page").classList.add("hidden");
		dispatch("memories:changed");
		dispatch("links:changed");
		switchTab("memories");
	} catch (e) {
		showToast(e.message, "error");
	}
}

export async function deleteLink(linkId, memoryId) {
	try {
		await api("DELETE", `/api/links/${linkId}`);
		dispatch("links:changed");
		selectMemory(memoryId);
	} catch (e) {
		showToast(e.message, "error");
	}
}

export async function submitAddLink(sourceId) {
	const targetId = document.getElementById("link-target").value;
	const relation = document.getElementById("link-relation").value;
	const reason = (document.getElementById("link-reason").value || "").trim();
	if (!targetId) {
		showToast("Select a target memory", "error");
		return;
	}
	if (!reason) {
		showToast("Enter a reason for the link", "error");
		return;
	}
	try {
		await api("POST", "/api/links", {
			source_memory_id: sourceId,
			target_memory_id: targetId,
			relation_type: relation,
			reason,
		});
		showToast("Link added");
		dispatch("links:changed");
		selectMemory(sourceId);
	} catch (e) {
		showToast(e.message, "error");
	}
}

export async function copyId(id) {
	await navigator.clipboard.writeText(id);
	showToast("ID copied");
}
