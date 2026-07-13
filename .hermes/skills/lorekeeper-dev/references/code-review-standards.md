# Code Review Standards

Apply these when reviewing PRs or self-reviewing before pushing. Flag issues at 3 levels: 🔴 **Blocker** (security/correctness), 🟡 **Should-fix** (maintainability/performance), 🟢 **Nit** (style).

## General Engineering Principles

- **Single Responsibility** — each function/class does one thing
- **DRY** — no duplicated logic; extract shared utilities
- **YAGNI** — no speculative code
- **PR size** — under ~400 lines; ask for splits if larger
- **No magic numbers** — literals extracted into named constants
- **Self-documenting naming** — code readable without comments
- **Max nesting depth: 3** — use early returns
- **No commented-out dead code**

## Clean Code

- Functions are verbs, classes are nouns
- Booleans prefixed: `is_valid`, `has_permission`, `can_retry`
- No abbreviations unless universal (`url`, `id`, `db` OK; `usrNm` ❌)
- Function length ≤ 30 lines; decompose if longer
- Comments explain _why_, not _what_
- TODOs include a ticket ref: `# TODO(LKPR-N): description`
- Errors never silently swallowed — no bare `except: pass`

## Python-Specific

- Type hints on all public functions (enforced by `mypy`)
- f-strings over `.format()` or `%`
- `enumerate()` over `range(len(...))`
- Context managers for file/DB/network resources
- `pathlib.Path` over `os.path` string manipulation
- Dataclasses or Pydantic models for structured data
- No mutable default arguments
- No bare `except:` — catch specific exceptions
- No `eval()`, `exec()`, or `pickle.loads()` on untrusted input
- SQL uses parameterized queries
- `subprocess` uses list args, never `shell=True` with user input

## JavaScript-Specific

- `const` by default, `let` only when needed — never `var`
- `===` always — no `==` loose equality
- Destructuring for object/array access
- Optional chaining `?.` and nullish coalescing `??`
- `async/await` over raw `.then()` chains
- `Promise.all()` for parallel async
- No floating promises
- No `innerHTML` with unsanitized user content (XSS risk 🔴)
- No `eval()` or `new Function()` with dynamic strings

## Security (🔴 all blockers)

- No secrets in code — API keys/passwords from env vars only
- All external input validated/sanitized
- New packages checked via `pip audit` / `npm audit`
- Least privilege for DB/file/API access

## Cross-cutting constraints

When a PR adds a new cross-cutting constraint: enumerate ALL data-access paths, apply constraint to each, guard both shared and scoped branches, guard write paths, and add regression test for isolation.

## Config/script injection safety

Always escape injected values (`json.dumps()` for YAML, `shlex.quote()` for shell). Test with adversarial input.

## Stateful UI completeness

State invalidation on refresh, dropdown options in sync with state.

## DB migration correctness

Use schema introspection (`PRAGMA`), not string-matching. Migration must be idempotent.

## Performance

No N+1 queries, pagination used, large collections streamed, timeouts set on external calls, structured logging (not `print()`).
