# LKPR-82 Implementation Plan — Documentation site (MkDocs + GitHub Pages)

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Deploy a browsable MkDocs documentation site with Material theme to GitHub Pages, using the include-markdown-plugin to keep README.md as the single source for the home page.

**Architecture:** Zero new content — all docs already exist in `docs/`. This is purely tooling: MkDocs config, a thin `docs/index.md` wrapper that includes `README.md` via plugin, a CI deploy workflow, a `pyproject.toml` extras group, a README badge, and a CLAUDE.md update. No new code in `src/`.

**Tech Stack:** MkDocs >=1.6, mkdocs-material >=9.5, mkdocs-include-markdown-plugin >=6.0 (all docs-only extras, not runtime deps). CI via `mkdocs gh-deploy --force`.

**Branch:** `feat/LKPR-82-docs-site`

---

### Task 1: Create `mkdocs.yml` with Material theme and nav

**Objective:** Configure MkDocs with Material theme, nav structure matching all 6 `docs/` pages, and the include-markdown-plugin enabled.

**Files:**

- Create: `mkdocs.yml`

**Complete code:**

```yaml
site_name: Lorekeeper
site_description: "Self-improving memory for AI agents — open-source MCP server"
site_url: "https://jessinra.github.io/Lorekeeper/"
repo_url: "https://github.com/Jessinra/Lorekeeper"
repo_name: Jessinra/Lorekeeper
edit_uri: edit/main/docs/

theme:
  name: material
  features:
    - navigation.instant
    - navigation.tracking
    - search.highlight
    - content.code.copy

plugins:
  - search
  - include-markdown

markdown_extensions:
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - admonition
  - pymdownx.details

nav:
  - Home: index.md
  - Quickstart: quickstart.md
  - API Reference: api-reference.md
  - Architecture: ARCHITECTURE.md
  - Comparison: positioning-manifesto.md
  - Roadmap: growth-strategy.md

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/Jessinra/Lorekeeper
```

**Verify:** Run `uv run mkdocs build --strict` and confirm no errors.

---

### Task 2: Create `docs/index.md` as a thin README wrapper

**Objective:** Create the home page that includes `README.md` via the plugin — no content duplication.

**Files:**

- Create: `docs/index.md`

**Complete code:**

```markdown
<!-- docs/index.md — thin wrapper that includes the project README -->

{!README.md!}
```

**Verify:** The `mkdocs build` from Task 1 should now produce an `index.html` that renders the full README content.

---

### Task 3: Add `docs` extras to `pyproject.toml`

**Objective:** Add a `docs` optional-dependencies group under `[project.optional-dependencies]` so docs tooling can be installed with `uv sync --group docs`.

**Files:**

- Modify: `pyproject.toml` — after the `dashboard = [...]` block, add:

```toml
docs = [
    "mkdocs>=1.6",
    "mkdocs-material>=9.5",
    "mkdocs-include-markdown-plugin>=6.0",
]
```

Also locate `[project.urls]` and update the `Documentation` URL:

```toml
Documentation = "https://jessinra.github.io/Lorekeeper/"
```

**Verify:** Run `uv sync --group docs` and confirm install succeeds with no errors.

---

### Task 4: Create `.github/workflows/docs.yml` — GitHub Pages deploy

**Objective:** Create the CI workflow that deploys the MkDocs site to GitHub Pages on every `main` push.

**Files:**

- Create: `.github/workflows/docs.yml`

**Complete code:**

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install mkdocs mkdocs-material mkdocs-include-markdown-plugin
      - run: mkdocs gh-deploy --force
```

**Note:** This workflow uses `pip install` (not `uv sync`) because it only needs 3 lightweight packages — no runtime deps. Running `uv sync --group docs` would pull in all runtime dependencies (mem0, chromadb, sentence-transformers, etc.), adding ~90s to the CI job. `pip install` on these 3 packages is ~10s.

**Verify:** The workflow YAML is valid (no syntax errors).

---

### Task 5: Add docs badge to README.md

**Objective:** Add a shields.io badge linking to the documentation site, placed right after the project description block.

**Files:**

- Modify: `README.md` — add badge line between line 11 (end of intro blockquote) and line 12 (dashboard image):

```markdown
[![docs](https://img.shields.io/badge/docs-lorekeeper.dev-blue)](https://jessinra.github.io/Lorekeeper/)
```

Specifically, replace lines 10-12:

```markdown
> Local. No API keys. No sign-up. **Free to run forever.**

![Lorekeeper dashboard — Memories tab](assets/dashboard-memories-tab.png)
```

with:

```markdown
> Local. No API keys. No sign-up. **Free to run forever.**

[![docs](https://img.shields.io/badge/docs-lorekeeper.dev-blue)](https://jessinra.github.io/Lorekeeper/)

![Lorekeeper dashboard — Memories tab](assets/dashboard-memories-tab.png)
```

**Verify:** `mkdocs build` succeeds with the updated README.

---

### Task 6: Update CLAUDE.md with docs build commands

**Objective:** Add the docs build/local-preview commands to the Environment/Tooling section so developers know how to verify docs changes.

**Files:**

- Modify: `CLAUDE.md` — add these lines after line 106 (`- Entrypoint: uv run lorekeeper`):

```
- Build docs (local preview): `uv sync --group docs && uv run mkdocs serve`
- Build docs (strict): `uv run mkdocs build --strict`
- Pre-PR rule: always run `mkdocs build --strict` before opening a PR that touches `mkdocs.yml`, `docs/`, or `README.md`. Catches broken includes or plugin issues before CI.
```

**Verify:** Read the updated section — it should flow naturally after the entrypoint line.

---

### Task 7: Run `mkdocs build --strict` locally to verify everything renders

**Objective:** Install the docs deps and build the full site, confirming zero warnings and all pages render.

**Command:**

```bash
cd /Users/jessinra/Code/lorekeeper
uv sync --group docs
uv run mkdocs build --strict
```

**Expected output:** `INFO    -  Documentation built in X.XX seconds` with zero errors or warnings.

**Also verify site renders correctly:**

```bash
ls -la site/index.html site/api-reference/index.html site/quickstart/index.html
```

All 3 should exist. Open `site/index.html` in a browser to confirm the README content renders and nav sidebar works.

---

### Task 8: Commit and push

**Objective:** Commit all changes with a descriptive message and push the branch.

**Files to commit:**

- `mkdocs.yml`
- `docs/index.md`
- `pyproject.toml`
- `.github/workflows/docs.yml`
- `README.md`
- `CLAUDE.md`

**Commands:**

```bash
git add mkdocs.yml docs/index.md pyproject.toml .github/workflows/docs.yml README.md CLAUDE.md
git commit -m "feat(LKPR-82): add MkDocs documentation site with GitHub Pages deploy"
git push origin feat/LKPR-82-docs-site
```

---

### Task 9: Open PR and verify CI + Pages deploy

**Objective:** Open a PR against `main` using `gh` CLI, wait for CI, then confirm the docs workflow ran.

**Commands:**

```bash
# Refresh GitHub token first
python3 /Users/jessinra/.hermes/scripts/gh-token-refresh.py

# Open PR
gh pr create \
  --base main \
  --head feat/LKPR-82-docs-site \
  --title "[LKPR-82] Documentation site — MkDocs + GitHub Pages" \
  --body "Implements browsable documentation site with Material theme.

- mkdocs.yml with nav covering all 6 doc pages
- docs/index.md includes README.md via include-markdown plugin (no duplication)
- docs extras group in pyproject.toml
- .github/workflows/docs.yml deploys on main push
- docs badge added to README.md
- CLAUDE.md updated with build commands

Closes #186"
```

After merge to main, verify:

- https://github.com/Jessinra/Lorekeeper/actions shows the `docs` workflow ran
- https://jessinra.github.io/Lorekeeper/ is live
- README badge renders correctly on GitHub

---

## What NOT to do (per ticket)

- Don't copy README content — the include-markdown plugin is the right approach
- Don't split api-reference.md into per-tool pages (336 lines is fine for one page)
- Don't add search indexing / analytics (Material theme has built-in search)
- Don't set up a custom domain — use `jessinra.github.io/Lorekeeper/` for now

## Acceptance Criteria

- [x] Task 1: mkdocs.yml with Material theme, nav, and include plugin
- [x] Task 2: docs/index.md includes README.md via plugin (no duplicate content)
- [x] Task 3: docs extras in pyproject.toml, Documentation URL updated
- [x] Task 4: .github/workflows/docs.yml deploys to GitHub Pages on main push
- [x] Task 5: README docs badge
- [x] Task 6: CLAUDE.md updated with build commands
- [x] Task 7: mkdocs build succeeds locally with no warnings
- [x] Task 8: Committed and pushed
- [x] Task 9: PR opened, merged, site live at https://jessinra.github.io/Lorekeeper/
