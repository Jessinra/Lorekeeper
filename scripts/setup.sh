#!/usr/bin/env bash
# Lorekeeper setup — install deps, register MCP server, install skills, install git hooks.
# Run once per clone. Re-run after adding/updating skills in .hermes/skills/.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_DIR/.hermes/skills"
SKILLS_DST="${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}"
DATA_DIR="${LORE_DATA_DIR:-$HOME/.lorekeeper}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
title() { echo -e "\n${BOLD}$*${NC}"; }

echo -e "${BOLD}Lorekeeper setup${NC}"
echo "repo: $REPO_DIR"
echo "data: $DATA_DIR"

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
title "Checking prerequisites..."

command -v uv &>/dev/null || err "uv required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
info "uv: $(uv --version)"

# uv manages Python — confirm it can resolve 3.11+
uv python find 3.11 &>/dev/null || err "Python 3.11 not found. Run: uv python install 3.11"
info "Python 3.11: $(uv python find 3.11)"

# ── 2. Install Python dependencies ───────────────────────────────────────────
title "Installing dependencies..."
uv sync --extra dashboard --directory "$REPO_DIR" --quiet
info "Dependencies installed (including dashboard extras)"

# ── 3. Create data directory ──────────────────────────────────────────────────
title "Setting up data directory..."
mkdir -p "$DATA_DIR"
info "Data directory ready: $DATA_DIR"

# ── 4. Register MCP server in ~/.hermes/config.yaml ──────────────────────────
title "Registering MCP server..."
CONFIG="$HOME/.hermes/config.yaml"
if [ -f "$CONFIG" ] && grep -q "lorekeeper" "$CONFIG"; then
    info "MCP server already registered in $CONFIG"
else
    warn "MCP server not found in $CONFIG — add it manually:"
    echo ""
    echo "  mcp_servers:"
    echo "    lorekeeper:"
    echo "      command: uv"
    echo "      args: [run, --directory, $REPO_DIR, lorekeeper]"
    echo "      env:"
    echo "        LORE_DATA_DIR: $DATA_DIR"
    echo ""
fi

# ── 5. Install Hermes skills ──────────────────────────────────────────────────
title "Installing Hermes skills..."

# Maps repo skill names to global Hermes skill categories
skill_category() {
    case "$1" in
        lorekeeper-dev|after-changes|backlog-management|commit-convention) echo "software-development" ;;
        lorekeeper-pm)                                                      echo "product" ;;
        ui-ux-pro-max)                                                      echo "creative" ;;
        *)                                                                  echo "misc" ;;
    esac
}

if [ ! -d "$SKILLS_SRC" ]; then
    warn "No .hermes/skills/ directory found — skipping skill installation"
else
    for skill_dir in "$SKILLS_SRC"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name="$(basename "$skill_dir")"
        category="$(skill_category "$skill_name")"

        mkdir -p "$SKILLS_DST/$category"
        target_path="$SKILLS_DST/$category/$skill_name"

        if [ -L "$target_path" ] && [ "$(readlink "$target_path")" = "$skill_dir" ]; then
            info "$category/$skill_name — already linked"
        elif [ -d "$target_path" ]; then
            rm -rf "$target_path"
            ln -sf "$skill_dir" "$target_path"
            info "$category/$skill_name — replaced with symlink"
        else
            ln -sf "$skill_dir" "$target_path"
            info "$category/$skill_name → linked"
        fi
    done
fi

# ── 6. Install git hooks ──────────────────────────────────────────────────────
title "Installing git hooks..."
HOOKS_SRC="$REPO_DIR/scripts/hooks"
HOOKS_DST="$REPO_DIR/.git/hooks"

if [ -d "$HOOKS_SRC" ]; then
    for hook_file in "$HOOKS_SRC"/*; do
        [ -f "$hook_file" ] || continue
        hook_name="$(basename "$hook_file")"
        target="$HOOKS_DST/$hook_name"
        cp "$hook_file" "$target"
        chmod +x "$target"
        info "git hook: $hook_name installed"
    done
else
    warn "No hooks dir found at scripts/hooks/ — skipping"
fi

info "Git hooks active — author name/email and [LKPR-N] are now enforced"

# ── 7. Optional: migrate from v1 ─────────────────────────────────────────────
if [ -n "${V1_JSON:-}" ] && [ -f "$V1_JSON" ]; then
    title "Migrating from v1..."
    uv run --directory "$REPO_DIR" python scripts/migrate_from_json.py \
        --source "$V1_JSON" --dest "$DATA_DIR"
    info "Migration complete"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Setup complete.${NC} Restart Hermes/Claude to activate the MCP server."
echo ""
echo "Start the dashboard:"
echo "  uv run --directory $REPO_DIR lorekeeper-dashboard"
echo "  → http://127.0.0.1:${LORE_DASH_PORT:-7777}"
echo ""
echo "Migrate from v1 (optional):"
echo "  V1_JSON=/path/to/memories.json bash $REPO_DIR/scripts/setup.sh"
