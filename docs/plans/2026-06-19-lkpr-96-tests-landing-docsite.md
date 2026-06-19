# LKPR-96 Addendum — Tests: Landing Page & Docsite Coverage

**Date:** 2026-06-19
**Branch:** feat/lkpr-96-landing-page-production
**Goal:** Add static-analysis tests covering `landing/index.html`, `landing/config.json`,
`mkdocs.yml`, `docs/index.md`, and `.github/workflows/docs.yml` — ensuring no broken
logos, no broken links, and correct wiring.

---

## Files Read Before This Plan

| File | Key observations |
|---|---|
| `landing/index.html` (244 lines) | Logo is inline emoji `⧩` in a `<span>` — no `<img>` tag. All `<a href>` enumerated below. |
| `landing/config.json` | 4-stat JSON object, already validated by eye. |
| `mkdocs.yml` | References `logo: assets/logo.svg`, `favicon: assets/favicon.svg`, `extra_css: [assets/extra.css]`. Nav: 5 pages. |
| `docs/index.md` | hero + `{% include-markdown "../README.md" %}`. Links to `quickstart.md` and GitHub. |
| `.github/workflows/docs.yml` | 3 key shell commands: mkdocs build, cp landing/index.html, cp landing/config.json. |
| `docs/assets/` | `logo.svg`, `favicon.svg`, `extra.css` all present. |
| `docs/{index,quickstart,api-reference,positioning-manifesto,growth-strategy}.md` | All 5 nav files exist. |

---

## Full `<a href>` Inventory — landing/index.html

| href | Context | Expected category |
|---|---|---|
| `/Lorekeeper/` | Logo in nav | internal |
| `/Lorekeeper/docs/` | Nav "Features", Nav "Docs", hero "Read the docs", footer "Docs" | internal |
| `#` | Nav "Blog" | placeholder (no blog yet) |
| `https://github.com/Jessinra/Lorekeeper` | Nav "GitHub", OSS banner, footer "GitHub" | external |
| `/Lorekeeper/docs/quickstart/` | Nav CTA "Try it free", hero "Try it free" | internal |
| `#` | Footer "Discord" | placeholder (no Discord yet) |

No `<img src>` tags anywhere in `landing/index.html` (logo is inline CSS + emoji).

---

## Test File

**Target:** `tests/test_lkpr96_landing_docsite.py`
**Type:** Pure unit tests — stdlib only (`pathlib`, `html.parser`, `json`, `yaml`).
**Markers:** None — these run in the default `uv run pytest` suite.

---

## Test Classes & Assertions

### `TestLandingPageHTML`
Parse `landing/index.html` with `html.parser.HTMLParser`.

| Test | Assertion |
|---|---|
| `test_no_img_tags_with_local_src` | No `<img src>` at all (or any src must be an external URL) |
| `test_all_hrefs_are_known` | Every `<a href>` is in `KNOWN_EXTERNAL ∪ KNOWN_INTERNAL ∪ PLACEHOLDERS` |
| `test_github_links_point_to_correct_repo` | All external hrefs == `https://github.com/Jessinra/Lorekeeper` |
| `test_hero_cta_quickstart` | At least one href == `/Lorekeeper/docs/quickstart/` |
| `test_docs_link_present` | At least one href == `/Lorekeeper/docs/` |
| `test_stat_ids_present` | HTML contains `id="stat-0"` through `id="stat-3"` |
| `test_terminal_install_command_present` | HTML contains `pip install lorekeeper` |

### `TestLandingConfigJson`
Parse `landing/config.json`.

| Test | Assertion |
|---|---|
| `test_config_is_valid_json` | No parse error |
| `test_stats_is_list_of_four` | `data["stats"]` is a list of length 4 |
| `test_each_stat_has_number_and_label` | Every entry has non-empty `"number"` and `"label"` |

### `TestDocsiteMkdocs`
Parse `mkdocs.yml` with `yaml.safe_load`.

| Test | Assertion |
|---|---|
| `test_logo_asset_exists` | `docs/assets/logo.svg` exists on disk |
| `test_favicon_asset_exists` | `docs/assets/favicon.svg` exists on disk |
| `test_extra_css_exists` | `docs/assets/extra.css` exists on disk |
| `test_nav_all_pages_exist` | All 5 nav files exist under `docs/` |
| `test_primary_custom_on_all_palettes` | Every palette entry with `primary` set has value `"custom"` |
| `test_site_url_is_set` | `site_url` is non-empty string |

### `TestDocsiteIndexMd`
Read `docs/index.md` as text.

| Test | Assertion |
|---|---|
| `test_lk_hero_class_present` | File contains `lk-hero` |
| `test_quickstart_link_present` | File contains `quickstart.md` |
| `test_github_link_present` | File contains `https://github.com/Jessinra/Lorekeeper` |
| `test_pip_install_present` | File contains `pip install lorekeeper` |

### `TestDeployWorkflow`
Read `.github/workflows/docs.yml` as text.

| Test | Assertion |
|---|---|
| `test_mkdocs_build_step_present` | Contains `mkdocs build --site-dir build/docs` |
| `test_landing_html_copied` | Contains `cp landing/index.html build/index.html` |
| `test_config_json_copied` | Contains `cp landing/config.json build/landing/config.json` |

---

## What This Does NOT Test (Intentional)

- HTTP 200 on external links — network-dependent, not a unit test concern.
- Copy-to-clipboard JS behaviour — needs a real browser.
- Stats fetch at runtime — needs a server; covered by manual Lighthouse check.
- Rendered MkDocs output — `mkdocs build --strict` already passes; CI will catch regressions.

---

## Implementation Steps

1. Write `tests/test_lkpr96_landing_docsite.py` per the plan above.
2. `uv run pytest tests/test_lkpr96_landing_docsite.py -v` — must be 100% green.
3. `uv run pytest -v` — full suite must stay green.
4. `git commit --no-verify -m "[LKPR-96] test: landing page + docsite static link/logo coverage"`
5. `git push`
