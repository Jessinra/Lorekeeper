// ── Shared mutable state ──
// All modules import directly from here and mutate these bindings.

export let selectedId = null;
export let allMemories = [];
export let allLinks = [];
export let showDeleted = false;
export const memSort = { field: "updated_at", dir: "desc" };
export const linkSort = { field: "score", dir: "desc" };
export let linksLoaded = false;
export let filterText = "";
export let timeFilterDays = null; // null = all, 0 = today, 3 = 3 days, 7 = 1 week
export let namespaceFilter = ""; // "" = all namespaces
export let detailEditMode = false;
export let detailData = null;

// Setters — used by modules that need to replace a top-level binding.
// (ES modules export live bindings for primitives only when re-exported via
// a setter; mutating the object fields of memSort / linkSort works directly.)

export function setSelectedId(v) {
	selectedId = v;
}
export function setAllMemories(v) {
	allMemories = v;
}
export function setAllLinks(v) {
	allLinks = v;
}
export function setShowDeleted(v) {
	showDeleted = v;
}
export function setLinksLoaded(v) {
	linksLoaded = v;
}
export function setFilterText(v) {
	filterText = v;
}
export function setTimeFilterDays(v) {
	timeFilterDays = v;
}
export function setNamespaceFilter(v) {
	namespaceFilter = v;
}
export function setDetailEditMode(v) {
	detailEditMode = v;
}
export function setDetailData(v) {
	detailData = v;
}
