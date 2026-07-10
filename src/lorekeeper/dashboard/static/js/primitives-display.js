// ──────────────────────────────────────────────────────
// UI Primitives — Data Display — LKPR-126
// Data visualization widgets: StatTile, HealthRing, EmptyState, HeatmapGrid.
// ──────────────────────────────────────────────────────

import { scoreTier, el } from "./primitives-core.js";
import { ScorePill } from "./primitives-badges.js";

// ── 7. StatTile ──

/**
 * @param {object} opts
 * @param {string} [opts.icon] - SVG string or text label
 * @param {string|number} opts.value
 * @param {string} opts.label
 * @param {object} [opts.statusPill] - {score, label, color?}
 * @returns {HTMLDivElement}
 */
export function StatTile({ icon, value, label, statusPill }) {
  const tile = el("div", { className: "pr-stat-tile" });

  // Icon row
  if (icon) {
    const iconWrap = el("div", { className: "pr-stat-tile-icon" });
    if (icon.startsWith("<svg")) {
      iconWrap.innerHTML = icon; // static SVG — safe
    } else {
      iconWrap.textContent = icon;
    }
    tile.appendChild(iconWrap);
  }

  // Value
  const valEl = el("div", { className: "pr-stat-tile-value" });
  valEl.textContent = String(value ?? "\u2014");
  tile.appendChild(valEl);

  // Label
  const lblEl = el("div", { className: "pr-stat-tile-label" });
  lblEl.textContent = label;
  tile.appendChild(lblEl);

  // Status pill
  if (statusPill) {
    const statusEl = el("div", { className: "pr-stat-tile-status" });
    const pill = ScorePill(statusPill.score);
    pill.style.minWidth = "auto";
    pill.style.padding = "1px 6px";
    pill.style.fontSize = "10px";
    statusEl.appendChild(pill);
    if (statusPill.label) {
      const txt = document.createTextNode(` ${statusPill.label}`);
      statusEl.appendChild(txt);
    }
    tile.appendChild(statusEl);
  }

  return tile;
}

// ── 8. HealthRing ──

const _RING_R = 22;
const _RING_C = 2 * Math.PI * _RING_R; // circumference

/**
 * @param {object} opts
 * @param {number} opts.percent - 0–100
 * @returns {HTMLDivElement}
 */
export function HealthRing({ percent }) {
  const pct = Math.max(0, Math.min(100, percent ?? 0));
  const offset = _RING_C * (1 - pct / 100);

  const tier = scoreTier(pct / 10);
  const strokeColor =
    tier === "high"
      ? "var(--success)"
      : tier === "mid"
        ? "var(--warning)"
        : "var(--danger)";

  const ring = el("div", { className: "pr-health-ring" });

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "56");
  svg.setAttribute("height", "56");
  svg.setAttribute("viewBox", "0 0 56 56");

  // Background circle
  const bgCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  bgCircle.setAttribute("class", "pr-health-ring-bg");
  bgCircle.setAttribute("cx", "28");
  bgCircle.setAttribute("cy", "28");
  bgCircle.setAttribute("r", String(_RING_R));
  svg.appendChild(bgCircle);

  // Foreground arc
  const fgCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  fgCircle.setAttribute("class", "pr-health-ring-fg");
  fgCircle.setAttribute("cx", "28");
  fgCircle.setAttribute("cy", "28");
  fgCircle.setAttribute("r", String(_RING_R));
  fgCircle.setAttribute("stroke-dasharray", String(_RING_C));
  fgCircle.setAttribute("stroke-dashoffset", String(offset));
  fgCircle.style.stroke = strokeColor;
  svg.appendChild(fgCircle);

  ring.appendChild(svg);

  // Center label
  const label = el("span", {
    className: `pr-health-ring-label ${tier}`,
  });
  label.textContent = `${Math.round(pct)}%`;
  ring.appendChild(label);

  return ring;
}

// ── 9. EmptyState ──

/**
 * @param {object} opts
 * @param {string} [opts.title]
 * @param {string} [opts.message]
 * @param {object} [opts.action] - {label, onClick}
 * @returns {HTMLDivElement}
 */
export function EmptyState({ title, message, action }) {
  const empty = el("div", { className: "pr-empty" });

  const icon = el("div", { className: "pr-empty-icon" });
  icon.textContent = "\u2298";
  empty.appendChild(icon);

  if (title) {
    const titleEl = el("div", { className: "pr-empty-title" });
    titleEl.textContent = title;
    empty.appendChild(titleEl);
  }

  if (message) {
    const msgEl = el("div", { className: "pr-empty-message" });
    msgEl.textContent = message;
    empty.appendChild(msgEl);
  }

  if (action) {
    const wrap = el("div", { className: "pr-empty-action" });
    const btn = el("button", {
      className: "btn-primary btn-sm",
      type: "button",
    });
    btn.textContent = action.label;
    btn.addEventListener("click", action.onClick);
    wrap.appendChild(btn);
    empty.appendChild(wrap);
  }

  return empty;
}

// ── 10. HeatmapGrid ──

const _CELL_S = 16;
const _GAP = 2;
const _PAD_L = 0;
const _PAD_T = 0;

function _intensityToHex(i) {
  const r = Math.round(0x82 * (1 - i));
  const g = Math.round(0xf6 - 0x74 * i);
  const b = 0xf6;
  const toHex = (n) =>
    Math.max(0, Math.min(255, n))
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * @param {object} opts
 * @param {number[][]} opts.data  - 2D array of values (rows x cols)
 * @param {string[]} [opts.rowLabels]
 * @param {string[]} [opts.colLabels]
 * @returns {HTMLDivElement}
 */
export function HeatmapGrid({ data = [], rowLabels = [], colLabels = [] }) {
  if (!data.length || !data[0].length) {
    const empty = el("div", { className: "pr-heatmap" });
    empty.textContent = "No data";
    return empty;
  }

  const rows = data.length;
  const cols = data[0].length;

  // Find min/max for color scaling
  let minVal = Infinity;
  let maxVal = -Infinity;
  for (const row of data) {
    for (const v of row) {
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    }
  }
  const range = maxVal - minVal || 1;

  // Label dimensions
  const maxRowLabelW = rowLabels.length
    ? Math.max(...rowLabels.map((l) => l.length)) * 7 + 8
    : 0;
  const colLabelH = colLabels.length ? 16 : 0;

  const w = maxRowLabelW + cols * (_CELL_S + _GAP) + _PAD_L;
  const h = colLabelH + rows * (_CELL_S + _GAP) + _PAD_T;

  const heatmap = el("div", { className: "pr-heatmap" });

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(w));
  svg.setAttribute("height", String(h));
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);

  // Column labels
  for (let c = 0; c < cols; c++) {
    if (c < colLabels.length) {
      const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      const x = maxRowLabelW + c * (_CELL_S + _GAP) + _CELL_S / 2;
      txt.setAttribute("x", String(x));
      txt.setAttribute("y", "10");
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("fill", "var(--subtle)");
      txt.textContent = colLabels[c];
      svg.appendChild(txt);
    }
  }

  // Cells
  for (let r = 0; r < rows; r++) {
    // Row label
    if (r < rowLabels.length) {
      const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      txt.setAttribute("x", String(maxRowLabelW - 4));
      txt.setAttribute(
        "y",
        String(colLabelH + r * (_CELL_S + _GAP) + _CELL_S / 2 + 3)
      );
      txt.setAttribute("text-anchor", "end");
      txt.setAttribute("fill", "var(--subtle)");
      txt.textContent = rowLabels[r];
      svg.appendChild(txt);
    }

    for (let c = 0; c < cols; c++) {
      const v = data[r][c];
      const normalized = (v - minVal) / range;
      const intensity = Math.round(0.15 + normalized * 0.65);
      const hex = _intensityToHex(intensity);

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      const x = maxRowLabelW + c * (_CELL_S + _GAP) + _PAD_L;
      const y = colLabelH + r * (_CELL_S + _GAP) + _PAD_T;
      rect.setAttribute("class", "pr-heatmap-cell");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", String(y));
      rect.setAttribute("width", String(_CELL_S));
      rect.setAttribute("height", String(_CELL_S));
      rect.setAttribute("rx", "2");
      rect.setAttribute("fill", hex);
      rect.setAttribute("stroke", "transparent");
      rect.setAttribute("stroke-width", "1");

      // Tooltip
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      const rowLabel = rowLabels[r] || `row ${r}`;
      const colLabel = colLabels[c] || `col ${c}`;
      title.textContent = `${rowLabel}, ${colLabel}: ${v}`;
      rect.appendChild(title);

      svg.appendChild(rect);
    }
  }

  heatmap.appendChild(svg);
  return heatmap;
}