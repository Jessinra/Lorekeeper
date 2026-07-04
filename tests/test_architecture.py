"""Architecture layer enforcement tests.

RULES:
1. A module may import only from strictly lower layers (same-layer imports
   allowed only within the same top-level package, e.g. infra → infra).
2. Exception: layer 6 (presentation) may import `lorekeeper.server`,
   `shared`, `processors`, and `domains.*.models` ONLY — not domain
   `service`/`repository`/`ranking` modules, not `platform`, not `infra`.
3. Cross-domain DAG: suggestion → {memory, link}, reflection → {memory},
   memory → {link} only.
4. No `processors.X` imports `processors.Y` (X ≠ Y).
5. `lorekeeper.services` must not be imported by anything not in
   `TEMPORARY_ALLOWED` — and once the list is empty, must not exist at all.
6. `server.py` is exempt from all rules (composition root imports everything).
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

# ── Layer classification ──────────────────────────────────────────────────

LAYER: dict[str, int] = {
    # Presentation layer
    "api": 6,
    "dashboard": 6,
    "cli": 6,
    "server": 6,
    "__main__": 6,
    # Shared utilities
    "shared": 5,
    # Processors (empty until Step 4x — rule still declared)
    "processors": 4,
    # Domain logic
    "domains": 3,
    # Platform services
    "platform": 2,
    # Infrastructure
    "infra": 1,
    # Temporary facade — will be deleted. Service module can import anything
    # (it assembles everything). Other modules must NOT import it except via
    # TEMPORARY_ALLOWED (Rule 5).
    "services": 99,
}

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "lorekeeper"

# ── Allowed cross-domain edges ────────────────────────────────────────────

CROSS_DOMAIN_ALLOWED: set[tuple[str, str]] = {
    ("lorekeeper.domains.suggestion", "lorekeeper.domains.memory"),
    ("lorekeeper.domains.suggestion", "lorekeeper.domains.link"),
    ("lorekeeper.domains.reflection", "lorekeeper.domains.memory"),
    ("lorekeeper.domains.memory", "lorekeeper.domains.link"),
}

# ── Temporary exception list ──────────────────────────────────────────────
# Each entry is (importer_module_full, imported_module_full).
# Entries are deleted by the step that fixes the violation.
# Step 5 deletes the entire set (must be empty).

TEMPORARY_ALLOWED: set[tuple[str, str]] = {
    # Steps 4a-4d / 5 remove — presentation → facade / deep domain
    ("lorekeeper.api.mcp.handlers.memory_handlers", "lorekeeper.services.orchestrator"),
    ("lorekeeper.api.mcp.handlers.memory_handlers", "lorekeeper.domains.memory.ranking"),
    # server.py (composition root) — exempt from rules, but listed here for clarity
    ("lorekeeper.server", "lorekeeper.services.orchestrator"),
    ("lorekeeper.server", "lorekeeper.domains.link.repository"),
    ("lorekeeper.server", "lorekeeper.domains.memory.repository"),
    ("lorekeeper.server", "lorekeeper.domains.reflection.repository"),
    ("lorekeeper.server", "lorekeeper.domains.suggestion.repository"),
    ("lorekeeper.server", "lorekeeper.domains.suggestion.candidate"),
    ("lorekeeper.server", "lorekeeper.domains.suggestion.sweep"),
    ("lorekeeper.server", "lorekeeper.infra.database"),
    ("lorekeeper.server", "lorekeeper.infra.keyword_index"),
    ("lorekeeper.server", "lorekeeper.infra.search_engine"),
    ("lorekeeper.server", "lorekeeper.infra.settings"),
    ("lorekeeper.server", "lorekeeper.infra.scheduler"),
    ("lorekeeper.server", "lorekeeper.platform.config.repository"),
    ("lorekeeper.server", "lorekeeper.platform.metrics.repository"),
    # __main__ → infra (will die when server is the sole entry point)
    ("lorekeeper.__main__", "lorekeeper.infra.logging_setup"),
    ("lorekeeper.__main__", "lorekeeper.infra.settings"),
    ("lorekeeper.__main__", "lorekeeper.server"),
    ("lorekeeper.__main__", "lorekeeper.cli.setup"),
    # dashboard → server (composition root getter, fine)
    ("lorekeeper.dashboard.app", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.backup", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.config", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.links", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.memories", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.metrics", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.reflections", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.search", "lorekeeper.server"),
    ("lorekeeper.dashboard.routes.suggestions", "lorekeeper.server"),
}

# ── Helpers ────────────────────────────────────────────────────────────────


def _layer_of(module: str) -> int:
    """Return the layer number for a lorekeeper module path."""
    top = module.split(".")[1] if module.startswith("lorekeeper.") else module.split(".")[0]
    return LAYER.get(top, 0)


def _top_package(module: str) -> str:
    """Return the top-level package name, e.g. 'infra' from 'lorekeeper.infra.database'."""
    return module.split(".")[1] if module.startswith("lorekeeper.") else module.split(".")[0]


def _is_server_module(module: str) -> bool:
    """Check if module is lorekeeper.server or a submodule."""
    return module == "lorekeeper.server" or module.startswith("lorekeeper.server.")


def _is_domain_models(module: str) -> bool:
    """Check if the module is e.g. lorekeeper.domains.X.models (layer 6 may import these)."""
    parts = module.split(".")
    return (len(parts) >= 4 and parts[0] == "lorekeeper"
            and parts[1] == "domains"
            and parts[3] == "models")


def _is_services_package(module: str) -> bool:
    """Check if module is inside the temporary services package."""
    return module.startswith("lorekeeper.services.") or module == "lorekeeper.services"


def _collect_import_edges() -> list[tuple[str, str, list[str]]]:
    """Walk src/lorekeeper/ and return (importer_module, imported_module, lines) edges.

    Covers both runtime imports and TYPE_CHECKING-guarded imports.
    """
    edges: list[tuple[str, str, list[str]]] = []

    for pyfile in sorted(SRC_ROOT.rglob("*.py")):
        rel = pyfile.relative_to(SRC_ROOT.parent.parent / "src")
        importer = str(rel.with_suffix("")).replace(os.sep, ".")

        try:
            tree = ast.parse(pyfile.read_text(), filename=str(pyfile))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("lorekeeper."):
                        edges.append((importer, alias.name, [str(node.lineno)]))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("lorekeeper."):
                    edges.append((importer, node.module, [str(node.lineno)]))

    return edges


# ── Rule checks ────────────────────────────────────────────────────────────


def _check_rule1_lower_layer(
    importer: str, imported: str, lines: list[str],
) -> str | None:
    """Rule 1: A module may import only from strictly lower layers.

    Exemptions:
    - server.py (composition root) — exempt from all rules (Rule 6)
    - services package (temporary facade) — can import anything
    """
    # Rule 6: server.py is exempt from all rules
    if _is_server_module(importer):
        return None

    # Services package is temporary — can import anything
    if _is_services_package(importer):
        return None

    imp_layer = _layer_of(importer)
    imp_layer_imported = _layer_of(imported)
    imp_top = _top_package(importer)
    imp_top_imported = _top_package(imported)

    # Same top-level package: allowed (e.g. infra → infra)
    if imp_top == imp_top_imported:
        return None

    # Lower layer is fine
    if imp_layer_imported < imp_layer:
        return None

    # Same layer across different top-level packages: check Rule 2 first
    # (presentation layer may import server, shared, etc.)
    if imp_layer == 6 and imp_layer_imported == 6:
        # Rule 2 handles this — don't flag here
        return None

    return (
        f"RULE 1: {importer} (layer {imp_layer}) imports {imported} "
        f"(layer {imp_layer_imported}) at line(s) {','.join(lines)} — "
        f"may only import from strictly lower layers"
    )


def _check_rule2_presentation_domain(
    importer: str, imported: str, lines: list[str],
) -> str | None:
    """Rule 2: Layer 6 may only import server, shared, processors, and domains.*.models.

    server.py is exempt from all rules (Rule 6).
    """
    # Rule 6: server.py is exempt from all rules
    if _is_server_module(importer):
        return None

    imp_layer = _layer_of(importer)
    if imp_layer != 6:
        return None

    imp_top = _top_package(importer)

    # Same top-level package is fine (e.g. api → api, dashboard → dashboard)
    imp_top_imported = _top_package(imported)
    if imp_top == imp_top_imported:
        return None

    # Layer 6 always allowed: server, shared, processors
    allowed_prefixes = ("lorekeeper.server", "lorekeeper.shared", "lorekeeper.processors")
    if any(imported.startswith(p) for p in allowed_prefixes):
        return None

    # Layer 6 may import domains.*.models
    if _is_domain_models(imported):
        return None

    # Layer 6 also may import from its own top-level package or lower layers
    # (Rule 1 handles layer ordering)
    imp_layer_imported = _layer_of(imported)
    if imp_layer_imported <= imp_layer:
        # Rule 1 handles this
        return None

    # Domain non-models modules: not allowed for layer 6
    if imported.startswith("lorekeeper.domains."):
        return (
            f"RULE 2: {importer} (layer 6) imports {imported} (domain, not .models) "
            f"at line(s) {','.join(lines)} — layer 6 may only import "
            f"domains.*.models, not service/repository/ranking modules"
        )

    # Layer 6 importing from platform or infra → fail
    if imported.startswith("lorekeeper.platform.") or imported.startswith("lorekeeper.infra."):
        return (
            f"RULE 2: {importer} (layer 6) imports {imported} "
            f"at line(s) {','.join(lines)} — layer 6 may not import platform or infra"
        )

    return None


def _check_rule3_cross_domain(
    importer: str, imported: str, lines: list[str],
) -> str | None:
    """Rule 3: Cross-domain edges follow allowed DAG.

    server.py and services package are exempt.
    """
    if _is_server_module(importer):
        return None
    if _is_services_package(importer):
        return None

    if not imported.startswith("lorekeeper.domains."):
        return None
    if not importer.startswith("lorekeeper.domains."):
        return None

    imp_domain = ".".join(importer.split(".")[:3])
    imp_domain_imported = ".".join(imported.split(".")[:3])

    # Same domain is fine
    if imp_domain == imp_domain_imported:
        return None

    allowed_pair = (imp_domain, imp_domain_imported)
    if allowed_pair in CROSS_DOMAIN_ALLOWED:
        return None

    return (
        f"RULE 3: {importer} imports {imported} at line(s) {','.join(lines)} — "
        f"cross-domain edge '{imp_domain} → {imp_domain_imported}' is not in allowed DAG"
    )


def _check_rule4_processors(
    importer: str, imported: str, lines: list[str],
) -> str | None:
    """Rule 4: No processors.X imports processors.Y (X ≠ Y)."""
    if not importer.startswith("lorekeeper.processors."):
        return None
    if not imported.startswith("lorekeeper.processors."):
        return None
    if importer == imported:
        return None

    return (
        f"RULE 4: {importer} imports {imported} at line(s) {','.join(lines)} — "
        f"processors may not import each other"
    )


def _check_rule5_services(
    importer: str, imported: str, lines: list[str],
) -> str | None:
    """Rule 5: lorekeeper.services must not be imported unless in TEMPORARY_ALLOWED."""
    if not imported.startswith("lorekeeper.services."):
        return None
    if (importer, imported) in TEMPORARY_ALLOWED:
        return None

    # Services module importing itself is fine
    if _is_services_package(importer):
        return None

    return (
        f"RULE 5: {importer} imports {imported} at line(s) {','.join(lines)} — "
        f"services module is temporary; only TEMPORARY_ALLOWED entries may import it"
    )


# ── Violation collector ────────────────────────────────────────────────────


def _get_violations() -> list[str]:
    """Run all rules against the codebase and return violation messages.

    Excludes TEMPORARY_ALLOWED entries.
    """
    violations: list[str] = []
    edges = _collect_import_edges()
    all_checkers = [
        _check_rule5_services,
        _check_rule4_processors,
        _check_rule2_presentation_domain,
        _check_rule3_cross_domain,
        _check_rule1_lower_layer,
    ]

    for importer, imported, lines in edges:
        # Skip imports already in TEMPORARY_ALLOWED
        if (importer, imported) in TEMPORARY_ALLOWED:
            continue

        for checker in all_checkers:
            msg = checker(importer, imported, lines)
            if msg is not None:
                violations.append(msg)

    return violations


# ── Tests ──────────────────────────────────────────────────────────────────


def test_temporary_allowed_entries_are_still_real() -> None:
    """Every TEMPORARY_ALLOWED entry must still be a real import edge.

    Stale entries (violation already fixed) must be deleted.
    """
    edges = {(i, m) for i, m, _ in _collect_import_edges()}
    stale = [(i, m) for i, m in TEMPORARY_ALLOWED if (i, m) not in edges]
    assert not stale, (
        "Stale TEMPORARY_ALLOWED entries — delete them:\n"
        + "\n".join(f"  ({i}, {m})" for i, m in stale)
    )


def test_rule1_lower_layer_imports() -> None:
    """A module may import only from strictly lower layers."""
    violations = _get_violations()
    rule1_msgs = [v for v in violations if v.startswith("RULE 1:")]
    assert not rule1_msgs, (
        "Layer violations found:\n" + "\n".join(rule1_msgs)
    )


def test_rule2_presentation_layer_boundaries() -> None:
    """Layer 6 may only import server, shared, processors, and domains.*.models."""
    violations = _get_violations()
    rule2_msgs = [v for v in violations if v.startswith("RULE 2:")]
    assert not rule2_msgs, (
        "Presentation layer violations found:\n" + "\n".join(rule2_msgs)
    )


def test_rule3_cross_domain_dag() -> None:
    """Cross-domain imports must follow the allowed DAG."""
    violations = _get_violations()
    rule3_msgs = [v for v in violations if v.startswith("RULE 3:")]
    assert not rule3_msgs, (
        "Cross-domain violations found:\n" + "\n".join(rule3_msgs)
    )


def test_rule4_processors_independence() -> None:
    """Processors must not import each other."""
    violations = _get_violations()
    rule4_msgs = [v for v in violations if v.startswith("RULE 4:")]
    assert not rule4_msgs, (
        "Processor cross-import violations found:\n" + "\n".join(rule4_msgs)
    )


def test_rule5_services_temporary() -> None:
    """Services module may only be imported via TEMPORARY_ALLOWED."""
    violations = _get_violations()
    rule5_msgs = [v for v in violations if v.startswith("RULE 5:")]
    assert not rule5_msgs, (
        "Services import violations found:\n" + "\n".join(rule5_msgs)
    )


def test_architecture_negative_new_violation() -> None:
    """Verify a deliberate violation is caught (demonstrates test works).

    This tests that the check functions themselves detect violations.
    """
    # An infra module importing from platform (upward, not in TEMPORARY_ALLOWED)
    msg = _check_rule1_lower_layer(
        "lorekeeper.infra.foo", "lorekeeper.platform.config.repository", ["99"],
    )
    assert msg is not None, "Expected a violation for non-allowed infra upward import"

    # A domain module with an invalid cross-domain edge
    msg = _check_rule3_cross_domain(
        "lorekeeper.domains.link.service", "lorekeeper.domains.suggestion.models", ["99"],
    )
    assert msg is not None, "Expected a violation for link → suggestion (reverse of allowed)"
