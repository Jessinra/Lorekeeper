# Linter Decisions

Settled during LKPR-25 (2026-05-23). Revisit if the codebase changes significantly.

---

## Python — Ruff

**Tool**: Ruff (`uv run ruff check src tests`)  
**Config**: `pyproject.toml` → `[tool.ruff.lint]`

### Selected rulesets

| Code  | Ruleset               | Rationale                                                                     |
| ----- | --------------------- | ----------------------------------------------------------------------------- | ---------------- |
| `E`   | pycodestyle errors    | Canonical style errors (indentation, spacing)                                 |
| `W`   | pycodestyle warnings  | Whitespace warnings (trailing whitespace, blank lines)                        |
| `F`   | pyflakes              | Undefined names, unused imports/variables                                     |
| `I`   | isort                 | Import ordering — keeps diffs clean, removes merge conflicts                  |
| `B`   | flake8-bugbear        | Catches likely bugs and design issues (mutable defaults, bare `except`, etc.) |
| `UP`  | pyupgrade             | Modernises syntax for Python 3.11+ (`datetime.UTC`, `X                        | Y` unions, etc.) |
| `C4`  | flake8-comprehensions | Simplifies list/set/dict comprehensions                                       |
| `RUF` | Ruff-specific         | Ruff-native rules — unused `noqa`, ambiguous unicode, unpacked unused vars    |

### Explicit ignores

| Code     | Reason                                                                                                                            |
| -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `B008`   | FastAPI uses `File()` / `Depends()` in function argument defaults — this is the intended pattern, not a bug                       |
| `RUF003` | En-dashes (`–`) and multiplication signs (`×`) appear in math comments and documentation strings — intentional unicode, not typos |

### Not selected (and why)

| Code                  | Reason skipped                                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `D` (pydocstring)     | Docstring coverage would require a large retrofitting effort. Internal codebase, not a library. Add later if needed. |
| `N` (pep8-naming)     | No naming convention violations in existing code; rule is noisy on single-char vars in math/algo code                |
| `ANN` (annotations)   | mypy strict mode already enforces type annotations with better error messages                                        |
| `S` (bandit/security) | Low-risk internal tool; adds noise on `subprocess`, `tempfile`, etc. Add if surface area grows                       |
| `PTH` (pathlib)       | Existing code mixes `os.path` and `pathlib`; migration has no correctness benefit right now                          |

### Line length

100 characters. Rationale: standard Python projects use 88 (Black) or 79 (PEP 8), but 100 gives more room for readable SQL strings and nested dict literals in tests without forcing ugly line-breaks.

---

## Python — mypy

**Tool**: mypy (`uv run mypy src`)  
**Config**: `pyproject.toml` → `[tool.mypy]`

- `strict = true` — full strictness: no implicit `Any`, no untyped defs, checks return types
- `ignore_missing_imports = true` — third-party stubs (e.g. `lancedb`) are incomplete; errors here are noise

**Not in pre-commit**: mypy takes ~10–30s on a cold run because it needs to type-check all imports including heavy third-party libs. It runs in CI and should be run locally before pushing (`uv run mypy src`), but blocking every commit on it makes the feedback loop too slow.

---

## JavaScript — Biome (lint) + Prettier (format)

**Tool**: Biome lint (`npx @biomejs/biome lint src/lorekeeper/dashboard/static/js/`)  
**Tool**: Prettier format (`npx prettier@3.5.3 --check src/lorekeeper/dashboard/static/js/**/*.js`)  
**Config**: `biome.json` + `.prettierrc.json`

### Why Biome + Prettier instead of one tool

| Criteria      | Biome (lint only)        | Prettier (format)        |
| ------------- | ------------------------ | ------------------------ |
| Zero npm deps | ✅ Single binary via npx | ✅ Single binary via npx |
| Speed         | Fast (Rust)              | Fast (JS)                |
| Config        | One `biome.json`         | One `.prettierrc.json`   |
| Linting       | ✅ Covers all            | ❌ Not applicable        |
| Formatting    | ✅ Supported             | ✅ More opinionated      |

Previously Biome handled both linting and formatting (`biome check`). The dashboard JS is plain browser-side JavaScript (no TypeScript, no build step). Biome covers linting quickly, and Prettier handles formatting with a stricter, more consistent rule set. Running `biome lint` + `prettier --check` instead of `biome check` avoids conflicts between the two formatters.

### Biome settings

- `recommended: true` — catches common bugs, enforces modern idioms
- `useIterableCallbackReturn: off` — disabled because `.forEach()` callbacks that don't return are idiomatic DOM manipulation code (not a bug)
- `indentStyle: tab` — consistent with existing codebase
- `quoteStyle: double` — consistent with existing code

### Prettier settings (`.prettierrc.json`)

- `printWidth: 100` — matches the repo's readability target
- `useTabs: true`, `tabWidth: 4` — matches existing codebase
- `semi: true`, `singleQuote: false` — consistent with existing code
- `trailingComma: all` — cleaner diffs
- Markdown override: `useTabs: false`, `tabWidth: 2`, `proseWrap: preserve`

---

## Markdown — Prettier

**Tool**: Prettier (`while IFS= read -r -d '' f; do [ -f "$f" ] && printf '%s\0' "$f"; done < <(git ls-files -z '*.md') | xargs -0 npx --yes prettier@3.5.3 --check --prose-wrap preserve`)  
**Config**: `.prettierrc.json`

### Why Prettier over markdownlint-cli2

| Criteria           | Prettier                                          | markdownlint-cli2                                               |
| ------------------ | ------------------------------------------------- | --------------------------------------------------------------- |
| Table formatting   | ✅ Normalizes pipe tables                         | ❌ Lints tables, but does not reflow them well                  |
| Paragraph wrapping | ✅ `proseWrap: preserve` avoids aggressive reflow | ✅ Configurable, but no full formatter                          |
| Zero runtime drift | ✅ One pinned `npx` invocation                    | ✅ One pinned `npx` invocation                                  |
| Developer friction | ✅ One formatter for all markdown                 | ⚠️ Rules-first, but still needs separate formatting conventions |

The repo's markdown pain is mostly mechanical formatting drift: tables, list spacing, trailing whitespace, and inconsistent code fence layout. Prettier is the simplest tool that actually rewrites the content into a consistent shape without introducing a separate lint-vs-format split. `proseWrap: preserve` keeps intentional hard-wrapped docs readable.

### Settings

- `printWidth: 100` — matches the repo's existing readability target
- `proseWrap: preserve` — avoids reflowing prose paragraphs in docs like `CLAUDE.md`

---

## Pre-commit Hook

**File**: `.githooks/pre-commit`  
**Installed by**: `bash scripts/setup.sh` (run once per clone)

The hook runs:

1. `uv run ruff check src tests` — Python lint
2. `npx --yes @biomejs/biome lint src/lorekeeper/dashboard/static/js/` — JS lint (Biome)
3. `npx --yes prettier@3.5.3 --check "src/lorekeeper/dashboard/static/js/**/*.js"` — JS formatting (Prettier)
4. `npx --yes prettier@3.5.3 --check "*.md"` — Markdown formatting (Prettier)

**mypy is not in the hook** (see note above). Run it manually before pushing: `uv run mypy src`.

---

## Open Questions Resolved

| Question                                     | Decision                                                                                             |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Should `ruff format --check` be in the hook? | No — `ruff format` is not configured, only `ruff check`. Add if we adopt Black-style autoformatting. |
| Should `uv run mypy` be in the hook?         | No — too slow. Run manually before push.                                                             |
| ESLint or Biome for JS?                      | Biome — zero deps, fast, covers lint + format in one tool.                                           |
| Pre-commit framework vs manual shell hook?   | Manual shell hook — simpler, no Python package dependency, no config drift.                          |
