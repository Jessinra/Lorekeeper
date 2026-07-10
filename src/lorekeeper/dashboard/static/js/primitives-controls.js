// ──────────────────────────────────────────────────────
// UI Primitives — Interactive Controls — LKPR-126
// Form-like interactive elements: FilterChip, SegmentedControl, ToggleSwitch.
// ──────────────────────────────────────────────────────

import { el } from "./primitives-core.js";

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
  const chip = el("button", {
    className: `pr-filter-chip${active ? " active" : ""}`,
    type: "button",
  });
  chip.textContent = label;

  if (count != null) {
    const badge = el("span", { className: "pr-filter-chip-count" });
    badge.textContent = String(count);
    chip.appendChild(badge);
  }

  chip.addEventListener("click", () => {
    const next = !chip.classList.contains("active");
    chip.classList.toggle("active", next);
    if (onToggle) onToggle(next);
  });

  return chip;
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
  const group = el("div", { className: "pr-segmented" });

  for (const opt of options) {
    const btn = el("button", {
      className: `pr-seg-opt${opt.value === value ? " active" : ""}`,
      type: "button",
    });
    btn.textContent = opt.label;

    btn.addEventListener("click", () => {
      if (btn.classList.contains("active")) return;
      group.querySelectorAll(".pr-seg-opt").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      if (onChange) onChange(opt.value);
    });

    group.appendChild(btn);
  }

  return group;
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
  const toggle = el("label", { className: `pr-toggle${checked ? " on" : ""}` });

  const track = el("span", { className: "pr-toggle-track" });
  const input = el("input", {
    className: "pr-toggle-input",
    type: "checkbox",
  });
  input.checked = checked;

  input.addEventListener("change", () => {
    toggle.classList.toggle("on", input.checked);
    if (onChange) onChange(input.checked);
  });

  track.appendChild(input);
  toggle.appendChild(track);

  if (label != null) {
    const labelSpan = el("span");
    labelSpan.textContent = label;
    toggle.appendChild(labelSpan);
  }

  return toggle;
}