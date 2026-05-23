// ── Pure utility functions ── no state, no DOM side-effects ──

const _pad = (n) => String(n).padStart(2, "0");
const _UTC8_MS = 8 * 60 * 60 * 1000;

export function esc(str) {
	return String(str ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

export function scoreClass(s) {
	if (s >= 6) return "score-high";
	if (s >= 3) return "score-mid";
	return "score-low";
}

export function fmt2(n) {
	return (n ?? 0).toFixed(2);
}

export function fmtDate(iso) {
	if (!iso) return "";
	const d = new Date(iso);
	return `${d.getFullYear()}-${_pad(d.getMonth() + 1)}-${_pad(d.getDate())} ${_pad(d.getHours())}:${_pad(d.getMinutes())}`;
}

export function fmtDatePlus8(iso) {
	if (!iso) return "";
	const p8 = new Date(new Date(iso).getTime() + _UTC8_MS);
	return `${p8.getUTCFullYear()}-${_pad(p8.getUTCMonth() + 1)}-${_pad(p8.getUTCDate())} ${_pad(p8.getUTCHours())}:${_pad(p8.getUTCMinutes())}`;
}

export function fmtRelative(iso) {
	if (!iso) return "";
	const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
	if (mins < 1) return "just now";
	if (mins < 60) return `${mins}m ago`;
	const hrs = Math.floor(mins / 60);
	const rem = mins % 60;
	if (hrs < 24) return rem > 0 ? `${hrs}h ${rem}m ago` : `${hrs}h ago`;
	return `${Math.floor(hrs / 24)}d ago`;
}

const _todayLocal = (() => {
	const d = new Date();
	return `${d.getFullYear()}-${_pad(d.getMonth() + 1)}-${_pad(d.getDate())}`;
})();
export function isToday(iso) {
	if (!iso) return false;
	const d = new Date(iso);
	return (
		`${d.getFullYear()}-${_pad(d.getMonth() + 1)}-${_pad(d.getDate())}` ===
		_todayLocal
	);
}

export function clientSort(data, field, dir) {
	return [...data].sort((a, b) => {
		let av = a[field] ?? "",
			bv = b[field] ?? "";
		if (typeof av === "string") {
			av = av.toLowerCase();
			bv = String(bv).toLowerCase();
		}
		if (av < bv) return dir === "asc" ? -1 : 1;
		if (av > bv) return dir === "asc" ? 1 : -1;
		return 0;
	});
}

export function parseJsonArray(raw) {
	if (!raw) return [];
	try {
		return JSON.parse(raw);
	} catch {
		return [];
	}
}

export function htmlSection(title, text) {
	if (!text) return "";
	return `<div class="ref-section"><div class="ref-section-title">${title}</div><div class="ref-section-body">${esc(text)}</div></div>`;
}

// Expose on window for any inline onclick that may need it (none currently do,
// but kept for symmetry and future safety).
window.esc = esc;
window.scoreClass = scoreClass;
window.fmt2 = fmt2;
window.fmtDate = fmtDate;
window.fmtDatePlus8 = fmtDatePlus8;
window.fmtRelative = fmtRelative;
window.isToday = isToday;
window.clientSort = clientSort;
