---
applyTo: "src/lorekeeper/dashboard/static/js/*.js"
---

# Dashboard JavaScript Guidelines

## Scope

Apply these rules to the static dashboard JavaScript.

## Review focus

- Reuse the existing API helper and shared utilities.
- Avoid raw `fetch` wrappers when the project already has a helper.
- Keep DOM updates and data loading easy to follow.
- Prefer small modules over ad hoc duplication.
- Avoid console noise and unhandled promise failures.

## UI behavior

- Preserve the existing no-framework dashboard approach.
- Keep error states visible and user-facing.
- Do not introduce new dependencies for small UI changes.
- Watch for stale state, race conditions, and repeated network calls.

## Testing / verification

- If a change affects the dashboard flow, check the rendered behavior.
- Keep code consistent with the current style and naming in the static JS tree.

## Additional rules

For UI primitives/components (primitives.js), see [dashboard-primitives.instructions.md](./dashboard-primitives.instructions.md) — covers reusability, constants, `DESIGN_TOKENS`, separation of logic from config, and component architecture conventions.
