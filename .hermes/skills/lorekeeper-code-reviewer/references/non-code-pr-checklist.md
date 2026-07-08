# Non-Code PR Checklist

When the pre-check confirms this PR touches NO files under `src/lorekeeper/` (docs, landing, CI, configs, tests), all runtime BLOCKER patterns are N/A. Use this checklist instead.

## Link correctness (marketing / docs PRs)

- Every `<a href>` points to a real destination — no `href="#"` unless an intentional placeholder
- External links point to the correct repo/domain
- Internal links use the correct subpath (`/Lorekeeper/docs/...` not bare `/docs/`)
- Distinctly-labeled nav items point to distinct destinations

## Asset file existence (docsite PRs)

- Logo, favicon, extra CSS files in `mkdocs.yml` exist on disk under `docs/`
- All nav `.md` files in `mkdocs.yml` exist under `docs/`
- Landing page `<img src>` resolves at the deployed URL — verify the copy step exists in the deploy workflow
- **Reuse the official asset** — reference `docs/assets/logo.svg`, not a hand-rolled inline SVG

## Config / manifest validity

- YAML files parse without error
- JSON files have expected schema shape
- Schema changes are backward-compatible

## Deploy workflow correctness (CI/CD PRs)

- Artifact staging order: MkDocs built first, then landing page copied on top
- All required artefacts copied (landing HTML, config JSON)
- No third-party actions where pure git push would suffice
- Commit message `[skip ci]` on deploy commits prevents infinite CI loops

## Deploy URL contract compliance

| URL                                                         | Expected content      |
| ----------------------------------------------------------- | --------------------- |
| `https://jessinra.github.io/Lorekeeper/`                    | `landing/index.html`  |
| `https://jessinra.github.io/Lorekeeper/docs/`               | MkDocs site root      |
| `https://jessinra.github.io/Lorekeeper/landing/config.json` | `landing/config.json` |

## License / brand consistency

- Landing page, docs footer, `pyproject.toml` agree on license type (MIT vs Apache-2.0)
- Brand palette `#8a7bb5` consistent across landing CSS, MkDocs `extra_css`, dark-mode

## Install commands must match PyPI package name

The PyPI package is `lorekeeper-mcp` (see `pyproject.toml` `[project] name`), NOT `lorekeeper`. Grep every `pip install` in the diff:

```bash
grep -n "^name" pyproject.toml                         # source of truth
grep -rn "pip install lorekeeper" landing/ docs/ README.md
```

Verify ALL surfaces: terminal mockup, copy-to-clipboard JS, and get-started steps. Usually 3+ copies per page.

## MkDocs palette validation

**Every palette entry must set `primary: custom` and `accent: custom`.** An auto-detect entry without these silently defaults to indigo. Check:

```python
# Every entry must have the key:
for i, pal in enumerate(palettes):
    assert "primary" in pal, f"palette[{i}] missing 'primary' key"
    assert pal["primary"] == "custom"
```

## attr_list extension required for button syntax

If docs use `{ .md-button }` syntax, `attr_list` must be in `mkdocs.yml` `markdown_extensions:`. Without it, button syntax renders as literal text. Build won't fail — only visual inspection catches it.

## Dead links to exclude_docs pages

`mkdocs build --strict` does NOT fail on links to excluded pages — it only logs INFO. After a strict build, grep for `excluded from the built site` and `unrecognized relative link`. Each is a real dead link on the published site.

Fix: repoint to GitHub source URL instead of relative path.

## Command-name consistency

Within a how-to / quickstart page, the command name must be consistent across ALL steps. If step 1 says `lorekeeper setup`, steps 2, 4, and troubleshooting should NOT say `setup.sh`.

## Test file integrity

- New test files pass `ruff check` — bot-authored PRs may skip pre-commit
- Tests don't depend on network/browser/server unless explicitly marked E2E
- All test files in the diff exist in the working tree — `git status D` must be restored
