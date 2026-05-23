import { showToast } from "./api.js";
import { esc } from "./utils.js";

let _stagedFile = null;

export function initBackup() {
	document
		.getElementById("import-file")
		.addEventListener("change", onImportFileChosen);
}

export function triggerExport() {
	const includeDel = document.getElementById("export-include-deleted").checked;
	const a = document.createElement("a");
	a.href = `/api/export?include_deleted=${includeDel}`;
	a.download = "";
	document.body.appendChild(a);
	a.click();
	a.remove();
}

export async function onImportFileChosen() {
	const input = document.getElementById("import-file");
	const file = input.files[0];
	if (!file) return;

	document.getElementById("import-filename").textContent = file.name;
	document.getElementById("backup-preview").style.display = "none";
	document.getElementById("btn-confirm-import").disabled = true;
	_stagedFile = null;

	try {
		const data = await _postForm("/api/import/preview", file);
		_renderPreview(data);
		_stagedFile = file;
		const total = data.memories_inserted + data.links_inserted;
		document.getElementById("btn-confirm-import").textContent =
			`Import ${data.memories_inserted} ${data.memories_inserted === 1 ? "memory" : "memories"}, ${data.links_inserted} ${data.links_inserted === 1 ? "link" : "links"}`;
		document.getElementById("btn-confirm-import").disabled = total === 0;
	} catch (e) {
		showToast(`Preview failed: ${e.message}`, "error");
	}
}

export async function confirmImport() {
	if (!_stagedFile) return;
	try {
		const data = await _postForm("/api/import/confirm", _stagedFile);
		showToast(
			`Imported ${data.memories_inserted} memories, ${data.links_inserted} links.`,
			"success",
		);
		_resetUI();
	} catch (e) {
		showToast(`Import failed: ${e.message}`, "error");
	}
}

async function _postForm(path, file) {
	const fd = new FormData();
	fd.append("file", file);
	const res = await fetch(path, { method: "POST", body: fd });
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || res.statusText);
	}
	return res.json();
}

function _renderPreview(data) {
	document.getElementById("bk-mem-insert").textContent = data.memories_inserted;
	document.getElementById("bk-mem-skip").textContent = data.memories_skipped;
	document.getElementById("bk-lnk-insert").textContent = data.links_inserted;
	document.getElementById("bk-lnk-skip").textContent = data.links_skipped;
	document.getElementById("bk-lnk-err").textContent = data.links_error;
	document.getElementById("backup-preview").style.display = "block";

	const list = document.getElementById("bk-detail-list");
	const mems = data.preview_memories || [];
	const links = data.preview_links || [];
	if (mems.length === 0 && links.length === 0) {
		list.style.display = "none";
		return;
	}

	const titleById = {};
	for (const m of mems) titleById[m.id] = m.title || m.id;

	const rows = [];

	for (const m of mems) {
		const desc = m.description
			? `<div style="font-size:12px;color:var(--subtle);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(m.description)}</div>`
			: "";
		const tag = m.type
			? `<span style="font-size:10px;padding:1px 5px;border-radius:3px;background:var(--chip-bg,#2a2a3a);color:var(--subtle);margin-left:6px">${esc(m.type)}</span>`
			: "";
		rows.push(`<div class="bk-row" style="padding:7px 12px;border-bottom:1px solid var(--border)">
      <div style="display:flex;align-items:center;font-size:13px;font-weight:500">
        <span style="color:var(--accent-green,#4caf50);margin-right:6px;font-size:11px">MEM</span>
        ${esc(m.title || m.id)}${tag}
      </div>
      ${desc}
    </div>`);
	}

	for (const lnk of links) {
		const src = esc(titleById[lnk.source_memory_id] || lnk.source_memory_id);
		const tgt = esc(titleById[lnk.target_memory_id] || lnk.target_memory_id);
		const rel = esc(lnk.relation_type || "related_to");
		const reason = lnk.reason
			? `<div style="font-size:12px;color:var(--subtle);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(lnk.reason)}</div>`
			: "";
		rows.push(`<div class="bk-row" style="padding:7px 12px;border-bottom:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:5px;font-size:13px">
        <span style="color:var(--accent-blue,#7c9fff);font-size:11px">LNK</span>
        <span style="font-weight:500">${src}</span>
        <span style="color:var(--subtle);font-size:11px">—${rel}→</span>
        <span style="font-weight:500">${tgt}</span>
      </div>
      ${reason}
    </div>`);
	}

	list.innerHTML = rows.join("");
	list.style.display = "block";
}

function _resetUI() {
	_stagedFile = null;
	document.getElementById("import-file").value = "";
	document.getElementById("import-filename").textContent = "No file chosen";
	document.getElementById("backup-preview").style.display = "none";
	const list = document.getElementById("bk-detail-list");
	list.style.display = "none";
	list.innerHTML = "";
	const btn = document.getElementById("btn-confirm-import");
	btn.disabled = true;
	btn.textContent = "Import";
}

window.triggerExport = triggerExport;
window.confirmImport = confirmImport;
