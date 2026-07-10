// ──────────────────────────────────────────────────────
// UI Primitives — Badges & Indicators — LKPR-126
// Small read-only display elements: ScorePill, NamespaceDot, RelationPill.
// ──────────────────────────────────────────────────────

import { hashColor, scoreTier, el } from "./primitives-core.js";

// ── 1. ScorePill ──

/**
 * @param {object} opts
 * @param {number|null|undefined} opts.score - 0–10 scale
 * @returns {HTMLSpanElement}
 */
export function ScorePill({ score } = {}) {
  const tier = scoreTier(score);
  const pill = el("span", { className: `pr-score-pill ${tier}` });
  const clamped = score != null ? Math.max(0, Math.min(10, Math.round(score))) : null;
  pill.textContent = clamped != null ? String(clamped) : "\u2014";
  return pill;
}

// ── 2. NamespaceDot ──

/**
 * @param {object} opts
 * @param {string} opts.namespace
 * @returns {HTMLSpanElement}
 */
export function NamespaceDot({ namespace } = {}) {
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
 * @param {object} opts
 * @param {string} opts.type - e.g. "auto_linked", "related_to", "used_in", etc.
 * @returns {HTMLSpanElement}
 */
export function RelationPill({ type } = {}) {
  const t = type || "default";
  const pill = el("span", {
    className: "pr-rel-pill",
    dataset: { type: t },
  });
  pill.textContent = t.replace(/_/g, " ");
  return pill;
}