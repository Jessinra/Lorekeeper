#!/usr/bin/env python3
"""
CI guard: every SKILL.md in assets/skills/ must have valid YAML frontmatter
with required fields: name, description, version.

Exit 0 — all skills valid.
Exit 1 — one or more skills missing required fields; prints actionable diff.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "src" / "lorekeeper" / "assets" / "skills"

REQUIRED_FIELDS = ("name", "description", "version")


def extract_frontmatter(text: str) -> dict[str, str] | None:
    """Parse YAML frontmatter block (between --- delimiters). Returns dict or None."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    block = m.group(1)
    result: dict[str, str] = {}
    for line in block.splitlines():
        # Match simple key: value (no nested YAML needed)
        kv = re.match(r"^(\w+)\s*:\s*(.+)$", line.strip())
        if kv:
            result[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return result


def check_skill(skill_dir: Path) -> list[str]:
    """Return list of error strings for a skill directory. Empty = valid."""
    skill_md = skill_dir / "SKILL.md"
    errors: list[str] = []

    if not skill_md.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]

    text = skill_md.read_text()
    fm = extract_frontmatter(text)

    if fm is None:
        return [f"{skill_dir.name}/SKILL.md: missing YAML frontmatter (no --- block)"]

    for field in REQUIRED_FIELDS:
        if field not in fm or not fm[field]:
            errors.append(
                f"{skill_dir.name}/SKILL.md: frontmatter missing required field '{field}'"
            )

    # name must match directory name
    if "name" in fm and fm["name"] != skill_dir.name:
        errors.append(
            f"{skill_dir.name}/SKILL.md: frontmatter 'name: {fm['name']}' "
            f"does not match directory name '{skill_dir.name}'"
        )

    return errors


def main() -> int:
    if not SKILLS_DIR.exists():
        print(f"✅  No skills directory found at {SKILLS_DIR} — skipping.")
        return 0

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())

    if not skill_dirs:
        print("✅  No skills found — skipping.")
        return 0

    all_errors: list[str] = []
    for skill_dir in skill_dirs:
        all_errors.extend(check_skill(skill_dir))

    if all_errors:
        print("❌  Skill validation FAILED")
        print(
            f"   {len(all_errors)} error(s) found across {len(skill_dirs)} skill(s):\n"
        )
        for err in all_errors:
            print(f"   - {err}")
        print(
            "\n   Each SKILL.md must have a YAML frontmatter block with: "
            + ", ".join(f"'{f}'" for f in REQUIRED_FIELDS)
        )
        return 1

    print(
        f"✅  All {len(skill_dirs)} skill(s) valid: "
        + ", ".join(d.name for d in skill_dirs)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
