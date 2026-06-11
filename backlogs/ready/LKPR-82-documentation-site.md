---
id: LKPR-82
title: Documentation site — MkDocs + GitHub Pages for browsable quickstart + API ref
type: enhancement
status: S:Ready
priority: P1:high
sprint: beta
rice_score: ~
filed_by: Akane (PM)
filed_date: 2026-06-11
github_issue: 186
---

# [LKPR-82] Documentation site — MkDocs + GitHub Pages for browsable quickstart + API ref

## Problem

Lorekeeper has well-written documentation in raw markdown (`README.md`, `docs/quickstart.md`, `docs/api-reference.md`, `docs/ARCHITECTURE.md`), but there's no browsable, searchable documentation site. This hurts:

- **First impressions** — no docs site = looks hobbyist. HN launch, Reddit, and MCP Registry listings need somewhere to link to.
- **Discoverability** — users have to open raw markdown files on GitHub. No nav, no search, no table of contents sidebar.
- **Onboarding friction** — Quickstart + API ref are great content but get buried in the repo tree.

Maintaining duplicate content (README vs mkdocs copy) is **not acceptable** — the README must remain the single source of truth for the landing/home page.

## Solution

Deploy a MkDocs site with the Material theme to GitHub Pages. Use `mkdocs-include-markdown-plugin` to embed `README.md` as the home page without copying content. API reference, quickstart, and architecture docs already live in `docs/` — they get a single `nav:` entry each.

### Architecture

```
lorekeeper/
├── README.md              ← single source for home page (included via plugin)
├── mkdocs.yml             ← new: MkDocs config
├── docs/
│   ├── index.md           ← new: thin page that includes README.md
│   ├── quickstart.md      ← already exists
│   ├── api-reference.md   ← already exists (336 lines, covers all 8 tools)
│   ├── ARCHITECTURE.md    ← already exists
│   ├── positioning-manifesto.md  ← already exists (→ Comparison section)
│   └── growth-strategy.md ← already exists (→ Roadmap section)
├── .github/workflows/
│   └── docs.yml           ← new: CI deploy to GitHub Pages on main push
└── assets/                ← screenshots already used by README
```

### Nav Structure

```yaml
nav:
  - Home: index.md
  - Quickstart: quickstart.md
  - API Reference: api-reference.md
  - Architecture: ARCHITECTURE.md
  - Comparison: positioning-manifesto.md
  - Roadmap: growth-strategy.md
```

### Dependencies

Add to `pyproject.toml` under `[project.optional-dependencies]` as `docs` extras:

```toml
[project.optional-dependencies]
docs = [
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
    "mkdocs-include-markdown-plugin>=6.0",
]
```

Note: these are NOT runtime deps — docs extra only, used in CI.

### CI/Automation

```yaml
# .github/workflows/docs.yml
name: docs
on:
  push:
    branches: [main]
  workflow_dispatch: # allow manual re-deploy

permissions:
  contents: write # needed for gh-deploy to push to gh-pages branch

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install mkdocs mkdocs-material mkdocs-include-markdown-plugin
      - run: mkdocs gh-deploy --force
```

### Implementation Steps

1. Create `mkdocs.yml` with Material theme config, nav structure, and `mkdocs-include-markdown-plugin` enabled
2. Create `docs/index.md` that references README.md:

   ```markdown
   <!--docs/index.md—thin wrapper that includes the project README-->

   {!README.md!}
   ```

3. Create `.github/workflows/docs.yml` with the CI deploy step
4. Add `docs` extras to `pyproject.toml`
5. Run `mkdocs build` locally to verify everything renders
6. Push to main → CI deploys to `https://jessinra.github.io/Lorekeeper/`
7. Add a docs badge to README.md: `[![docs](https://img.shields.io/badge/docs-lorekeeper.dev-blue)](https://jessinra.github.io/Lorekeeper/)`

### What NOT to do

- **Don't copy README content** — use the include plugin. README is the single source.
- **Don't split api-reference.md into per-tool pages** — 336 lines is fine for one page. Split later when it grows.
- **Don't add search indexing / analytics** — Material theme has built-in search. No extra tooling needed.
- **Don't set up a custom domain** — use `jessinra.github.io/Lorekeeper/` for now. Can add a custom domain later.

## Acceptance Criteria

- [ ] `mkdocs.yml` exists with Material theme, nav, and include plugin
- [ ] `docs/index.md` includes `README.md` via the plugin (no duplicate content)
- [ ] `mkdocs build` succeeds locally with no warnings
- [ ] Site renders correctly: nav sidebar, search works, all pages accessible
- [ ] `.github/workflows/docs.yml` deploys to GitHub Pages on main push
- [ ] Site is live at `https://jessinra.github.io/Lorekeeper/`
- [ ] README has a docs badge linking to the site
- [ ] API reference page covers all 8 tools with examples
- [ ] Quickstart page renders correctly (includes setup command, dashboard screenshot)

## Dependencies

- None — all content already exists. This is pure tooling + CI polish.

## Required Updates

- [ ] README.md — add docs badge
- [ ] CLAUDE.md — add docs build command and workflow note
- [ ] Skills: none (dev workflow unchanged)
