#!/bin/bash
# lorekeeper-setup — install repo-local skills into global Hermes skills directory
# Run this once per machine, or after adding/updating skills in .hermes/skills/
#
# Maps repo skills to global categories:
#   lorekeeper-dev     → software-development/
#   backlog-management → software-development/
#   after-changes      → software-development/
#   lorekeeper-pm      → product/
#   ui-ux-pro-max      → creative/

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_SRC="$REPO_DIR/.hermes/skills"
SKILLS_DST="$HOME/.hermes/skills"

echo "Installing lorekeeper repo skills → global Hermes skills..."
echo "  Source: $SKILLS_SRC"
echo "  Target: $SKILLS_DST"
echo ""

for skill_dir in "$SKILLS_SRC"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"

    case "$skill_name" in
        lorekeeper-dev|after-changes) category="software-development" ;;
        backlog-management)           category="software-development" ;;
        commit-convention)            category="software-development" ;;
        lorekeeper-pm)                category="product" ;;
        ui-ux-pro-max)                category="creative" ;;
        *)                            category="misc" ;;
    esac

    mkdir -p "$SKILLS_DST/$category"
    target_path="$SKILLS_DST/$category/$skill_name"

    if [ -L "$target_path" ] && [ "$(readlink "$target_path")" = "$skill_dir" ]; then
        echo "  ✓ $category/$skill_name — already linked"
    elif [ -d "$target_path" ]; then
        rm -rf "$target_path"
        ln -sf "$skill_dir" "$target_path"
        echo "  ⟳ $category/$skill_name — replaced with symlink"
    else
        ln -sf "$skill_dir" "$target_path"
        echo "  + $category/$skill_name → linked"
    fi
done

echo ""
echo "Done. Run 'skills_list | grep lorekeeper' to verify."

# ── Install git hooks ────────────────────────────────────────────────────────
echo ""
echo "Installing git hooks..."
HOOKS_SRC="$REPO_DIR/scripts/hooks"
HOOKS_DST="$REPO_DIR/.git/hooks"

if [ -d "$HOOKS_SRC" ]; then
    for hook_file in "$HOOKS_SRC"/*; do
        [ -f "$hook_file" ] || continue
        hook_name="$(basename "$hook_file")"
        target="$HOOKS_DST/$hook_name"
        cp "$hook_file" "$target"
        chmod +x "$target"
        echo "  + git hook: $hook_name installed"
    done
else
    echo "  (no hooks dir found at scripts/hooks/)"
fi

echo ""
echo "All done. Git hooks active — author name/email and [LKPR-N] are now enforced."