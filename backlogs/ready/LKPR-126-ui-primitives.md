---
id: LKPR-126
title: UI primitives library — ScorePill, NamespaceDot, RelationPill, FilterChip, SegmentedControl, ToggleSwitch, StatTile, HealthRing, EmptyState, HeatmapGrid
type: feature
sprint: ~
rice_score: ~
filed_by: Akane
filed_date: 2026-07-05
github_issue: 291
---

# [LKPR-126] UI primitives library — reusable dashboard components

## Key References

Read only when you need detailed information

- high level plan: docs/plans/dashboard-v2-epic.md
- visuals: design/visuals/\*
- mockups: design/mockups/\*
- design specification: design/Lorekeeper-Dashboard-v7-Design-Spec.md

## Problem

The dashboard's JS modules (health, memories, activity grid) each re-implement the same visual patterns — colored badges, toggleable chips, stat cards — with slightly different CSS and HTML. This leads to visual drift, duplicated code, and makes it harder to add new tabs or iterate on existing ones. There's no shared component library that ensures consistent rendering.

The spec (§2.3-2.5, §2.10) calls for a set of primitives that appear across multiple dashboard contexts. These need a single home with consistent design tokens.

## Solution

Build a `primitives.js` module exposing 10 reusable UI components. Each is a plain function that returns an HTMLElement or HTML string, taking a props/config object. No framework — just DOM API + a shared design-tokens module for colors and spacing.

### Component: ScorePill (§2.3)

A rounded pill showing a numeric score with background color based on threshold:

| Range | Background | Text  |
| ----- | ---------- | ----- |
| ≥ 7   | `#16a34a`  | white |
| 5-7   | `#d97706`  | white |
| < 5   | `#dc2626`  | white |

Props: `score` (number). Renders as a small inline pill, ~28px height, `border-radius: 9999px`, padding `2px 10px`, `font-size: 12px`, `font-weight: 600`.

### Component: NamespaceDot (§2.3)

An 8px × 8px colored circle representing a memory namespace.

Props: `namespace` (string). Color mapping via lookup table:

| Namespace | Color     |
| --------- | --------- |
| `code`    | `#3b82f6` |
| `user`    | `#8b5cf6` |
| `system`  | `#10b981` |
| `project` | `#f59e0b` |
| `concept` | `#ec4899` |
| _default_ | `#6b7280` |

Renders as a `<span>` with fixed 8px dimensions, `border-radius: 50%`.

### Component: RelationPill (§2.3)

A small pill label indicating a relationship type between two memories. Color per relation type:

| Relation type    | Background | Text      |
| ---------------- | ---------- | --------- |
| `references`     | `#dbeafe`  | `#1e40af` |
| `implements`     | `#dcfce7`  | `#166534` |
| `depends_on`     | `#fef3c7`  | `#92400e` |
| `conflicts_with` | `#fce7f3`  | `#9d174d` |
| `part_of`        | `#e0e7ff`  | `#3730a3` |
| _fallback_       | `#f3f4f6`  | `#374151` |

Props: `type` (string), `label` (optional string — defaults to readable version of type, e.g. `"conflicts_with"` → `"Conflicts With"`). Height ~24px, border-radius 9999px, padding `2px 10px`, font-size 11px, font-weight 500.

### Component: FilterChip (§2.4)

A toggleable chip that shows an active/inactive state and an optional count badge.

Props: `label` (string), `active` (boolean, default false), `count` (number, optional), `onToggle` (callback).

Inactive: gray border (`#d1d5db`), gray text (`#6b7280`), white background (`#ffffff`).
Active (spec §2.4): `#8b5cf6` border, `#8b5cf6` text (or white on filled), `#f5f3ff` background.

Count badge: when provided, shows small pill to the right of label with count number, same style as chip.

### Component: SegmentedControl (§2.5)

A pill-group of 2-3 buttons where exactly one is active. Renders as a horizontal segmented button row with rounded container.

Props: `options` (array of `{value, label}`), `value` (selected value), `onChange` (callback).

Container: `bg-gray-100`, `border-radius: 8px`, `padding: 2px`. Active tab: white background (`#ffffff`), purple text (`#8b5cf6`), font-weight 600. Inactive tabs: transparent background, gray-500 text. All tabs: `font-size: 13px`, `padding: 4px 14px`, `border-radius: 6px`.

### Component: ToggleSwitch (§2.5)

A boolean toggle rendered as a sliding switch. Purple when on, gray when off.

Props: `checked` (boolean), `onChange` (callback), `label` (optional string).

Track: `width: 36px`, `height: 20px`, `border-radius: 10px`. When on: background `#8b5cf6`. When off: background `#d1d5db`.
Thumb: `width: 16px`, `height: 16px`, `border-radius: 50%`, white. Slides to right when on (translate-x +16px). CSS transition on background and transform (150ms ease).

### Component: StatTile (§2.5)

A white card with an icon, a status pill, a large number, and a footer label. Used in the Health tab summary strip and dashboard overview.

Props: `icon` (SVG string or innerHTML), `value` (string — the large number), `label` (string — footer text), `statusPill` (optional `{text, color}` — small colored badge in top-right corner).

Container: white card, `border: 1px solid #e5e7eb`, `border-radius: 12px`, `padding: 16px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.05)`. Icon: 24×24, `#6b7280`. Value: `font-size: 28px`, `font-weight: 700`. Label: `font-size: 12px`, `color: #6b7280`.

### Component: HealthRing (§2.5)

An SVG donut chart showing a percentage/proportion. Used in Health tab for memory quality distribution.

Props: `percent` (0-100), `size` (number, default 60), `strokeWidth` (number, default 6), `color` (string, default `#8b5cf6`), `label` (optional string shown in center).

SVG: two `<circle>` elements. Background ring: stroke `#e5e7eb`. Foreground ring: `stroke-dasharray` computed from percent, `stroke-linecap: round`, `transform: rotate(-90deg)`, `transform-origin: center`. Center text: `font-size: 14px`, `font-weight: 700`, `fill: #111827`.

### Component: EmptyState (§2.10)

A centered panel with an icon and descriptive message. Used when search returns zero results or a tab has no data.

Props: `icon` (SVG string, optional), `title` (string), `message` (string), `action` (optional `{label, onClick}` — a button shown below the message).

Layout: `display: flex`, `flex-direction: column`, `align-items: center`, `justify-content: center`, `padding: 64px 24px`. Icon: 48×48, `#d1d5db`, margin-bottom 16px. Title: `font-size: 16px`, `font-weight: 600`, `color: #374151`. Message: `font-size: 14px`, `color: #6b7280`, margin-top 4px, max-width 360px, text-align center. Action button (if provided): primary purple button (`#8b5cf6`), margin-top 16px.

### Component: HeatmapGrid (§2.5)

A configurable grid cell chart where each cell's background intensity represents a value. Used in Health tab for the retention/decay heatmap.

Props: `data` (2D array `{value, tooltip}`), `rowLabels` (array of strings), `colLabels` (array of strings), `colorScale` (function `(value, max) => color`), `cellSize` (number, default 14), `gap` (number, default 2).

Renders as inline SVG or a `<table>` with styled `<td>` elements. Each cell: fixed width/height, `border-radius: 2px`. Background computed from `colorScale(value, maxValue)`. Cell with `value=0` gets `#f3f4f6` (very light gray). On hover: show tooltip text. Row labels: right-aligned, `font-size: 11px`, `color: #6b7280`, padding-right 6px. Col labels: centered, `font-size: 11px`, `color: #6b7280`, padding-bottom 4px. Optional color legend bar at top or bottom.

## Acceptance Criteria

- [ ] `static/js/primitives.js` exposes all 10 component functions as named exports
- [ ] Each component accepts a single props object and returns an `HTMLElement`
- [ ] ScorePill renders correct color for low / mid / high scores
- [ ] NamespaceDot renders correct color per namespace, fallback for unknown
- [ ] RelationPill renders correct color per relation type, fallback for unknown
- [ ] FilterChip toggles active state visually and fires `onToggle`
- [ ] SegmentedControl renders N options, highlights active, fires `onChange`
- [ ] ToggleSwitch renders on/off states with purple color, fires `onChange`
- [ ] StatTile renders icon, value, label, and optional status pill
- [ ] HealthRing renders SVG donut at the correct percentage
- [ ] EmptyState renders centered icon + title + message + optional action button
- [ ] HeatmapGrid renders N×M grid with intensity coloring and tooltips
- [ ] All primitives use design tokens from a shared `design-tokens.js` module (colors, spacing, font sizes)
- [ ] All colors match the exact hex values specified above

## Non-goals

- No framework dependency (no React, no Alpine, no jQuery)
- No CSS-in-JS — all styles are inline or via a single `primitives.css` file
- No accessibility scaffolding beyond basic `aria-label` — that's a follow-up
- No `HeatmapGrid` auto-scaling (responsive fallback like word-wrap is fine, not full responsive)

## Affected Files

**New:**

- `src/lorekeeper/dashboard/static/js/primitives.js` — component functions + design tokens
- `src/lorekeeper/dashboard/static/css/primitives.css` — shared styles for all components

**Modified:**

- `src/lorekeeper/dashboard/index.html` — remove any duplicated inline component styles in existing tabs where primitives.js is used

## Dependencies

_None_ — pure frontend JS/CSS. The existing dashboard architecture (vanilla JS modules, static files served by FastAPI) supports this without changes.

## Required Updates

- **CLAUDE.md**: [ ] Add `static/js/primitives.js` to project map under "Dashboard JS"
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A

## Notes

These components are referenced by LKPR-129 (Memories page) and LKPR-88 (Health tab). Consumers should import from `primitives.js` rather than reimplementing.

The design-tokens approach follows an informal convention already emerging in the codebase. A single `DESIGN_TOKENS` export in `primitives.js` keeps colors, spacing, and font sizes in one place.

## Next

**LKPR-127** — Memory Detail Drawer (view + edit modes)
