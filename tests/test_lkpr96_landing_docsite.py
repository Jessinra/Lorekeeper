"""
LKPR-96 — Static coverage: landing page + docsite.

Tests that:
  1. landing/index.html has no broken links or <img> with local-file srcs
  2. landing/config.json is structurally valid
  3. mkdocs.yml wires up logo, favicon, extra_css, nav pages correctly
  4. docs/index.md contains required hero + CTA content
  5. .github/workflows/docs.yml copies landing artefacts correctly

All stdlib-only — no network, no browser, no server required.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Repo root — resolve once from this file's location
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _LinkCollector(HTMLParser):
    """Collect hrefs (from <a> only), srcs (from <img>/<script>), and all id= attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []  # <a href> only — navigation links
        self.srcs: list[str] = []   # <img src>, <script src> — local asset refs
        self.ids: list[str] = []    # all id= attributes

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        # Only collect hrefs from anchor tags — <link href> is a stylesheet, not a nav link
        if tag == "a":
            if href := attr_dict.get("href"):
                self.hrefs.append(href)
        # Collect src from media/script tags to check for broken local refs
        if tag in ("img", "script", "source"):
            if src := attr_dict.get("src"):
                self.srcs.append(src)
        if id_val := attr_dict.get("id"):
            self.ids.append(id_val)


def _parse_landing_html() -> _LinkCollector:
    html_path = REPO / "landing" / "index.html"
    collector = _LinkCollector()
    collector.feed(html_path.read_text(encoding="utf-8"))
    return collector


# ---------------------------------------------------------------------------
# Allowed link sets — single source of truth for what the landing page links to
# ---------------------------------------------------------------------------

# External links the landing page is permitted to use
_ALLOWED_EXTERNAL = {
    "https://github.com/Jessinra/Lorekeeper",
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
}

# Internal absolute paths on the GitHub Pages site
_ALLOWED_INTERNAL = {
    "/Lorekeeper/",
    "/Lorekeeper/docs/",
    "/Lorekeeper/docs/quickstart/",
}

# Intentional stub placeholders (blog / Discord don't exist yet)
_ALLOWED_PLACEHOLDERS = {"#"}

_ALL_ALLOWED_HREFS = _ALLOWED_EXTERNAL | _ALLOWED_INTERNAL | _ALLOWED_PLACEHOLDERS


# ===========================================================================
# 1. Landing HTML tests
# ===========================================================================


class TestLandingPageHTML:
    """Parse landing/index.html and verify all links + assets are correct."""

    def test_landing_html_exists(self) -> None:
        assert (REPO / "landing" / "index.html").exists(), "landing/index.html must exist"

    def test_no_local_img_srcs(self) -> None:
        """No <img src='local-file'>. Logo is an inline CSS span — no raster images."""
        collector = _parse_landing_html()
        local_srcs = [
            s
            for s in collector.srcs
            if not s.startswith(("http://", "https://", "data:", "//"))
        ]
        assert local_srcs == [], (
            f"Found <img> or <link> with local src/href (could 404 on GitHub Pages):\n"
            + "\n".join(f"  {s}" for s in local_srcs)
        )

    def test_all_hrefs_are_known(self) -> None:
        """Every <a href> must be in the explicitly approved set — nothing unknown slips in."""
        collector = _parse_landing_html()
        unknown = [h for h in collector.hrefs if h not in _ALL_ALLOWED_HREFS]
        assert unknown == [], (
            f"Found unexpected hrefs in landing/index.html:\n"
            + "\n".join(f"  {h}" for h in unknown)
            + "\nIf intentional, add to _ALLOWED_EXTERNAL / _ALLOWED_INTERNAL."
        )

    def test_github_links_point_to_correct_repo(self) -> None:
        collector = _parse_landing_html()
        gh_links = [h for h in collector.hrefs if "github.com" in h]
        assert gh_links, "Expected at least one GitHub link in landing page"
        bad = [h for h in gh_links if h != "https://github.com/Jessinra/Lorekeeper"]
        assert bad == [], f"GitHub links point to wrong repos: {bad}"

    def test_hero_cta_links_to_quickstart(self) -> None:
        collector = _parse_landing_html()
        assert "/Lorekeeper/docs/quickstart/" in collector.hrefs, (
            "CTA should link to /Lorekeeper/docs/quickstart/"
        )

    def test_docs_link_present(self) -> None:
        collector = _parse_landing_html()
        assert "/Lorekeeper/docs/" in collector.hrefs, (
            "Nav/footer should link to /Lorekeeper/docs/"
        )

    def test_stat_ids_present(self) -> None:
        """stat-0..3 must exist so the config.json fetch can update them."""
        collector = _parse_landing_html()
        for i in range(4):
            assert f"stat-{i}" in collector.ids, f"id='stat-{i}' missing from landing HTML"
            assert f"stat-label-{i}" in collector.ids, (
                f"id='stat-label-{i}' missing from landing HTML"
            )

    def test_terminal_mock_id_present(self) -> None:
        collector = _parse_landing_html()
        assert "terminal-mock" in collector.ids, (
            "id='terminal-mock' required for copy-to-clipboard JS"
        )

    def test_pip_install_command_present(self) -> None:
        html = (REPO / "landing" / "index.html").read_text(encoding="utf-8")
        assert "pip install lorekeeper" in html, "Install command missing from terminal block"

    def test_lorekeeper_start_command_present(self) -> None:
        html = (REPO / "landing" / "index.html").read_text(encoding="utf-8")
        assert "lorekeeper start" in html, "'lorekeeper start' command missing from landing"


# ===========================================================================
# 2. Config JSON tests
# ===========================================================================


class TestLandingConfigJson:
    """landing/config.json is valid JSON and structurally correct."""

    def _load(self) -> dict:
        return json.loads((REPO / "landing" / "config.json").read_text(encoding="utf-8"))

    def test_config_exists(self) -> None:
        assert (REPO / "landing" / "config.json").exists()

    def test_config_is_valid_json(self) -> None:
        data = self._load()  # raises on invalid JSON
        assert isinstance(data, dict)

    def test_stats_is_list_of_four(self) -> None:
        data = self._load()
        assert "stats" in data, "config.json missing 'stats' key"
        assert isinstance(data["stats"], list), "'stats' must be a list"
        assert len(data["stats"]) == 4, f"Expected 4 stats, got {len(data['stats'])}"

    def test_each_stat_has_number_and_label(self) -> None:
        data = self._load()
        for i, stat in enumerate(data["stats"]):
            assert "number" in stat, f"stats[{i}] missing 'number'"
            assert "label" in stat, f"stats[{i}] missing 'label'"
            assert stat["number"], f"stats[{i}]['number'] must not be empty"
            assert stat["label"], f"stats[{i}]['label'] must not be empty"


# ===========================================================================
# 3. mkdocs.yml tests
# ===========================================================================


class TestDocsiteMkdocs:
    """mkdocs.yml wires up logos, css, nav pages, and brand palette correctly."""

    def _load(self) -> dict:
        return yaml.safe_load((REPO / "mkdocs.yml").read_text(encoding="utf-8"))

    def test_logo_asset_exists(self) -> None:
        cfg = self._load()
        logo = cfg.get("theme", {}).get("logo", "")
        assert logo, "theme.logo not set in mkdocs.yml"
        assert (REPO / "docs" / logo).exists(), f"Logo file missing: docs/{logo}"

    def test_favicon_asset_exists(self) -> None:
        cfg = self._load()
        fav = cfg.get("theme", {}).get("favicon", "")
        assert fav, "theme.favicon not set in mkdocs.yml"
        assert (REPO / "docs" / fav).exists(), f"Favicon file missing: docs/{fav}"

    def test_extra_css_files_exist(self) -> None:
        cfg = self._load()
        css_list = cfg.get("extra_css", [])
        assert css_list, "extra_css not set in mkdocs.yml"
        for css in css_list:
            assert (REPO / "docs" / css).exists(), f"extra_css file missing: docs/{css}"

    def test_all_nav_pages_exist(self) -> None:
        """Every page referenced in the nav must exist under docs/."""
        cfg = self._load()
        nav = cfg.get("nav", [])
        missing = []
        for entry in nav:
            if isinstance(entry, dict):
                for _label, page in entry.items():
                    if isinstance(page, str) and page.endswith(".md"):
                        if not (REPO / "docs" / page).exists():
                            missing.append(page)
        assert missing == [], (
            f"Nav references pages that don't exist:\n"
            + "\n".join(f"  docs/{p}" for p in missing)
        )

    def test_primary_custom_on_all_palettes(self) -> None:
        """All colour-scheme palettes must use primary: custom (brand override via extra_css)."""
        cfg = self._load()
        palettes = cfg.get("theme", {}).get("palette", [])
        assert palettes, "No palette defined in mkdocs.yml"
        for i, pal in enumerate(palettes):
            if "primary" in pal:
                assert pal["primary"] == "custom", (
                    f"palette[{i}].primary should be 'custom', got '{pal['primary']}'"
                )

    def test_site_url_is_set(self) -> None:
        cfg = self._load()
        site_url = cfg.get("site_url", "")
        assert site_url, "site_url must be set in mkdocs.yml"
        assert "jessinra.github.io" in site_url, (
            f"site_url doesn't look right: {site_url}"
        )

    def test_include_markdown_plugin_enabled(self) -> None:
        """docs/index.md uses {% include-markdown %} — plugin must be present."""
        cfg = self._load()
        plugin_names = [
            (p if isinstance(p, str) else next(iter(p)))
            for p in cfg.get("plugins", [])
        ]
        assert "include-markdown" in plugin_names, (
            "include-markdown plugin not found in mkdocs.yml plugins list"
        )


# ===========================================================================
# 4. docs/index.md tests
# ===========================================================================


class TestDocsiteIndexMd:
    """docs/index.md hero block is correct and links properly."""

    def _read(self) -> str:
        return (REPO / "docs" / "index.md").read_text(encoding="utf-8")

    def test_lk_hero_class_present(self) -> None:
        assert "lk-hero" in self._read(), "lk-hero CSS class missing from docs/index.md"

    def test_quickstart_link_present(self) -> None:
        assert "quickstart.md" in self._read(), (
            "Quickstart link missing from docs/index.md hero"
        )

    def test_github_link_present(self) -> None:
        assert "https://github.com/Jessinra/Lorekeeper" in self._read(), (
            "GitHub link missing from docs/index.md"
        )

    def test_pip_install_present(self) -> None:
        assert "pip install lorekeeper" in self._read(), (
            "pip install command missing from docs/index.md"
        )

    def test_readme_include_present(self) -> None:
        assert "include-markdown" in self._read(), (
            "README include-markdown directive missing from docs/index.md"
        )

    def test_readme_itself_exists(self) -> None:
        assert (REPO / "README.md").exists(), (
            "README.md missing — docs/index.md includes it via include-markdown"
        )


# ===========================================================================
# 5. GitHub Actions deploy workflow tests
# ===========================================================================


class TestDeployWorkflow:
    """docs.yml must copy both landing artefacts and run mkdocs build."""

    def _read(self) -> str:
        return (REPO / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")

    def test_workflow_file_exists(self) -> None:
        assert (REPO / ".github" / "workflows" / "docs.yml").exists()

    def test_mkdocs_build_step_present(self) -> None:
        assert "mkdocs build --site-dir build/docs" in self._read(), (
            "mkdocs build step missing from docs.yml"
        )

    def test_landing_html_copied(self) -> None:
        assert "cp landing/index.html build/index.html" in self._read(), (
            "landing/index.html copy step missing from docs.yml"
        )

    def test_config_json_copied(self) -> None:
        assert "cp landing/config.json build/landing/config.json" in self._read(), (
            "landing/config.json copy step missing from docs.yml"
        )

    def test_deploys_to_gh_pages(self) -> None:
        assert "gh-pages" in self._read(), (
            "Workflow must deploy to gh-pages branch"
        )

    def test_triggers_on_main_push(self) -> None:
        content = self._read()
        assert "push" in content and "main" in content, (
            "Workflow must trigger on push to main"
        )
