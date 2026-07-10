---
applyTo: "src/lorekeeper/dashboard/static/js/primitives.js"
---

# Dashboard UI Primitives — Architecture & Code Convention

These rules govern the `primitives.js` library — the reusable vanilla JS component collection for the Lorekeeper dashboard. Every component function must follow these rules.

---

## Reusability

Each component is a **pure function** that returns an `HTMLElement`. No framework, no side effects, no shared mutable state.

- **One export per component function** — named export, PascalCase (`ScorePill`, `FilterChip`).
- **Single options object parameter** — destructure named keys at the top of the function ([`FilterChip({ label, active, count, onToggle })`](https://github.com/user-attachments/files/...)).
- **No cross-component state sharing** — any event callbacks are injected via the options object (e.g., `onToggle`, `onChange`).
- **No class-based components** — use functions returning `HTMLElement`. No `this`, no `new`, no prototype.
- **`_el(tag, attrs, children)` is the sole DOM builder** — never use `document.createElement()` directly. The `_el` helper handles `className`, `dataset`, text children, and `Node` children uniformly.

### BLOCKER: No innerHTML for dynamic content

- `innerHTML` is **forbidden** for any content that contains user data, API responses, or dynamic strings.
- Use `.textContent` exclusively for text content.
- **Exception**: Static SVG icon strings (predefined, not user-derived) may use `innerHTML`, but only when the caller is the same module and the strings are constants. The `StatTile` icon parameter is the only permitted case.

---

## Constants & Design Tokens

All shared config values live in a single `DESIGN_TOKENS` export at the top of `primitives.js`.

### DESIGN_TOKENS structure

```js
export const DESIGN_TOKENS = {
  colors: {
    /* CSS custom property references */
  },
  radius: "var(--radius)",
  transition: "var(--t)",
  font: {
    /* font stacks */
  },
  score: { highThreshold: 7, midThreshold: 5 },
};
```

### Rules

- **Score thresholds must read from `DESIGN_TOKENS.score`** — never hardcode `7` or `5` in component logic. Use `_scoreTier()` which reads from `DESIGN_TOKENS`.
- **CSS custom properties for colors** — `var(--primary)`, `var(--success)`, etc. Never hardcode hex values in JS. CSS files may use hardcoded values for static decoration (namespaced dot colors, relation pill backgrounds) but these should be considered for tokenization in future.
- **Module-level constants** — use `const` with `_` prefix for private module constants (`_CELL_S`, `_RING_R`, `_GAP`). Define them **before** the function that uses them.
- **No magic numbers in component logic** — spacing, dimensions, thresholds must be named constants. Exception: trivial offsets (padding of 1-2px in layout calculations) are acceptable with a comment.

---

## Separation of Logic from Config

### Layering (within a single file)

```
┌─────────────────────────────────────┐
│  DESIGN_TOKENS                       │ ← Config
├─────────────────────────────────────┤
│  Private helpers (_el, _scoreTier)   │ ← Shared logic
├─────────────────────────────────────┤
│  Component functions (ScorePill, …) │ ← Presentation logic
└─────────────────────────────────────┘
```

- **Config** (`DESIGN_TOKENS`) — thresholds, colors (as CSS vars), font stacks, dimensions. Pure data, no logic.
- **Logic** — `_scoreTier()`, `_hashColor()`, `_intensityToHex()`. Pure functions, no side effects.
- **Presentation** — component functions. Orchestrate helpers + config to produce DOM. Must not contain hardcoded thresholds.

### BLOCKER: No config in component logic

- Component functions must not contain hardcoded numeric thresholds. Use `DESIGN_TOKENS.score.highThreshold` (via `_scoreTier()`).
- SVG dimensions are acceptable constants (`_RING_R = 22`, `_CELL_S = 16`) since they are structural, not configurable.

---

## Code Structure & Readability

### Order (top to bottom)

1. Module docstring
2. `DESIGN_TOKENS` export
3. Private helpers
4. Component functions (numbered and grouped by component)
5. **No stray code after the last component function**

### Private function conventions

- `_` prefix for all module-private functions and constants.
- Define **before** the function that uses them — no forward references. `_intensityToHex` must be defined before `HeatmapGrid`.
- No unnecessary aliases — if `_GAP` is a constant, use `_GAP` everywhere, not `const _Gap = _GAP`.

### JSDoc

Every component function must have a JSDoc block with `@param` and `@returns`:

```js
/**
 * @param {object} opts
 * @param {string} opts.label
 * @param {boolean} [opts.active=false]
 * @returns {HTMLButtonElement}
 */
```

### Indentation

Match the existing codebase: **tabs**, not spaces. The existing `app.js`, `utils.js`, and all other dashboard JS files use tabs. `primitives.js` was created with 2-space indentation — this is a known deviation that should be corrected when the file is next touched for substantive changes.

---

## SVG Handling

- Use `document.createElementNS("http://www.w3.org/2000/svg", ...)` for SVG elements — never use `innerHTML` for SVG construction.
- SVG dimension attributes (`width`, `height`, `viewBox`) are constants, defined at the module level.
- Tooltip `<title>` elements use `.textContent` (no `innerHTML`).

---

## Edge Cases Every Component Must Handle

| Category             | Check                                             |
| -------------------- | ------------------------------------------------- |
| Null/undefined input | Fallback to sensible default or display "—"       |
| Empty arrays         | Render empty state or no-op                       |
| Negative values      | Clamp to valid range                              |
| Over-large values    | Clamp to valid range                              |
| Missing callbacks    | Guard with `if (onChange) onChange(...)`          |
| Invalid types        | Coerce or fallback (e.g., `String(value ?? "—")`) |

---

## Testing

- Every component must have a test file (`primitives.test.js`) with vitest + jsdom.
- Test structure: `describe("ComponentName", () => { ... })` — one `describe` per component.
- Coverage per component:
  - ✅ Return type (`HTMLElement` with correct tag)
  - ✅ Default class present
  - ✅ Variant classes (e.g., `high`/`mid`/`low` for ScorePill)
  - ✅ Text content correctness
  - ✅ Callbacks fire with correct arguments
  - ✅ Edge cases (null, empty, boundaries)
  - ✅ Integration: all components return `instanceof HTMLElement`
- Tests must run in CI — `npx vitest run` must pass.

---

## MAJOR Review Items (from LKPR-126 review)

These are specific issues caught during the LKPR-126 review that should not recur:

1. **No dead code** — `const _Gap = _GAP; // alias for closure` at line 520 was a redundant alias. Use the original constant directly.
2. **No forward references** — `_intensityToHex` was defined at line 522 but called at line 484. Define helpers before their consumers.
3. **Consistent DOM helpers** — `document.createElement("span")` at line 224 should be `_el("span")`. Use `_el` universally.
4. **Test file must not be deleted from working tree** — `primitives.test.js` was committed in `bb6ee09` but deleted from the working tree between commits. Always check `git status` before committing to ensure no tracked files are missing.
