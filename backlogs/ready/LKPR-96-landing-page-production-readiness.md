---
id: LKPR-96
title: Landing Page — wire up real links, terminal interactivity, mobile QA, Lighthouse audit
type: chore
status: S:ready
priority: P2:medium
sprint: ~
rice_score: ~
filed_by: Akane (from Chisa handoff)
filed_date: 2026-06-15
github_issue: 221
---

# [LKPR-96] Landing Page — Production Readiness

## Problem

Chisa's final landing page design (`~/.hermes/profiles/chisa/docs/research/content/ab-test/landing/lorekeeper-landing-final.html`) is fully designed and A/B tested but uses placeholder links, static mockups, and needs deploy pipeline changes to work as the GH Pages root. The existing MkDocs docsite needs theme alignment to match.

## Solution

Landing page as root `index.html` with the MkDocs docsite at `/docs/` subpath. Diana wires up real links, adds terminal interactivity, drives stats from configurable JSON, runs Lighthouse audit, updates the deploy workflow, and matches the docsite color theme to the landing page.

## Scope

**Source file:** `~/.hermes/profiles/chisa/docs/research/content/ab-test/landing/lorekeeper-landing-final.html`

### Required

1. **Wire up real links** — replace all `href="#"` with actual destinations:

   - Features → link to docs section
   - Docs → `/Lorekeeper/docs/`
   - Blog → `#` (no blog yet, keep placeholder)
   - GitHub → `https://github.com/Jessinra/Lorekeeper`
   - "Try it free" → `/Lorekeeper/` (landing page IS the homepage)
   - "Read the docs" → `/Lorekeeper/docs/`
   - Discord → `#` placeholder (no Discord yet)
   - Footer GitHub/Docs/Discord → same as above
   - Nav logo → `/Lorekeeper/`

2. **Terminal interactivity** — add copy-to-clipboard on the terminal block (click to copy commands). Optional: animated typing effect.

3. **Mobile responsive QA** — existing breakpoints at 900px and 640px. Test on real mobile sizes (375px, 390px). Fix any layout breaks.

4. **Lighthouse audit** — run Lighthouse (perf, a11y, SEO). Target: 90+ across all categories. Report scores in PR.

5. **Deploy pipeline** — update `.github/workflows/docs.yml` so the landing page is the root `index.html` and MkDocs lives under `/docs/`:

   - Change `mkdocs.yml` `site_url` to `https://jessinra.github.io/Lorekeeper/docs/`
   - Replace `mkdocs gh-deploy --force` with a build + deploy flow that:
     - Builds MkDocs to a `build/` dir (with `--site-dir build/docs`)
     - Copies landing page HTML as `build/index.html`
     - Deploys `build/` to gh-pages branch

6. **Configurable stats** — drive the 4 stat numbers from `landing/config.json`:

   - Create `landing/config.json` with the 4 stat values (label + number)
   - HTML fetches it on load and populates the stats row
   - Jason can edit JSON to change marketing copy without touching HTML

7. **Docsite theme alignment** — update the MkDocs docsite to match the landing page color scheme:
   - Change `mkdocs.yml` theme: `primary: custom`, `accent: custom` with `#8a7bb5` dusty purple
   - Add `extra_css: [assets/extra.css]` with CSS variables for the brand color
   - Add a hero section to `docs/index.md` (badge, headline, CTAs, terminal mockup, stats row — similar layout to landing page)
   - Handle dark mode (slate scheme overrides)
   - Verify `uv run mkdocs build --strict` passes

### Out of scope

- Content stats — keep as marketing copy, no verification needed
- GitHub stars badge — skip for now (count still low)
- Analytics — skip for now

## Acceptance Criteria

- [ ] All placeholder `href="#"` replaced with real URLs (or documented intentional placeholders)
- [ ] Terminal block has copy-to-clipboard
- [ ] Page renders correctly at 375px, 390px, 768px, 1280px
- [ ] Lighthouse scores ≥ 90 for perf, a11y, SEO on desktop
- [ ] Landing page deployed as root index.html on `https://jessinra.github.io/Lorekeeper/`
- [ ] Docsite accessible at `https://jessinra.github.io/Lorekeeper/docs/`
- [ ] Stat numbers driven from `landing/config.json` (not hardcoded in HTML)
- [ ] Docsite matches landing page theme (white + dusty purple, hero section, dark mode)
- [ ] Deploy workflow updated (no longer uses raw `mkdocs gh-deploy --force`)
- [ ] PR opened against Lorekeeper repo

## Dependencies

_None_

## Notes

Landing page was A/B tested across 8 personas. Key design decisions to preserve:

- White + dusty purple (`#8a7bb5`) palette
- Honestly box (not testimonials) — A/B tested as strongest trust element
- Terminal mockup in hero section
- Pipeline section (not code blocks) for "get started"

Full handoff doc: `~/.hermes/profiles/chisa/docs/briefs/handoff-akane-lorekeeper-landing.md`

## Required Updates

- **CLAUDE.md**: [ ] N/A
- **README.md**: [ ] N/A
- **Skills**: [ ] N/A
- **Backlog**: [ ] N/A
