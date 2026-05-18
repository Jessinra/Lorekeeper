#!/usr/bin/env bash
# Lorekeeper setup — install deps, register MCP server, install skills.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_DIR/assets/skills"
SKILLS_DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
SETTINGS="${CLAUDE_SETTINGS:-$HOME/.claude/settings.json}"
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

# ── 4. Register MCP server in ~/.claude/settings.json ─────────────────────────
title "Registering MCP server..."
uv run --directory "$REPO_DIR" python - "$SETTINGS" "$REPO_DIR" "$DATA_DIR" <<'PYEOF'
import json, pathlib, sys

settings_path = pathlib.Path(sys.argv[1])
repo_dir      = sys.argv[2]
data_dir      = sys.argv[3]

settings = {}
if settings_path.exists():
    with open(settings_path) as f:
        settings = json.load(f)

settings.setdefault("mcpServers", {})

entry = {
    "command": "uv",
    "args": ["run", "--directory", repo_dir, "lorekeeper"],
    "env": {"LORE_DATA_DIR": data_dir},
}

if "lorekeeper" in settings["mcpServers"]:
    existing = settings["mcpServers"]["lorekeeper"]
    if existing == entry:
        print("  already registered — no change")
    else:
        settings["mcpServers"]["lorekeeper"] = entry
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print("  updated existing entry in " + str(settings_path))
else:
    settings["mcpServers"]["lorekeeper"] = entry
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)
    print("  registered in " + str(settings_path))
PYEOF
info "MCP server registered"

# ── 5. Install Claude Code skills ─────────────────────────────────────────────
title "Installing skills..."
if [ ! -d "$SKILLS_SRC" ]; then
    warn "No assets/skills/ directory found — skipping skill installation"
else
    mkdir -p "$SKILLS_DST"
    installed=0
    for skill_dir in "$SKILLS_SRC"/*/; do
        [ -f "$skill_dir/SKILL.md" ] || continue
        skill_name=$(basename "$skill_dir")
        dst="$SKILLS_DST/$skill_name"
        mkdir -p "$dst"
        cp "$skill_dir/SKILL.md" "$dst/SKILL.md"
        info "  $skill_name"
        (( installed++ )) || true
    done
    info "$installed skills installed to $SKILLS_DST"
fi

# ── 6. Optional: migrate from v1 ─────────────────────────────────────────────
if [ -n "${V1_JSON:-}" ] && [ -f "$V1_JSON" ]; then
    title "Migrating from v1..."
    uv run --directory "$REPO_DIR" python scripts/migrate_from_json.py \
        --source "$V1_JSON" --dest "$DATA_DIR"
    info "Migration complete"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Setup complete.${NC} Restart Claude Code to activate the MCP server."
echo ""
echo "Start the dashboard:"
echo "  uv run --directory $REPO_DIR lorekeeper-dashboard"
echo "  → http://127.0.0.1:${LORE_DASH_PORT:-7777}"
echo ""
echo "Migrate from v1 (optional):"
echo "  V1_JSON=/path/to/memories.json bash $REPO_DIR/scripts/setup.sh"
