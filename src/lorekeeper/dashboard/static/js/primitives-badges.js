// ──────────────────────────────────────────────────────
// UI Primitives — Badges & Indicators — LKPR-126
// Small read-only display elements: ScorePill, NamespaceDot, RelationPill.
// ──────────────────────────────────────────────────────

import { DESIGN_TOKENS, hashColor, scoreTier, el } from "./primitives-core.js";

// ── 1. ScorePill ──

/**
 * @param {number|null|undefined} score - 0–10 scale
 * @returns {HTMLSpanElement}
 */
export function ScorePill(score) {
  const tier = scoreTier(score);
  const pill = el("span", { className: `pr-score-pill ${tier}` });
  pill.textContent = score != null ? String(Math.round(score)) : "\u2014";
  return pill;
}

// ── 2. NamespaceDot ──

/**
 * @param {string} namespace
 * @returns {HTMLSpanElement}
 */
export function NamespaceDot(namespace) {
  const color = hashColor(namespace);
  const dot = el("span", {
    className: "pr-ns-dot",
    dataset: { color },
  });
  dot.textContent = namespace || "\u2014";
  return dot;
}

// ── 3. RelationPill ──

/**
 * @param {string} type - e.g. "auto_linked", "related_to", "used_in", etc.
 * @returns {HTMLSpanElement}
 */
export function RelationPill(type) {
  const t = type || "default";
  const pill = el("span", {
    className: "pr-rel-pill",
    dataset: { type: t },
  });
  pill.textContent = t.replace(/_/g, " ");
  return pill;
}