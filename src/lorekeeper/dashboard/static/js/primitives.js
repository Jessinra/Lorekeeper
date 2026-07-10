// ──────────────────────────────────────────────────────
// UI Primitives — LKPR-126
// Vanilla JS component functions for the Lorekeeper dashboard.
// Each function returns an HTMLElement. No framework.
//
// CONSTRAINT: No innerHTML for dynamic content.
// Static SVG icons may use innerHTML (they are predefined).
// ──────────────────────────────────────────────────────

// ── Design Tokens ──

export const DESIGN_TOKENS = {
  colors: {
    primary: "var(--primary)",
    primaryH: "var(--primary-h)",
    primaryBg: "var(--primary-bg)",
    success: "var(--success)",
    warning: "var(--warning)",
    danger: "var(--danger)",
    text: "var(--text)",
    muted: "var(--muted)",
    subtle: "var(--subtle)",
    surface: "var(--surface)",
    bg: "var(--bg)",
    border: "var(--border)",
  },
  radius: "var(--radius)",
  transition: "var(--t)",
  font: {
    mono: "'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace",
    ui: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  score: {
    highThreshold: 7,
    midThreshold: 5,
  },
};

// ── Helpers ──

const _NS_COLORS = [
  "indigo", "teal", "blue", "amber", "pink",
  "green", "purple", "red", "cyan", "gray",
];

/** Deterministic color from a string. */
function _hashColor(s) {
  if (!s) return "gray";
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) | 0;
  }
  return _NS_COLORS[Math.abs(hash) % _NS_COLORS.length];
}

function _scoreTier(score) {
  if (score == null) return "low";
  if (score >= DESIGN_TOKENS.score.highThreshold) return "high";
  if (score >= DESIGN_TOKENS.score.midThreshold) return "mid";
  return "low";
}

function _el(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") {
      el.className = v;
    } else if (k === "dataset") {
      Object.assign(el.dataset, v);
    } else {
      el.setAttribute(k, v);
    }
  }
  for (const child of children) {
    if (child instanceof Node) {
      el.appendChild(child);
    } else if (child != null) {
      el.appendChild(document.createTextNode(String(child)));
    }
  }
  return el;
}

// ── 1. ScorePill ──

/**
 * @param {number|null|undefined} score - 0–10 scale
 * @returns {HTMLSpanElement}
 */
export function ScorePill(score) {
  const tier = _scoreTier(score);
  const el = _el("span", { className: `pr-score-pill ${tier}` });
  el.textContent = score != null ? String(Math.round(score)) : "—";
  return el;
}

// ── 2. NamespaceDot ──

/**
 * @param {string} namespace
 * @returns {HTMLSpanElement}
 */
export function NamespaceDot(namespace) {
  const color = _hashColor(namespace);
  const el = _el("span", {
    className: "pr-ns-dot",
    dataset: { color },
  });
  el.textContent = namespace || "—";
  return el;
}

// ── 3. RelationPill ──

/**
 * @param {string} type - e.g. "auto_linked", "related_to", "used_in", etc.
 * @returns {HTMLSpanElement}
 */
export function RelationPill(type) {
  const t = type || "default";
  const el = _el("span", {
    className: "pr-rel-pill",
    dataset: { type: t },
  });
  el.textContent = t.replace(/_/g, " ");
  return el;
}

// ── 4. FilterChip ──

/**
 * @param {object} opts
 * @param {string} opts.label
 * @param {boolean} [opts.active=false]
 * @param {number} [opts.count]
 * @param {(active: boolean) => void} [opts.onToggle]
 * @returns {HTMLButtonElement}
 */
export function FilterChip({ label, active = false, count, onToggle }) {
  const el = _el("button", {
    className: `pr-filter-chip${active ? " active" : ""}`,
    type: "button",
  });
  el.textContent = label;

  if (count != null) {
    const badge = _el("span", { className: "pr-filter-chip-count" });
    badge.textContent = String(count);
    el.appendChild(badge);
  }

  el.addEventListener("click", () => {
    const next = !el.classList.contains("active");
    el.classList.toggle("active", next);
    if (onToggle) onToggle(next);
  });

  return el;
}

// ── 5. SegmentedControl ──

/**
 * @param {object} opts
 * @param {Array<{label: string, value: string}>} opts.options
 * @param {string} opts.value - selected value
 * @param {(value: string) => void} [opts.onChange]
 * @returns {HTMLDivElement}
 */
export function SegmentedControl({ options = [], value, onChange }) {
  const el = _el("div", { className: "pr-segmented" });

  for (const opt of options) {
    const btn = _el("button", {
      className: `pr-seg-opt${opt.value === value ? " active" : ""}`,
      type: "button",
    });
    btn.textContent = opt.label;

    btn.addEventListener("click", () => {
      if (btn.classList.contains("active")) return;
      el.querySelectorAll(".pr-seg-opt").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      if (onChange) onChange(opt.value);
    });

    el.appendChild(btn);
  }

  return el;
}

// ── 6. ToggleSwitch ──

/**
 * @param {object} opts
 * @param {boolean} [opts.checked=false]
 * @param {(checked: boolean) => void} [opts.onChange]
 * @param {string} [opts.label]
 * @returns {HTMLLabelElement}
 */
export function ToggleSwitch({ checked = false, onChange, label }) {
  const el = _el("label", { className: `pr-toggle${checked ? " on" : ""}` });

  const track = _el("span", { className: "pr-toggle-track" });
  const input = _el("input", {
    className: "pr-toggle-input",
    type: "checkbox",
  });
  input.checked = checked;

  input.addEventListener("change", () => {
    el.classList.toggle("on", input.checked);
    if (onChange) onChange(input.checked);
  });

  track.appendChild(input);
  el.appendChild(track);

  if (label != null) {
    const labelSpan = _el("span");
    labelSpan.textContent = label;
    el.appendChild(labelSpan);
  }

  return el;
}

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
  const el = _el("div", { className: "pr-stat-tile" });

  // Icon row
  if (icon) {
    const iconWrap = _el("div", { className: "pr-stat-tile-icon" });
    if (icon.startsWith("<svg")) {
      iconWrap.innerHTML = icon; // static SVG — safe
    } else {
      iconWrap.textContent = icon;
    }
    el.appendChild(iconWrap);
  }

  // Value
  const valEl = _el("div", { className: "pr-stat-tile-value" });
  valEl.textContent = String(value ?? "—");
  el.appendChild(valEl);

  // Label
  const lblEl = _el("div", { className: "pr-stat-tile-label" });
  lblEl.textContent = label;
  el.appendChild(lblEl);

  // Status pill
  if (statusPill) {
    const statusEl = _el("div", { className: "pr-stat-tile-status" });
    const pill = ScorePill(statusPill.score);
    pill.style.minWidth = "auto";
    pill.style.padding = "1px 6px";
    pill.style.fontSize = "10px";
    statusEl.appendChild(pill);
    if (statusPill.label) {
      const txt = document.createTextNode(` ${statusPill.label}`);
      statusEl.appendChild(txt);
    }
    el.appendChild(statusEl);
  }

  return el;
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

  const tier = _scoreTier(pct / 10);
  const strokeColor =
    tier === "high"
      ? "var(--success)"
      : tier === "mid"
        ? "var(--warning)"
        : "var(--danger)";

  const el = _el("div", { className: "pr-health-ring" });

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", "56");
  svg.setAttribute("height", "56");
  svg.setAttribute("viewBox", "0 0 56 56");

  // Background circle
  const bgCircle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );
  bgCircle.setAttribute("class", "pr-health-ring-bg");
  bgCircle.setAttribute("cx", "28");
  bgCircle.setAttribute("cy", "28");
  bgCircle.setAttribute("r", String(_RING_R));
  svg.appendChild(bgCircle);

  // Foreground arc
  const fgCircle = document.createElementNS(
    "http://www.w3.org/2000/svg",
    "circle"
  );
  fgCircle.setAttribute("class", "pr-health-ring-fg");
  fgCircle.setAttribute("cx", "28");
  fgCircle.setAttribute("cy", "28");
  fgCircle.setAttribute("r", String(_RING_R));
  fgCircle.setAttribute("stroke-dasharray", String(_RING_C));
  fgCircle.setAttribute("stroke-dashoffset", String(offset));
  fgCircle.style.stroke = strokeColor;
  svg.appendChild(fgCircle);

  el.appendChild(svg);

  // Center label
  const label = _el("span", {
    className: `pr-health-ring-label ${tier}`,
  });
  label.textContent = `${Math.round(pct)}%`;
  el.appendChild(label);

  return el;
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
  const el = _el("div", { className: "pr-empty" });

  const icon = _el("div", { className: "pr-empty-icon" });
  icon.textContent = "⊘";
  el.appendChild(icon);

  if (title) {
    const titleEl = _el("div", { className: "pr-empty-title" });
    titleEl.textContent = title;
    el.appendChild(titleEl);
  }

  if (message) {
    const msgEl = _el("div", { className: "pr-empty-message" });
    msgEl.textContent = message;
    el.appendChild(msgEl);
  }

  if (action) {
    const wrap = _el("div", { className: "pr-empty-action" });
    const btn = _el("button", {
      className: "btn-primary btn-sm",
      type: "button",
    });
    btn.textContent = action.label;
    btn.addEventListener("click", action.onClick);
    wrap.appendChild(btn);
    el.appendChild(wrap);
  }

  return el;
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
    const empty = _el("div", { className: "pr-heatmap" });
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

  const el = _el("div", { className: "pr-heatmap" });

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(w));
  svg.setAttribute("height", String(h));
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);

  // Column labels
  for (let c = 0; c < cols; c++) {
    if (c < colLabels.length) {
      const txt = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text"
      );
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
      const txt = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text"
      );
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
      // blue-ish intensity scale
      const intensity = Math.round(0.15 + normalized * 0.65);
      const hex = _intensityToHex(intensity);

      const rect = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "rect"
      );
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
      const title = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "title"
      );
      const rowLabel = rowLabels[r] || `row ${r}`;
      const colLabel = colLabels[c] || `col ${c}`;
      title.textContent = `${rowLabel}, ${colLabel}: ${v}`;
      rect.appendChild(title);

      svg.appendChild(rect);
    }
  }

  el.appendChild(svg);
  return el;
}