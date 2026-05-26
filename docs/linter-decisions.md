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
- `ignore_missing_imports = true` — third-party stubs (mem0, chromadb) are incomplete; errors here are noise

**Not in pre-commit**: mypy takes ~10–30s on a cold run because it needs to type-check all imports including heavy third-party libs. It runs in CI and should be run locally before pushing (`uv run mypy src`), but blocking every commit on it makes the feedback loop too slow.

---

## JavaScript/TypeScript — Biome

**Tool**: Biome (`npx @biomejs/biome check src/lorekeeper/dashboard/static/js/`)  
**Config**: `biome.json`

### Why Biome over ESLint

| Criteria        | Biome                    | ESLint                           |
| --------------- | ------------------------ | -------------------------------- |
| Zero npm deps   | ✅ Single binary via npx | ❌ Needs `node_modules/` install |
| Speed           | Fast (Rust)              | Slower                           |
| Config          | One `biome.json`         | Multiple config files + plugins  |
| Formatting      | Built-in                 | Needs Prettier                   |
| JS-only project | ✅ Good fit              | Overkill for plain JS            |

The dashboard JS is plain browser-side JavaScript (no TypeScript, no build step). Biome covers linting + formatting in one tool with no `package.json` / `node_modules` needed in the repo.

### Settings

- `recommended: true` — catches common bugs, enforces modern idioms
- `useIterableCallbackReturn: off` — disabled because `.forEach()` callbacks that don't return are idiomatic DOM manipulation code (not a bug)
- `indentStyle: tab` — consistent with existing codebase
- `quoteStyle: double` — consistent with existing code

---

## Pre-commit Hook

**File**: `.githooks/pre-commit`  
**Installed by**: `bash scripts/setup.sh` (run once per clone)

The hook runs:

1. `uv run ruff check src tests` — Python lint
2. `npx --yes @biomejs/biome check src/lorekeeper/dashboard/static/js/` — JS lint
3. `uv run pytest tests/ -q --tb=short` — test suite

**mypy is not in the hook** (see note above). Run it manually before pushing: `uv run mypy src`.

**Bypass** (emergency only): `git commit --no-verify`

---

## Open Questions Resolved

| Question                                     | Decision                                                                                             |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Should `ruff format --check` be in the hook? | No — `ruff format` is not configured, only `ruff check`. Add if we adopt Black-style autoformatting. |
| Should `uv run mypy` be in the hook?         | No — too slow. Run manually before push.                                                             |
| ESLint or Biome for JS?                      | Biome — zero deps, fast, covers lint + format in one tool.                                           |
| Pre-commit framework vs manual shell hook?   | Manual shell hook — simpler, no Python package dependency, no config drift.                          |
