// ── LKPR-126: UI Primitives Tests ──
import { describe, it, expect, vi } from "vitest";
import {
  DESIGN_TOKENS,
  ScorePill,
  NamespaceDot,
  RelationPill,
  FilterChip,
  SegmentedControl,
  ToggleSwitch,
  StatTile,
  HealthRing,
  EmptyState,
  HeatmapGrid,
} from "./primitives.js";

// ── DESIGN_TOKENS ──

describe("DESIGN_TOKENS", () => {
  it("exports expected shape", () => {
    expect(DESIGN_TOKENS).toBeDefined();
    expect(DESIGN_TOKENS.colors).toBeDefined();
    expect(DESIGN_TOKENS.colors.primary).toBe("var(--primary)");
    expect(DESIGN_TOKENS.score.highThreshold).toBe(7);
    expect(DESIGN_TOKENS.score.midThreshold).toBe(5);
  });
});

// ── ScorePill ──

describe("ScorePill", () => {
  it("returns a span with pr-score-pill class", () => {
    const el = ScorePill({ score: 8 });
    expect(el.tagName).toBe("SPAN");
    expect(el.classList.contains("pr-score-pill")).toBe(true);
  });

  it("applies 'high' class for score >= 7", () => {
    expect(ScorePill({ score: 10 }).classList.contains("high")).toBe(true);
    expect(ScorePill({ score: 7 }).classList.contains("high")).toBe(true);
    expect(ScorePill({ score: 7 }).textContent).toBe("7");
  });

  it("applies 'mid' class for score 5-6", () => {
    const el = ScorePill({ score: 6 });
    expect(el.classList.contains("mid")).toBe(true);
    expect(el.textContent).toBe("6");
  });

  it("applies 'low' class for score < 5", () => {
    const el = ScorePill({ score: 3 });
    expect(el.classList.contains("low")).toBe(true);
    expect(el.textContent).toBe("3");
  });

  it("handles null/undefined gracefully", () => {
    const el = ScorePill({ score: null });
    expect(el.classList.contains("low")).toBe(true);
    expect(el.textContent).toBe("\u2014");
  });

  it("rounds scores", () => {
    expect(ScorePill({ score: 7.8 }).textContent).toBe("8");
  });

  it("clamps out-of-range scores", () => {
    expect(ScorePill({ score: -5 }).textContent).toBe("0");
    expect(ScorePill({ score: 50 }).textContent).toBe("10");
  });
});

// ── NamespaceDot ──

describe("NamespaceDot", () => {
  it("returns a span with pr-ns-dot class", () => {
    const el = NamespaceDot({ namespace: "core" });
    expect(el.tagName).toBe("SPAN");
    expect(el.classList.contains("pr-ns-dot")).toBe(true);
  });

  it("sets data-color attribute deterministically", () => {
    const el1 = NamespaceDot({ namespace: "core" });
    const el2 = NamespaceDot({ namespace: "core" });
    expect(el1.dataset.color).toBe(el2.dataset.color);
  });

  it("shows the namespace text", () => {
    expect(NamespaceDot({ namespace: "user" }).textContent).toBe("user");
  });

  it("handles empty/null namespace", () => {
    const el = NamespaceDot({ namespace: null });
    expect(el.textContent).toBe("\u2014");
    expect(el.dataset.color).toBe("gray");
  });
});

// ── RelationPill ──

describe("RelationPill", () => {
  it("returns a span with pr-rel-pill class", () => {
    const el = RelationPill({ type: "auto_linked" });
    expect(el.tagName).toBe("SPAN");
    expect(el.classList.contains("pr-rel-pill")).toBe(true);
  });

  it("replaces underscores with spaces in display text", () => {
    expect(RelationPill({ type: "auto_linked" }).textContent).toBe("auto linked");
    expect(RelationPill({ type: "related_to" }).textContent).toBe("related to");
  });

  it("sets data-type attribute", () => {
    expect(RelationPill({ type: "used_in" }).dataset.type).toBe("used_in");
  });

  it("defaults to 'default' for unknown types", () => {
    const el = RelationPill({ type: "unknown_type" });
    expect(el.dataset.type).toBe("unknown_type");
    expect(el.textContent).toBe("unknown type");
  });

  it("handles null/undefined type", () => {
    const el = RelationPill({ type: null });
    expect(el.dataset.type).toBe("default");
    expect(el.textContent).toBe("default");
  });
});

// ── FilterChip ──

describe("FilterChip", () => {
  it("returns a button with pr-filter-chip class", () => {
    const el = FilterChip({ label: "All" });
    expect(el.tagName).toBe("BUTTON");
    expect(el.classList.contains("pr-filter-chip")).toBe(true);
  });

  it("shows label text", () => {
    expect(FilterChip({ label: "Active" }).textContent).toBe("Active");
  });

  it("applies active class when active=true", () => {
    const el = FilterChip({ label: "X", active: true });
    expect(el.classList.contains("active")).toBe(true);
  });

  it("does not apply active class when active=false", () => {
    const el = FilterChip({ label: "X", active: false });
    expect(el.classList.contains("active")).toBe(false);
  });

  it("shows count badge when count is provided", () => {
    const el = FilterChip({ label: "X", count: 42 });
    const badge = el.querySelector(".pr-filter-chip-count");
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe("42");
  });

  it("does not show badge when count is omitted", () => {
    const el = FilterChip({ label: "X" });
    expect(el.querySelector(".pr-filter-chip-count")).toBeNull();
  });

  it("toggles active class and calls onToggle on click", () => {
    const onToggle = vi.fn();
    const el = FilterChip({ label: "X", active: false, onToggle });
    el.click();
    expect(el.classList.contains("active")).toBe(true);
    expect(onToggle).toHaveBeenCalledWith(true);
    el.click();
    expect(onToggle).toHaveBeenCalledWith(false);
  });
});

// ── SegmentedControl ──

describe("SegmentedControl", () => {
  const options = [
    { label: "All", value: "" },
    { label: "Today", value: "0" },
    { label: "3d", value: "3" },
  ];

  it("returns a div with pr-segmented class", () => {
    const el = SegmentedControl({ options, value: "" });
    expect(el.tagName).toBe("DIV");
    expect(el.classList.contains("pr-segmented")).toBe(true);
  });

  it("renders one button per option", () => {
    const el = SegmentedControl({ options, value: "" });
    const btns = el.querySelectorAll(".pr-seg-opt");
    expect(btns.length).toBe(3);
  });

  it("marks the selected option as active", () => {
    const el = SegmentedControl({ options, value: "3" });
    const btns = el.querySelectorAll(".pr-seg-opt");
    expect(btns[0].classList.contains("active")).toBe(false);
    expect(btns[2].classList.contains("active")).toBe(true);
  });

  it("calls onChange with new value on click", () => {
    const onChange = vi.fn();
    const el = SegmentedControl({ options, value: "", onChange });
    const btns = el.querySelectorAll(".pr-seg-opt");
    btns[2].click();
    expect(onChange).toHaveBeenCalledWith("3");
    expect(btns[2].classList.contains("active")).toBe(true);
    expect(btns[0].classList.contains("active")).toBe(false);
  });

  it("does not fire onChange when clicking already-active option", () => {
    const onChange = vi.fn();
    const el = SegmentedControl({ options, value: "0", onChange });
    el.querySelectorAll(".pr-seg-opt")[1].click();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("handles empty options", () => {
    const el = SegmentedControl({ options: [], value: "" });
    expect(el.children.length).toBe(0);
  });
});

// ── ToggleSwitch ──

describe("ToggleSwitch", () => {
  it("returns a label with pr-toggle class", () => {
    const el = ToggleSwitch({});
    expect(el.tagName).toBe("LABEL");
    expect(el.classList.contains("pr-toggle")).toBe(true);
  });

  it("applies 'on' class when checked=true", () => {
    const el = ToggleSwitch({ checked: true });
    expect(el.classList.contains("on")).toBe(true);
  });

  it("does not apply 'on' class when checked=false", () => {
    const el = ToggleSwitch({ checked: false });
    expect(el.classList.contains("on")).toBe(false);
  });

  it("shows label text when provided", () => {
    const el = ToggleSwitch({ label: "Include deleted" });
    expect(el.textContent).toContain("Include deleted");
  });

  it("calls onChange with checked state on toggle", () => {
    const onChange = vi.fn();
    const el = ToggleSwitch({ checked: false, onChange });
    const input = el.querySelector("input");
    input.checked = true;
    input.dispatchEvent(new Event("change"));
    expect(onChange).toHaveBeenCalledWith(true);
    expect(el.classList.contains("on")).toBe(true);
  });

  it("contains a hidden checkbox input", () => {
    const el = ToggleSwitch({ checked: true });
    const input = el.querySelector("input.pr-toggle-input");
    expect(input).not.toBeNull();
    expect(input.type).toBe("checkbox");
    expect(input.checked).toBe(true);
  });
});

// ── StatTile ──

describe("StatTile", () => {
  it("returns a div with pr-stat-tile class", () => {
    const el = StatTile({ value: "42", label: "memories" });
    expect(el.tagName).toBe("DIV");
    expect(el.classList.contains("pr-stat-tile")).toBe(true);
  });

  it("shows value and label", () => {
    const el = StatTile({ value: "128", label: "Total" });
    const valEl = el.querySelector(".pr-stat-tile-value");
    const lblEl = el.querySelector(".pr-stat-tile-label");
    expect(valEl.textContent).toBe("128");
    expect(lblEl.textContent).toBe("Total");
  });

  it("shows icon when provided", () => {
    const el = StatTile({ icon: "\uD83D\uDCCA", value: "5", label: "tests" });
    const iconEl = el.querySelector(".pr-stat-tile-icon");
    expect(iconEl.textContent).toBe("\uD83D\uDCCA");
  });

  it("handles SVG icon string", () => {
    const el = StatTile({
      icon: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>',
      iconIsSvg: true,
      value: "10",
      label: "items",
    });
    const iconEl = el.querySelector(".pr-stat-tile-icon");
    expect(iconEl.querySelector("svg")).not.toBeNull();
  });

  it("shows status pill when provided", () => {
    const el = StatTile({
      value: "85",
      label: "health",
      statusPill: { score: 8, label: "good" },
    });
    const statusEl = el.querySelector(".pr-stat-tile-status");
    expect(statusEl).not.toBeNull();
    expect(statusEl.textContent).toContain("good");
    const pill = statusEl.querySelector(".pr-score-pill");
    expect(pill).not.toBeNull();
  });

  it("handles missing value with fallback", () => {
    const el = StatTile({ value: null, label: "test" });
    const valEl = el.querySelector(".pr-stat-tile-value");
    expect(valEl.textContent).toBe("\u2014");
  });
});

// ── HealthRing ──

describe("HealthRing", () => {
  it("returns a div with pr-health-ring class", () => {
    const el = HealthRing({ percent: 75 });
    expect(el.tagName).toBe("DIV");
    expect(el.classList.contains("pr-health-ring")).toBe(true);
  });

  it("renders SVG with two circles", () => {
    const el = HealthRing({ percent: 50 });
    const svg = el.querySelector("svg");
    expect(svg).not.toBeNull();
    const circles = svg.querySelectorAll("circle");
    expect(circles.length).toBe(2);
  });

  it("shows percent label", () => {
    const el = HealthRing({ percent: 75 });
    const label = el.querySelector(".pr-health-ring-label");
    expect(label.textContent).toBe("75%");
  });

  it("applies 'high' class for percent >= 70", () => {
    const el = HealthRing({ percent: 80 });
    const label = el.querySelector(".pr-health-ring-label");
    expect(label.classList.contains("high")).toBe(true);
  });

  it("applies 'mid' class for percent 50-69", () => {
    const el = HealthRing({ percent: 60 });
    const label = el.querySelector(".pr-health-ring-label");
    expect(label.classList.contains("mid")).toBe(true);
  });

  it("applies 'low' class for percent < 50", () => {
    const el = HealthRing({ percent: 30 });
    const label = el.querySelector(".pr-health-ring-label");
    expect(label.classList.contains("low")).toBe(true);
  });

  it("clamps percent to 0-100", () => {
    const el1 = HealthRing({ percent: -10 });
    const el2 = HealthRing({ percent: 150 });
    expect(el1.querySelector(".pr-health-ring-label").textContent).toBe("0%");
    expect(el2.querySelector(".pr-health-ring-label").textContent).toBe("100%");
  });

  it("handles zero percent", () => {
    const el = HealthRing({ percent: 0 });
    expect(el.querySelector(".pr-health-ring-label").textContent).toBe("0%");
  });
});

// ── EmptyState ──

describe("EmptyState", () => {
  it("returns a div with pr-empty class", () => {
    const el = EmptyState({});
    expect(el.tagName).toBe("DIV");
    expect(el.classList.contains("pr-empty")).toBe(true);
  });

  it("shows title when provided", () => {
    const el = EmptyState({ title: "No results" });
    const titleEl = el.querySelector(".pr-empty-title");
    expect(titleEl).not.toBeNull();
    expect(titleEl.textContent).toBe("No results");
  });

  it("shows message when provided", () => {
    const el = EmptyState({ message: "Try a different filter" });
    const msgEl = el.querySelector(".pr-empty-message");
    expect(msgEl).not.toBeNull();
    expect(msgEl.textContent).toBe("Try a different filter");
  });

  it("renders action button when action is provided", () => {
    const onClick = vi.fn();
    const el = EmptyState({
      title: "Empty",
      message: "Nothing here",
      action: { label: "Refresh", onClick },
    });
    const btn = el.querySelector(".pr-empty-action button");
    expect(btn).not.toBeNull();
    expect(btn.textContent).toBe("Refresh");
    btn.click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not render action section when action is omitted", () => {
    const el = EmptyState({ title: "Empty" });
    expect(el.querySelector(".pr-empty-action")).toBeNull();
  });

  it("always shows an icon", () => {
    const el = EmptyState({});
    const icon = el.querySelector(".pr-empty-icon");
    expect(icon).not.toBeNull();
  });
});

// ── HeatmapGrid ──

describe("HeatmapGrid", () => {
  it("returns a div with pr-heatmap class", () => {
    const el = HeatmapGrid({
      data: [[1, 2], [3, 4]],
    });
    expect(el.tagName).toBe("DIV");
    expect(el.classList.contains("pr-heatmap")).toBe(true);
  });

  it("renders SVG with correct number of cells", () => {
    const el = HeatmapGrid({
      data: [[1, 2, 3], [4, 5, 6]],
    });
    const rects = el.querySelectorAll("rect");
    expect(rects.length).toBe(6);
  });

  it("shows row and column labels", () => {
    const el = HeatmapGrid({
      data: [[1, 2], [3, 4]],
      rowLabels: ["A", "B"],
      colLabels: ["X", "Y"],
    });
    const texts = el.querySelectorAll("text");
    expect(texts.length).toBeGreaterThanOrEqual(4);
    const textContents = Array.from(texts).map((t) => t.textContent);
    expect(textContents).toContain("A");
    expect(textContents).toContain("B");
    expect(textContents).toContain("X");
    expect(textContents).toContain("Y");
  });

  it("returns fallback text for empty data", () => {
    const el = HeatmapGrid({ data: [] });
    expect(el.textContent).toBe("No data");
  });

  it("returns fallback for data with empty rows", () => {
    const el = HeatmapGrid({ data: [[]] });
    expect(el.textContent).toBe("No data");
  });

  it("renders cells with tooltip titles", () => {
    const el = HeatmapGrid({
      data: [[42]],
      rowLabels: ["R1"],
      colLabels: ["C1"],
    });
    const rect = el.querySelector("rect");
    const title = rect.querySelector("title");
    expect(title).not.toBeNull();
    expect(title.textContent).toContain("42");
  });
});

// ── Integration: all components return HTMLElement ──

describe("All components return HTMLElement", () => {
  const cases = [
    ["ScorePill", () => ScorePill({ score: 5 })],
    ["NamespaceDot", () => NamespaceDot({ namespace: "test" })],
    ["RelationPill", () => RelationPill({ type: "auto_linked" })],
    ["FilterChip", () => FilterChip({ label: "test" })],
    [
      "SegmentedControl",
      () =>
        SegmentedControl({
          options: [{ label: "A", value: "a" }],
          value: "a",
        }),
    ],
    ["ToggleSwitch", () => ToggleSwitch({})],
    ["StatTile", () => StatTile({ value: "1", label: "t" })],
    ["HealthRing", () => HealthRing({ percent: 50 })],
    ["EmptyState", () => EmptyState({})],
    ["HeatmapGrid", () => HeatmapGrid({ data: [[1]] })],
  ];

  for (const [name, fn] of cases) {
    it(`${name} returns an HTMLElement`, () => {
      const el = fn();
      expect(el instanceof HTMLElement).toBe(true);
    });
  }
});