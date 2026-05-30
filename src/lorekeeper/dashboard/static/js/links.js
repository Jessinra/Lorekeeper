// ── Links tab ──
import { api, showToast } from "./api.js";
import { updateHeaderMeta, updateSortHeaders } from "./memories.js";
import * as state from "./state.js";
import { registerTab } from "./tab-registry.js";
import { clientSort, esc, fmt2, scoreClass } from "./utils.js";

// ── Self-register ──

registerTab("links", { load: loadLinks });

// ── Event listeners ──

document.addEventListener("app:links:changed", () => {
	if (state.linksLoaded) loadLinks();
});

document.addEventListener("app:sort:set", (e) => {
	if (e.detail.target === "link") setLinkSort(e.detail.field);
});

document.addEventListener("app:links:delete", (e) => {
	deleteLinkFromTab(e.detail.id);
});

document.addEventListener("app:links:relation-filter", (e) => {
	setLinkRelationFilter(e.detail.value);
});

document.addEventListener("app:links:load", () => loadLinks());

let _relationFilter = "";

export function setLinkRelationFilter(value) {
	_relationFilter = value;
	renderLinks();
}

export async function loadLinks() {
	const inc = document.getElementById("links-show-deleted").checked;
	state.setAllLinks(await api("GET", `/api/links?include_deleted=${inc}`));
	state.setLinksLoaded(true);
	renderLinks();
	updateHeaderMeta();
}

export function setLinkSort(field) {
	state.linkSort.dir =
		state.linkSort.field === field
			? state.linkSort.dir === "desc"
				? "asc"
				: "desc"
			: ["source_title", "target_title", "relation_type"].includes(field)
				? "asc"
				: "desc";
	state.linkSort.field = field;
	updateSortHeaders("lth-", state.linkSort, [
		"source_title",
		"relation_type",
		"target_title",
		"score",
		"usage_count",
	]);
	renderLinks();
}

export function renderLinks() {
	let filtered = state.allLinks;
	if (_relationFilter) {
		if (_relationFilter === "auto_linked") {
			filtered = filtered.filter((l) =>
				l.reason?.startsWith("auto-linked from"),
			);
		} else {
			filtered = filtered.filter((l) => l.relation_type === _relationFilter);
		}
	}
	const sorted = clientSort(filtered, state.linkSort.field, state.linkSort.dir);
	document.getElementById("links-count").textContent =
		`${filtered.length} / ${state.allLinks.length}`;
	document.getElementById("link-rows").innerHTML = sorted
		.map(
			(l) => `
    <tr>
      <td class="col-link-title" data-memory-id="${l.source_memory_id}" title="${esc(l.source_title)}">${esc(l.source_title)}</td>
      <td><span class="relation-badge">${esc(l.relation_type)}</span></td>
      <td class="col-link-title" data-memory-id="${l.target_memory_id}" title="${esc(l.target_title)}">${esc(l.target_title)}</td>
      <td class="col-reason" title="${esc(l.reason)}">${esc(l.reason)}</td>
      <td class="col-score"><span class="score-badge ${scoreClass(l.score)}">${fmt2(l.score)}</span></td>
      <td class="col-usage-r">${l.usage_count}</td>
      <td class="col-actions"><button class="btn-sm btn-danger" data-link-delete="${l.id}">×</button></td>
    </tr>
  `,
		)
		.join("");
}

export async function deleteLinkFromTab(linkId) {
	if (!confirm("Delete this link?")) return;
	try {
		await api("DELETE", `/api/links/${linkId}`);
		showToast("Link deleted");
		loadLinks();
	} catch (e) {
		showToast(e.message, "error");
	}
}
