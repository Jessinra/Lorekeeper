#!/usr/bin/env python3
"""
Layer-0 BLOCKER detector — runs in pre-commit on staged diffs only.

Detects Lorekeeper-specific BLOCKER-tier patterns BEFORE they reach a PR:
  B001 — print() call in src/lorekeeper/ (breaks MCP stdout transport)
  B002 — mem0.add() without infer=False (triggers silent LLM rewrite of content)
  B003 — os.environ["KEY"] direct access outside config.py (fails on missing key)
  B004 — bare `except:` or `except Exception: pass` (swallows all errors silently)
  B005 — hardcoded secret pattern (password/token/secret = "..." in non-test code)
  B006 — TODO(security) or FIXME(security) comment left in staged code
  B007 — Direct sqlite3 cursor execute with f-string (SQL injection risk)

Design principles:
  - STAGED DIFF ONLY — only checks lines added/modified in this commit
  - Zero external deps — pure Python stdlib (ast, re, pathlib, subprocess)
  - Fast — <200ms on any realistic staged set
  - False-positive aware — each rule has explicit exclusions
  - Exit 1 on any BLOCKER finding — blocks the commit
  - Exit 0 on clean — silent, no noise
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
)

# Files where print() is intentional (CLI tools, entry points)
PRINT_ALLOWLIST = {
    "src/lorekeeper/cli/",
    "scripts/",
    "tests/",
    "docs/",
}

# Files where mem0.add without infer=False is the expected pattern (test fixtures)
MEM0_ALLOWLIST = {
    "tests/",
    "docs/",
}

# Files where hardcoded strings in password/token lines are expected (test fixtures)
SECRET_ALLOWLIST = {
    "tests/",
    "docs/",
}


# ── Data types ─────────────────────────────────────────────────────────────────


@dataclass
class Finding:
    rule_id: str
    file: str
    line: int
    col: int
    message: str
    context: str
    fix: str

    def format(self) -> str:
        return (
            f"\n  🚫 {self.rule_id}  {self.file}:{self.line}\n"
            f"     {self.message}\n"
            f"     Context: {self.context.strip()}\n"
            f"     Fix:     {self.fix}\n"
        )


# ── Staged diff helpers ────────────────────────────────────────────────────────


def get_staged_diff() -> list[tuple[str, int, str]]:
    """
    Returns (filepath, line_number, line_content) for every ADDED line in the staged diff.
    Only lines starting with '+' (excluding diff header '+++') are returned.
    """
    try:
        raw = subprocess.check_output(
            ["git", "diff", "--cached", "--unified=0", "--diff-filter=d"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []

    result: list[tuple[str, int, str]] = []
    current_file = ""
    current_line = 0

    for line in raw.splitlines():
        # New file in diff
        if line.startswith("+++ b/"):
            current_file = line[6:]  # strip "+++ b/"
            current_line = 0
        elif line.startswith("@@ "):
            # Parse @@ -a,b +c,d @@ — extract new file start line
            m = re.search(r"\+(\d+)", line)
            if m:
                current_line = int(m.group(1)) - 1  # will be incremented on first '+'
        elif line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            content = line[1:]  # strip leading '+'
            result.append((current_file, current_line, content))
        elif not line.startswith("-"):
            # Context line — advance line counter
            current_line += 1

    return result


def is_in_allowlist(filepath: str, allowlist: set[str]) -> bool:
    return any(filepath.startswith(prefix) for prefix in allowlist)


# ── Rules ──────────────────────────────────────────────────────────────────────


def check_b001_print_in_src(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B001: print() call in src/lorekeeper/ breaks MCP stdout JSON-RPC transport."""
    findings: list[Finding] = []
    pattern = re.compile(r"(?<![a-zA-Z_])print\s*\(")

    for filepath, lineno, content in lines:
        if not filepath.startswith("src/lorekeeper/"):
            continue
        if is_in_allowlist(filepath, PRINT_ALLOWLIST):
            continue
        if content.strip().startswith("#"):
            continue
        if pattern.search(content):
            findings.append(
                Finding(
                    rule_id="B001",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message="print() in src/lorekeeper/ corrupts the MCP stdout JSON-RPC transport.",  # noqa: E501
                    context=content,
                    fix="Use structlog: log = structlog.get_logger()  →  log.debug('msg', key=val)",
                )
            )
    return findings


def check_b002_mem0_add_without_infer(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B002: mem0.add() without infer=False triggers a silent background LLM call."""
    findings: list[Finding] = []
    by_file: dict[str, list[tuple[int, str]]] = {}
    for filepath, lineno, content in lines:
        if is_in_allowlist(filepath, MEM0_ALLOWLIST):
            continue
        by_file.setdefault(filepath, []).append((lineno, content))

    for filepath, file_lines in by_file.items():
        for i, (lineno, content) in enumerate(file_lines):
            if content.strip().startswith("#"):
                continue
            if re.search(r"_mem0\.add\s*\(|mem0\.add\s*\(", content):
                # Check if infer=False appears in this line or next 5 added lines
                window = [c for _, c in file_lines[i : i + 6]]
                combined = " ".join(window)
                if "infer=False" not in combined:
                    findings.append(
                        Finding(
                            rule_id="B002",
                            file=filepath,
                            line=lineno,
                            col=0,
                            message="mem0.add() without infer=False — triggers silent LLM rewrite of stored content.",  # noqa: E501
                            context=content,
                            fix="Always pass infer=False: self._mem0.add(text, ..., infer=False)",
                        )
                    )
    return findings


def check_b003_environ_direct_access(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B003: os.environ["KEY"] raises KeyError at runtime on missing env var."""
    findings: list[Finding] = []
    pattern = re.compile(r'os\.environ\[[\"\']')

    for filepath, lineno, content in lines:
        if "test" in filepath or "config.py" in filepath or "settings.py" in filepath:
            continue
        if content.strip().startswith("#"):
            continue
        if pattern.search(content):
            findings.append(
                Finding(
                    rule_id="B003",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message='os.environ["KEY"] raises KeyError on missing env var — crashes server at startup.',  # noqa: E501
                    context=content,
                    fix='Use os.environ.get("KEY") or declare in lorekeeper/config.py as a Pydantic Settings field.',  # noqa: E501
                )
            )
    return findings


def check_b004_bare_except(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B004: bare except: or except Exception: pass swallows all errors silently."""
    findings: list[Finding] = []
    bare_except = re.compile(r"^\s*except\s*:\s*$")
    except_pass = re.compile(r"^\s*except\s+\w[\w.,\s]*:\s*pass\s*$")

    for filepath, lineno, content in lines:
        if "tests/" in filepath:
            continue
        if content.strip().startswith("#"):
            continue
        if bare_except.match(content) or except_pass.match(content):
            findings.append(
                Finding(
                    rule_id="B004",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message="Bare except: or except Exception: pass — swallows all errors, makes bugs invisible.",  # noqa: E501
                    context=content,
                    fix="Catch a specific exception and log it: except SomeError as e: log.warning('msg', error=str(e))",  # noqa: E501
                )
            )
    return findings


def check_b005_hardcoded_secret(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B005: hardcoded credentials in source code."""
    findings: list[Finding] = []
    pattern = re.compile(
        r'(?i)(password|secret|api_key|token|private_key|access_key)\s*=\s*["\'][^"\']{6,}["\']'
    )
    placeholder = re.compile(
        r"(?i)(your[-_]|example|placeholder|changeme|xxx|fake|test|dummy|mock|\*\*\*)"
    )

    for filepath, lineno, content in lines:
        if is_in_allowlist(filepath, SECRET_ALLOWLIST):
            continue
        if content.strip().startswith("#"):
            continue
        m = pattern.search(content)
        if m:
            if placeholder.search(m.group(0)):
                continue
            findings.append(
                Finding(
                    rule_id="B005",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message="Hardcoded credential detected — never commit secrets to source.",
                    context=re.sub(r'(["\'])[^"\']+(["\'])', r"\1***\2", content),
                    fix="Use environment variables or Pydantic Settings. Remove from all git history if committed.",  # noqa: E501
                )
            )
    return findings


def check_b006_security_todo(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B006: TODO(security) / FIXME(security) — unresolved security debt."""
    findings: list[Finding] = []
    pattern = re.compile(r"(?i)(TODO|FIXME)\s*\(\s*security\s*\)")

    for filepath, lineno, content in lines:
        if pattern.search(content):
            findings.append(
                Finding(
                    rule_id="B006",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message="Security TODO/FIXME left in staged code — must be resolved before merge.",  # noqa: E501
                    context=content,
                    fix="Fix the underlying security concern, or file a tracked ticket and remove the inline marker.",  # noqa: E501
                )
            )
    return findings


def check_b007_fstring_sql(lines: list[tuple[str, int, str]]) -> list[Finding]:
    """B007: f-string inside execute() → SQL injection risk."""
    findings: list[Finding] = []
    pattern = re.compile(r'\.execute\s*\(\s*f["\']')

    for filepath, lineno, content in lines:
        if "tests/" in filepath:
            continue
        if content.strip().startswith("#"):
            continue
        if pattern.search(content):
            findings.append(
                Finding(
                    rule_id="B007",
                    file=filepath,
                    line=lineno,
                    col=0,
                    message="f-string inside SQL execute() — SQL injection vulnerability.",
                    context=content,
                    fix="Use parameterized queries: cursor.execute('SELECT ... WHERE id = ?', (value,))",  # noqa: E501
                )
            )
    return findings


# ── Runner ─────────────────────────────────────────────────────────────────────

RULES = [
    check_b001_print_in_src,
    check_b002_mem0_add_without_infer,
    check_b003_environ_direct_access,
    check_b004_bare_except,
    check_b005_hardcoded_secret,
    check_b006_security_todo,
    check_b007_fstring_sql,
]


def main() -> int:
    staged = get_staged_diff()
    if not staged:
        return 0  # Nothing staged — silent pass

    all_findings: list[Finding] = []
    for rule in RULES:
        all_findings.extend(rule(staged))

    if not all_findings:
        return 0  # Clean — silent

    print("\n🚨  BLOCKER patterns detected — commit blocked\n")
    print(
        "   These are Lorekeeper-specific BLOCKERs that corrupt the server"
        " or break the MCP contract.\n"
        "   Fix them before committing.\n"
    )

    by_rule: dict[str, list[Finding]] = {}
    for f in all_findings:
        by_rule.setdefault(f.rule_id, []).append(f)

    for _rule_id, rule_findings in sorted(by_rule.items()):
        for finding in rule_findings:
            print(finding.format())

    print(f"  ❌  {len(all_findings)} BLOCKER(s) found across {len(by_rule)} rule(s)")
    print("  Fix all BLOCKERs above, then re-stage and commit.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
