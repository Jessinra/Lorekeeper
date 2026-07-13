---
name: ui-ux-pro-max
description: "UI/UX design intelligence. 67 styles, 96 palettes, 57 font pairings, 25 charts, 13 stacks (React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, mobile app, .html, .tsx, .vue, .svelte. Elements: button, modal, navbar, sidebar, card, table, form, chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, flat design. Topics: color palette, accessibility, animation, layout, typography, font pairing, spacing, hover, shadow, gradient. Integrations: shadcn/ui MCP for component search and examples."
version: v1.0.0
---

# UI/UX Pro Max - Design Intelligence

Comprehensive design guide for web and mobile applications. Contains 67 styles, 96 color palettes, 57 font pairings, 99 UX guidelines, and 25 chart types across 13 technology stacks.

## When to Apply

- Designing new UI components or pages
- Choosing color palettes and typography
- Reviewing code for UX issues
- Building landing pages or dashboards
- Implementing accessibility requirements

## Rule Categories by Priority

| Priority | Category            | Impact   | Domain                |
| -------- | ------------------- | -------- | --------------------- |
| 1        | Accessibility       | CRITICAL | `ux`                  |
| 2        | Touch & Interaction | CRITICAL | `ux`                  |
| 3        | Performance         | HIGH     | `ux`                  |
| 4        | Layout & Responsive | HIGH     | `ux`                  |
| 5        | Typography & Color  | MEDIUM   | `typography`, `color` |
| 6        | Animation           | MEDIUM   | `ux`                  |
| 7        | Style Selection     | MEDIUM   | `style`, `product`    |
| 8        | Charts & Data       | LOW      | `chart`               |

## Quick Reference

### 1. Accessibility (CRITICAL)

- `color-contrast` — Minimum 4.5:1 ratio for normal text
- `focus-states` — Visible focus rings on interactive elements
- `alt-text` — Descriptive alt text for meaningful images
- `aria-labels` — aria-label for icon-only buttons
- `keyboard-nav` — Tab order matches visual order
- `form-labels` — Use label with for attribute

### 2. Touch & Interaction (CRITICAL)

- `touch-target-size` — Minimum 44x44px touch targets
- `hover-vs-tap` — Use click/tap for primary interactions
- `loading-buttons` — Disable button during async operations
- `error-feedback` — Clear error messages near problem
- `cursor-pointer` — Add cursor-pointer to clickable elements

### 3. Performance (HIGH)

- `image-optimization` — Use WebP, srcset, lazy loading
- `reduced-motion` — Check prefers-reduced-motion
- `content-jumping` — Reserve space for async content

### 4. Layout & Responsive (HIGH)

- `viewport-meta` — width=device-width initial-scale=1
- `readable-font-size` — Minimum 16px body text on mobile
- `horizontal-scroll` — Ensure content fits viewport width
- `z-index-management` — Define z-index scale (10, 20, 30, 50)

### 5. Typography & Color (MEDIUM)

- `line-height` — Use 1.5-1.75 for body text
- `line-length` — Limit to 65-75 characters per line
- `font-pairing` — Match heading/body font personalities

### 6. Animation (MEDIUM)

- `duration-timing` — Use 150-300ms for micro-interactions
- `transform-performance` — Use transform/opacity, not width/height
- `loading-states` — Skeleton screens or spinners

### 7. Style Selection (MEDIUM)

- `style-match` — Match style to product type
- `consistency` — Use same style across all pages
- `no-emoji-icons` — Use SVG icons, not emojis

### 8. Charts & Data (LOW)

- `chart-type` — Match chart type to data type
- `color-guidance` — Use accessible color palettes
- `data-table` — Provide table alternative for accessibility

---

## How to Use

### Step 1: Analyze Requirements

Extract: product type, style keywords, industry, stack (default: `html-tailwind`).

### Step 2: Generate Design System (REQUIRED)

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<product_type> <industry> <keywords>" --design-system [-p "Project Name"]
```

### Step 2b: Persist Design System

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" [--page "dashboard"]
```

Creates `design-system/MASTER.md` and `design-system/pages/<page>.md` for hierarchical retrieval.

### Step 3: Supplement with Detailed Searches

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --domain <domain> [-n <max_results>]
```

| Need                  | Domain       | Example                                 |
| --------------------- | ------------ | --------------------------------------- |
| More style options    | `style`      | `--domain style "glassmorphism dark"`   |
| Chart recommendations | `chart`      | `--domain chart "real-time dashboard"`  |
| UX best practices     | `ux`         | `--domain ux "animation accessibility"` |
| Alternative fonts     | `typography` | `--domain typography "elegant luxury"`  |
| Landing structure     | `landing`    | `--domain landing "hero social-proof"`  |

### Step 4: Stack Guidelines

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<keyword>" --stack <stack>
```

---

## Available Domains

`product`, `style`, `typography`, `color`, `landing`, `chart`, `ux`, `react`, `web`, `prompt`

## Available Stacks

| Stack             | Focus                                |
| ----------------- | ------------------------------------ |
| `html-tailwind`   | Tailwind, responsive, a11y (DEFAULT) |
| `react`           | State, hooks, performance            |
| `nextjs`          | SSR, routing, images                 |
| `vue`             | Composition API, Pinia               |
| `svelte`          | Runes, stores, SvelteKit             |
| `swiftui`         | Views, State, Animation              |
| `react-native`    | Components, Navigation               |
| `flutter`         | Widgets, State, Theming              |
| `shadcn`          | shadcn/ui components, forms          |
| `jetpack-compose` | Composables, Modifiers               |

## Output Formats

```bash
# ASCII box (default) — best for terminal
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system

# Markdown — best for documentation
python3 skills/ui-ux-pro-max/scripts/search.py "fintech crypto" --design-system -f markdown
```

## Tips for Better Results

1. **Be specific with keywords** — "healthcare SaaS dashboard" > "app"
2. **Search multiple times** — Different keywords reveal different insights
3. **Combine domains** — Style + Typography + Color = Complete design system
4. **Always check UX** — Search "animation", "z-index", "accessibility" for common issues
5. **Use stack flag** — Get implementation-specific best practices
6. **Iterate** — If first search doesn't match, try different keywords

## Common Rules & Pre-Delivery Checklist

See `references/common-rules.md` for professional UI rules (icons, hover, contrast, layout).
See `references/pre-delivery-checklist.md` for the pre-delivery verification checklist.
See `references/example-workflow.md` for a complete workflow example.
