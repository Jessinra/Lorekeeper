# Maintainability & Simplicity — BLOCKER Patterns

These aren't style preferences — they're **merge-blocking** because complexity compounds. Every overly-clever or tightly-coupled change added today becomes someone else's debugging headache tomorrow.

## Complexity review (check every PR)

- **Is the simplest thing that works?** — If there's a straightforward 10-line approach and a generalized 50-line approach, the 10-line one wins unless there's an actual (not hypothetical) second consumer. Premature generality is the #1 maintainability killer.

- **Can a new person understand this in one read?** — Magic numbers, non-obvious state transitions, exception handling that silently swallows, and mutation-in-place that affects callers all fail this test. If you re-read the diff and have to think about what it does, that's a sign.

- **How many files does one logical change touch?** — A single new feature that requires edits to models.py, store, orchestrator, schema, handler, server, test, and docs = 8 files. If a future PR needs to add another feature with a similar shape, will it also touch 8 files? That's a design problem, not a feature cost.

- **Would a config change or a code change?** — Tunable numbers, type lists, and supported backends should be config-driven (env var, YAML, Settings class) so future changes don't require a code PR. Hardcoded lists of 3+ items that are likely to grow are a BLOCKER.

- **Does it introduce a new "thing to remember"?** — Every new pattern, convention, or unwritten rule added to the codebase increases cognitive load. A new decorator, a new registration pattern, a new base class — is it justified by actual duplication, or is it speculative?

## BLOCKER patterns

```python
# BLOCKER — premature configurability (speculative generality)
class SearchScorer:
    def __init__(self, weights: dict[str, float] = None):
        self.weights = weights or {"semantic": 0.45, "keyword": 0.30, ...}

# BETTER — flat, obvious, changeable via constants
SEMANTIC_WEIGHT = 0.45
KEYWORD_WEIGHT = 0.30
# If it actually needs to be configurable → env var with Settings
```

```python
# BLOCKER — two concerns, one function
def process_and_send(data):
    validated = validate(data)
    enriched = enrich(validated)
    response = api.send(enriched)
    log_metric("send", response.status)
    return response

# BETTER — split, each testable independently
def process(data):
    return enrich(validate(data))

def send_processed(data):
    response = api.send(data)
    log_metric("send", response.status)
    return response
```

```python
# BLOCKER — state mutation with invisible side effects
def add_tag(memory: dict, tag: str) -> dict:
    memory.setdefault("tags", []).append(tag)
    return memory  # ← mutated the caller's dict

# BETTER — explicit
def with_tag(memory: dict, tag: str) -> dict:
    return {**memory, "tags": memory.get("tags", []) + [tag]}
```

```python
# BLOCKER — throwing away information
try:
    result = external_api.call()
except Exception:
    return None  # ← caller doesn't know WHY it failed

# BETTER — preserve the what
try:
    result = external_api.call()
except TimeoutError:
    raise ServiceUnavailable("external_api timed out")
except ValidationError:
    raise InvalidRequest("external_api rejected input")
```

## Questions every reviewer should ask

- "If I come back to this in 6 months, will I understand why it's done this way?"
- "Does this change make the next similar change faster or slower?"
- "Is there a simpler version that solves today's problem without solving for next year's?"
- "Will a new contributor to the project feel confident modifying this code?"
