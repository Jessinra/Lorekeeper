#!/usr/bin/env python3
"""
CI guard: every @mcp.tool() in server.py must have a ### `lore_<name>` section
in README.md or docs/api-reference.md.

Exit 0 — all tools documented.
Exit 1 — one or more tools missing from both files; prints actionable diff.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SERVER = ROOT / "src" / "lorekeeper" / "server.py"
README = ROOT / "README.md"
API_REF = ROOT / "docs" / "api-reference.md"


def extract_tool_names(server_text: str) -> list[str]:
    """Return all MCP tool names registered via @mcp.tool()."""
    names = []
    lines = server_text.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # @mcp.tool(name="lore_foo") — single-line explicit name
        m = re.search(r'@mcp\.tool\(name=[\"\'](\w+)[\"\']', stripped)
        if m:
            names.append(m.group(1))
            continue

        # @mcp.tool(\n  name="lore_foo", ...) — multi-line, name on next lines
        if stripped.startswith("@mcp.tool(") and "name=" not in stripped:
            for j in range(i + 1, min(i + 5, len(lines))):
                m = re.search(r'name=[\"\'](\w+)[\"\']', lines[j])
                if m:
                    names.append(m.group(1))
                    break
            else:
                # Fallback: resolve from following function def
                for j in range(i + 1, min(i + 5, len(lines))):
                    m = re.match(r"\s*(?:async )?def (\w+)\(", lines[j])
                    if m:
                        names.append(m.group(1))
                        break
            continue

        # @mcp.tool() — no name, resolve from following function def
        if re.search(r"@mcp\.tool\(\s*\)", stripped):
            for j in range(i + 1, min(i + 5, len(lines))):
                m = re.match(r"\s*(?:async )?def (\w+)\(", lines[j])
                if m:
                    names.append(m.group(1))
                    break

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            unique.append(n)
    return unique


def extract_documented_tools(readme_text: str) -> set[str]:
    """Return all tool names that have a ## or ### `lore_<name>` heading in the given text."""
    return set(re.findall(r"#{2,3}\s+`(lore_\w+)`", readme_text))


def main() -> int:
    server_text = SERVER.read_text()
    readme_text = README.read_text()
    api_ref_text = API_REF.read_text() if API_REF.exists() else ""

    registered = extract_tool_names(server_text)
    documented = extract_documented_tools(readme_text) | extract_documented_tools(api_ref_text)

    missing = [t for t in registered if t not in documented]

    if missing:
        print("❌  MCP tool documentation check FAILED")
        print(
            "   The following tools are registered in server.py but missing from README.md "
            "or docs/api-reference.md:\n"
        )
        for t in missing:
            print(f"   - {t}  →  add a '### `{t}`' section to README.md or docs/api-reference.md")
        print(
            "\n   See the PR checklist (.github/pull_request_template.md) "
            "for the full doc requirements."
        )
        return 1

    print(f"✅  All {len(registered)} MCP tools documented: {', '.join(sorted(registered))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
