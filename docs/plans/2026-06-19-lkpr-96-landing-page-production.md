# LKPR-96: Landing Page — Production Readiness

**Date:** 2026-06-19  
**Ticket:** backlogs/ready/LKPR-96-landing-page-production-readiness.md  
**GitHub Issue:** #221  
**Branch:** `feat/lkpr-96-landing-page-production`

---

## Source of Truth

- **Input file:** `/Users/jessinra/.hermes/profiles/chisa/docs/research/content/ab-test/landing/lorekeeper-landing-final.html` (157 lines, 14.6KB — A/B-tested final design)
- **Deployed target:** `https://jessinra.github.io/Lorekeeper/` = landing page root, `/docs/` = MkDocs

---

## Files Affected

| File                         | Action     | Why                                                                                         |
| ---------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `landing/index.html`         | **Create** | Production landing page (copy from Chisa + modifications)                                   |
| `landing/config.json`        | **Create** | Configurable stats JSON                                                                     |
| `.github/workflows/docs.yml` | **Modify** | Replace `mkdocs gh-deploy --force` with 2-stage build+deploy                                |
| `mkdocs.yml`                 | **Modify** | Change `site_url`, theme colors → dusty purple, add `extra_css`, add `md_in_html` extension |
| `docs/assets/extra.css`      | **Create** | Brand color CSS variables for mkdocs-material                                               |
| `docs/index.md`              | **Modify** | Add hero section (badge, headline, CTAs, terminal, stats) before README include             |

---

## Change Breakdown

### 1. `landing/index.html` (new file)

Start from Chisa's final HTML. Apply these changes:

**A. Wire up real links** — replace all `href="#"`:
| Element | From | To |
|---------|------|-----|
| Nav logo | `#` | `/Lorekeeper/` |
| Nav "Features" | `#` | `/Lorekeeper/docs/#features` |
| Nav "Docs" | `#` | `/Lorekeeper/docs/` |
| Nav "Blog" | `#` | `#` (intentional — no blog yet, keep) |
| Nav "GitHub" | `#` | `https://github.com/Jessinra/Lorekeeper` |
| Nav "Try it free" CTA | `#` | `/Lorekeeper/docs/quickstart/` |
| Hero "Try it free" btn | `#` | `/Lorekeeper/docs/quickstart/` |
| Hero "Read the docs" btn | `#` | `/Lorekeeper/docs/` |
| OSS banner "View on GitHub" | `#` | `https://github.com/Jessinra/Lorekeeper` |
| Footer "GitHub" | `#` | `https://github.com/Jessinra/Lorekeeper` |
| Footer "Docs" | `#` | `/Lorekeeper/docs/` |
| Footer "Discord" | `#` | `#` (intentional — no Discord yet) |

> Note: "Try it free" maps to quickstart (not root — linking to self is a no-op UX). Ticket says `/Lorekeeper/` but quickstart is the actionable equivalent. **Will flag this in PR.**

**B. Stats driven from `landing/config.json`:**

- Remove hardcoded stat values from HTML
- Add `id` attrs to `.stat-number` elements: `stat-0`, `stat-1`, `stat-2`, `stat-3`
- Add `<script>` at bottom: fetch `./landing/config.json` on `DOMContentLoaded`, populate `textContent`
- Fallback: if fetch fails, silently keep existing text (graceful degradation)

**C. Copy-to-clipboard on terminal block:**

- Add `cursor: pointer; user-select: none;` to `.terminal-mock`
- Add `title="Click to copy"` tooltip hint on `.terminal-header`
- Add click handler: copy the two install commands to clipboard via `navigator.clipboard.writeText()`
- Add brief visual feedback: `.terminal-header` briefly shows "✓ Copied!" text, resets after 1.5s
- NO animated typing — spec says "optional", keep it simple, less JS = better Lighthouse perf score

**D. Mobile QA fixes** (based on inspecting the existing breakpoints):

- The existing `@media (max-width: 640px)` hides `.nav-links` — confirm nav CTA still visible
- Add `padding: 14px 16px` to `.nav-inner` on mobile (tighten from 24px)
- Verify `.stats` 2-col layout doesn't overflow at 375px — add `min-width: 0` to `.stat-item`
- Pipeline section needs `padding: 0 16px` on mobile (currently no padding)
- Add `@media (max-width: 375px)` micro-fix: `.hero h1` font-size floor to 28px

---

### 2. `landing/config.json` (new file)

```json
{
  "stats": [
    { "number": "200+", "label": "Teams using it" },
    { "number": "5K+", "label": "Memories per server" },
    { "number": "<30s", "label": "Setup time" },
    { "number": "MCP", "label": "One-line config" }
  ]
}
```

---

### 3. `.github/workflows/docs.yml` (modify)

**Current:** `mkdocs gh-deploy --force` (single step, overwrites gh-pages with MkDocs output)

**New approach:** Build MkDocs → `build/docs/`, copy landing page → `build/index.html`, push `build/` to gh-pages.

```yaml
name: docs

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install MkDocs
        run: pip install mkdocs mkdocs-material mkdocs-include-markdown-plugin
      - name: Build MkDocs to build/docs/
        run: mkdocs build --site-dir build/docs
      - name: Assemble build root
        run: |
          cp landing/index.html build/index.html
          mkdir -p build/landing
          cp landing/config.json build/landing/config.json
      - name: Deploy to GitHub Pages
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          cd build
          git init -b gh-pages
          git add .
          git commit -m "Deploy: landing page + docs"
          git push --force "https://x-access-token:${{ secrets.GITHUB_TOKEN }}@github.com/${GITHUB_REPOSITORY}.git" gh-pages
```

No external third-party action needed — pure git push.

---

### 4. `mkdocs.yml` (modify)

**Changes:**

1. `site_url`: `https://jessinra.github.io/Lorekeeper/` → `https://jessinra.github.io/Lorekeeper/docs/`
2. Theme palette: `primary: teal`, `accent: cyan` → `primary: custom`, `accent: custom` (both palettes)
3. Add `extra_css: [assets/extra.css]`
4. Add markdown extension: `- md_in_html` (needed for hero section HTML in docs/index.md)

Before/after line counts: ~65 lines → ~70 lines (minimal change)

---

### 5. `docs/assets/extra.css` (new file)

```css
/* LKPR-96: Lorekeeper brand colors — dusty purple #8a7bb5 */
[data-md-color-scheme="default"] {
  --md-primary-fg-color: #8a7bb5;
  --md-primary-fg-color--light: #b0a6d6;
  --md-primary-fg-color--dark: #6b5d95;
  --md-accent-fg-color: #8a7bb5;
  --md-accent-fg-color--transparent: rgba(138, 123, 181, 0.1);
}
[data-md-color-scheme="slate"] {
  --md-primary-fg-color: #b0a6d6;
  --md-primary-fg-color--light: #c9c2e4;
  --md-primary-fg-color--dark: #8a7bb5;
  --md-accent-fg-color: #b0a6d6;
}
```

---

### 6. `docs/index.md` (modify)

Replace the current thin `{% include-markdown "../README.md" %}` wrapper with:

1. A minimal HTML hero block (badge + headline + CTA buttons + terminal mockup + stats — adapted from landing page)
2. Then the README include below for the technical documentation

The hero uses `md_in_html` extension to allow HTML blocks. Styled via `extra.css` classes.

> **Scope boundary:** This is a lightweight hero, not a full recreation of the landing page. The goal is visual continuity so /docs/ doesn't feel like a different product.

---

## Deploy URL Contract After This PR

| URL                                                         | Content              |
| ----------------------------------------------------------- | -------------------- |
| `https://jessinra.github.io/Lorekeeper/`                    | `landing/index.html` |
| `https://jessinra.github.io/Lorekeeper/landing/config.json` | Stats config         |
| `https://jessinra.github.io/Lorekeeper/docs/`               | MkDocs site root     |
| `https://jessinra.github.io/Lorekeeper/docs/quickstart/`    | Quickstart page      |

---

## Lighthouse Plan

After deploying, run Lighthouse CLI against the live URL:

```bash
npx lighthouse https://jessinra.github.io/Lorekeeper/ --output json --output html
```

Target: ≥90 perf, a11y, SEO. Known risks:

- Google Fonts CDN call may hurt perf score slightly — if <90, add `<link rel="preconnect">` + `font-display: swap`
- Missing `meta description` in Chisa's HTML — add before deploy
- Missing `alt` on logo-mark span (it's a `<span>`, not `<img>`) — fine

---

## Acceptance Criteria Checklist

- [ ] All `href="#"` replaced with real URLs (or documented intentional placeholders: Blog, Discord)
- [ ] Terminal block has copy-to-clipboard with visual feedback
- [ ] Page renders correctly at 375px, 390px, 768px, 1280px
- [ ] Lighthouse ≥90 perf, a11y, SEO on desktop (report scores in PR)
- [ ] Landing page deployed as root at `https://jessinra.github.io/Lorekeeper/`
- [ ] Docsite accessible at `https://jessinra.github.io/Lorekeeper/docs/`
- [ ] Stat numbers driven from `landing/config.json`
- [ ] Docsite uses dusty purple `#8a7bb5` brand color
- [ ] Hero section added to `docs/index.md`
- [ ] `mkdocs build --strict` passes
- [ ] PR opened against Lorekeeper repo

---

## Questions for Jason (pre-implementation)

1. **"Try it free" destination**: Ticket says `/Lorekeeper/` (self-link). I'm planning to use `/Lorekeeper/docs/quickstart/` instead since linking to the same page is a no-op. OK to change?
2. **Lighthouse**: Should I run it against the live deployed URL (post-merge) or locally before PR? Local requires serving the file.
