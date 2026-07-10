// ──────────────────────────────────────────────────────
// UI Primitives — Core — LKPR-126
// Design tokens and shared helpers.
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
export function hashColor(s) {
  if (!s) return "gray";
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) | 0;
  }
  return _NS_COLORS[Math.abs(hash) % _NS_COLORS.length];
}

export function scoreTier(score) {
  if (score == null) return "low";
  if (score >= DESIGN_TOKENS.score.highThreshold) return "high";
  if (score >= DESIGN_TOKENS.score.midThreshold) return "mid";
  return "low";
}

export function el(tag, attrs = {}, children = []) {
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