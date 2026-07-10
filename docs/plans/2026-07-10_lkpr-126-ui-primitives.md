# Plan: LKPR-126 — UI Primitives Library

**Ticket:** `backlogs/ready/LKPR-126-ui-primitives.md` (GH #291)
**Branch:** `feat/LKPR-126-ui-primitives`
**Target:** existing dashboard (`src/lorekeeper/dashboard/static/`)

---

## Summary

Create 10 vanilla JS/CSS UI primitives for the existing dashboard. Each is a pure function that returns an `HTMLElement` (no innerHTML — see BLOCKER Pattern 25). All colors and spacing are driven by a single `DESIGN_TOKENS` export.

---

## Files to Create

### New: `static/js/primitives.js`

Named exports from one module:

| Export                    | Purpose                                           |
| ------------------------- | ------------------------------------------------- |
| `DESIGN_TOKENS`           | Shared colors, spacing, font sizes                |
| `ScorePill(props)`        | Rounded score badge, colored by threshold         |
| `NamespaceDot(props)`     | 8px colored circle per namespace                  |
| `RelationPill(props)`     | Colored pill per relation type                    |
| `FilterChip(props)`       | Toggleable chip with optional count badge         |
| `SegmentedControl(props)` | N-button pill group, one active                   |
| `ToggleSwitch(props)`     | Sliding boolean switch, purple when on            |
| `StatTile(props)`         | White card with icon, value, label, status pill   |
| `HealthRing(props)`       | SVG donut chart at given percentage               |
| `EmptyState(props)`       | Centered icon + title + message + optional action |
| `HeatmapGrid(props)`      | N×M intensity grid with tooltips                  |

### New: `static/css/primitives.css`

Shared styles for all components. Exported via a `<link>` in `index.html`.

---

## Key Decisions

1. **HTMLElement, not innerHTML** — BLOCKER Pattern 25 requires all components to return `HTMLElement` and use `.textContent` for dynamic text. No `innerHTML` assignment from API data.
2. **DESIGN_TOKENS in primitives.js** — single `const` object keeps colors, spacing, font sizes. Components reference these by key, not by hardcoded hex.
3. **primitives.css for structural styles** — component dimensions, border-radius, transitions, hover states. Dynamic colors (score thresholds, namespace colors) set via inline style from DESIGN_TOKENS.
4. **No framework** — pure DOM API. No React, Alpine, or jQuery.
5. **Score threshold** — use the ticket's thresholds (≥7 green, 5-7 amber, <5 red), not the design spec's light-bg variant. The ticket is the AC.
6. **index.html**: no duplicated inline styles to remove yet (LKPR-129/88 consumers aren't built). Add `<link rel="stylesheet" href="css/primitives.css">` to `<head>`.

---

## Component Details

### ScorePill

- Props: `{ score: number }`
- Thresholds: ≥7 → `#16a34a` bg, white text; 5-7 → `#d97706` bg, white text; <5 → `#dc2626` bg, white text
- Style: `border-radius: 9999px`, `padding: 2px 10px`, `font-size: 12px`, `font-weight: 600`, inline-block
- Returns `<span>` element

### NamespaceDot

- Props: `{ namespace: string }`
- Colors: `code:#3b82f6`, `user:#8b5cf6`, `system:#10b981`, `project:#f59e0b`, `concept:#ec4899`, default:`#6b7280`
- Style: 8×8px, `border-radius: 50%`, inline-block
- Returns `<span>` element

### RelationPill

- Props: `{ type: string, label?: string }`
- Colors: `references:#dbeafe/#1e40af`, `implements:#dcfce7/#166534`, `depends_on:#fef3c7/#92400e`, `conflicts_with:#fce7f3/#9d174d`, `part_of:#e0e7ff/#3730a3`, fallback:`#f3f4f6/#374151`
- Style: `height: 24px`, `border-radius: 9999px`, `padding: 2px 10px`, `font-size: 11px`, `font-weight: 500`
- Label defaults to readable version of type (e.g. `conflicts_with` → `Conflicts With`)
- Returns `<span>` element

### FilterChip

- Props: `{ label, active?: boolean, count?: number, onToggle?: (active: boolean) => void }`
- Inactive: `#d1d5db` border, `#6b7280` text, `#ffffff` bg
- Active: `#8b5cf6` border, `#8b5cf6` text, `#f5f3ff` bg
- Count badge: small pill to right of label when provided
- Returns `<button>` element, calls `onToggle` on click

### SegmentedControl

- Props: `{ options: {value, label}[], value, onChange: (value) => void }`
- Container: `bg: #f3f4f6`, `border-radius: 8px`, `padding: 2px`, inline-flex
- Active tab: white bg, `#8b5cf6` text, `font-weight: 600`
- Inactive: transparent bg, `#6b7280` text
- All tabs: `font-size: 13px`, `padding: 4px 14px`, `border-radius: 6px`
- Returns `<div>` element

### ToggleSwitch

- Props: `{ checked: boolean, onChange: (checked: boolean) => void, label?: string }`
- Track: 36×20px, `border-radius: 10px`. On: `#8b5cf6`. Off: `#d1d5db`
- Thumb: 16×16px, `border-radius: 50%`, white. Slides +16px when on
- CSS transition 150ms ease on background and transform
- Returns `<label>` element wrapping the track + optional label text

### StatTile

- Props: `{ icon: string, value: string, label: string, statusPill?: {text, color} }`
- Container: white card, `border: 1px solid #e5e7eb`, `border-radius: 12px`, `padding: 16px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.05)`
- Icon: 24×24, `#6b7280`. Value: `font-size: 28px`, `font-weight: 700`. Label: `font-size: 12px`, `color: #6b7280`
- Status pill: small colored badge in top-right corner
- Returns `<div>` element. Icon is rendered as innerHTML (static SVG string, not API data — safe per the XSS gate)

### HealthRing

- Props: `{ percent: 0-100, size?: number, strokeWidth?: number, color?: string, label?: string }`
- SVG: two `<circle>` elements. Background: stroke `#e5e7eb`. Foreground: `stroke-dasharray` from percent, `stroke-linecap: round`, `transform: rotate(-90deg)`
- Center text: `font-size: 14px`, `font-weight: 700`, `fill: #111827`
- Returns `<svg>` element

### EmptyState

- Props: `{ icon?: string, title: string, message: string, action?: {label, onClick} }`
- Layout: flex column, center, `padding: 64px 24px`
- Icon: 48×48, `#d1d5db`, margin-bottom 16px
- Title: `font-size: 16px`, `font-weight: 600`, `color: #374151`
- Message: `font-size: 14px`, `color: #6b7280`, max-width 360px, text-align center
- Action button: primary purple (`#8b5cf6`), margin-top 16px
- Returns `<div>` element. Icon rendered as innerHTML (static SVG, not API data)

### HeatmapGrid

- Props: `{ data: {value, tooltip}[][], rowLabels: string[], colLabels: string[], colorScale?: (value, max) => color, cellSize?: number, gap?: number }`
- Renders as inline SVG: rects for cells, text for labels
- Cell bg from `colorScale(value, maxValue)`. Value=0 gets `#f3f4f6`
- Hover tooltip via `<title>` element
- Row labels: right-aligned, `font-size: 11px`, `color: #6b7280`
- Col labels: centered, `font-size: 11px`, `color: #6b7280`
- Optional color legend bar
- Returns `<svg>` element

---

## Modified Files

### `static/index.html`

- Add `<link rel="stylesheet" href="css/primitives.css">` to `<head>`

---

## Non-Goals (from ticket)

- No framework dependency
- No CSS-in-JS
- No accessibility scaffolding beyond basic `aria-label`
- No HeatmapGrid auto-scaling

## Stale Ticket Correction

- Ticket says `src/lorekeeper/dashboard/index.html` → actual path is `static/index.html`
- BLOCKER Pattern 25 overrides ticket's "or HTML string" — ALL components MUST return `HTMLElement`

---

## Build Order

1. Write `DESIGN_TOKENS` export in `primitives.js`
2. Write `primitives.css`
3. Implement each component in order: ScorePill → NamespaceDot → RelationPill → FilterChip → SegmentedControl → ToggleSwitch → StatTile → HealthRing → EmptyState → HeatmapGrid
4. Wire `primitives.css` into `index.html`
5. Write tests in `tests/test_dashboard.py` (or a new `tests/test_primitives.py` if warranted)
6. Self-review loop
7. Commit, push, PR
