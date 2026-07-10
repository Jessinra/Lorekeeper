// ──────────────────────────────────────────────────────
// UI Primitives — Barrel — LKPR-126
// Re-exports all primitive components for backward compatibility.
// Consumers can import from "./primitives.js" or from individual files.
// ──────────────────────────────────────────────────────

export { DESIGN_TOKENS } from "./primitives-core.js";
export { ScorePill, NamespaceDot, RelationPill } from "./primitives-badges.js";
export { FilterChip, SegmentedControl, ToggleSwitch } from "./primitives-controls.js";
export { StatTile, HealthRing, EmptyState, HeatmapGrid } from "./primitives-display.js";