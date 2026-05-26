#!/usr/bin/env bash
# Lorekeeper setup — smart agent detection + MCP/prompt/skills injection.
# Run once per clone. Re-run after updates to sync agent configurations.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${PWD}"
SKILLS_DEV="$REPO_DIR/.hermes/skills"         # dev skills → Hermes only (with category)
SKILLS_USER="$REPO_DIR/assets/skills"          # user skills → all agents (flat)
PROMPT_FILE="$REPO_DIR/assets/prompts/lorekeeper-agent-prompt.md"
DATA_DIR="${LORE_DATA_DIR:-$HOME/.lorekeeper}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "  ${GREEN}✓${NC} $*"; }
warn()  { echo -e "  ${YELLOW}!${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
title() { echo -e "\n${BOLD}$*${NC}"; }

echo -e "${BOLD}Lorekeeper setup${NC}"
echo "repo: $REPO_DIR"
echo "data: $DATA_DIR"

# ── 1. Prerequisites ───────────────────────────────────────────────────────────
title "Checking prerequisites..."

command -v uv &>/dev/null || err "uv required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
info "uv: $(uv --version)"

uv python find 3.11 &>/dev/null || err "Python 3.11 not found. Run: uv python install 3.11"
info "Python 3.11: $(uv python find 3.11)"

# ── 2. Install Python dependencies ────────────────────────────────────────────
title "Installing dependencies..."
uv sync --group dev --extra dashboard --directory "$REPO_DIR" --quiet
info "Dependencies installed (including dashboard extras)"

# ── 3. Create data directory ──────────────────────────────────────────────────
title "Setting up data directory..."
mkdir -p "$DATA_DIR"
info "Data directory ready: $DATA_DIR"

# ── 4. Install git hooks ──────────────────────────────────────────────────────
title "Installing git hooks..."
HOOKS_SRC="$REPO_DIR/.githooks"
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
    warn "No .githooks/ directory found — skipping"
fi

info "Git hooks active — author name/email, [LKPR-N], lint, and tests enforced"

# ══════════════════════════════════════════════════════════════════════════════
# ── Helper functions ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Extract version from assets/prompts/lorekeeper-agent-prompt.md frontmatter
_prompt_version() {
    awk 'BEGIN{n=0} /^---$/{n++; next} n==1 && /^version:/{gsub(/^version: */,""); print; exit}' \
        "$PROMPT_FILE" 2>/dev/null || echo "unknown"
}

# Extract installed Lorekeeper version stamp from a target prompt file
_installed_version() {
    local file="$1"
    [ -f "$file" ] || { echo ""; return; }
    grep -m1 '<!-- lorekeeper:' "$file" 2>/dev/null \
        | sed 's/.*lorekeeper: \([^ |]*\).*/\1/' || echo ""
}

# Extract version field from a skill's SKILL.md frontmatter
_skill_version() {
    local file="$1"
    [ -f "$file" ] || { echo ""; return; }
    awk 'BEGIN{n=0} /^---$/{n++; next} n==1 && /^version:/{gsub(/^version: */,""); print; exit}' \
        "$file" 2>/dev/null || echo ""
}

# Inject lorekeeper MCP entry into a Hermes YAML config.
# Prints: added | skip | missing
# Uses regex-based YAML manipulation (no PyYAML dep) to correctly insert inside mcp_servers block.
_inject_mcp_yaml() {
    local config="$1"
    [ -f "$config" ] || { echo "missing"; return; }
    local result setup_ver
    setup_ver="$(_prompt_version)"
    result=$(python3 - "$config" "$REPO_DIR" "$DATA_DIR" "$setup_ver" <<'PYEOF'
import sys, re

config_path, repo_dir, data_dir, setup_ver = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

with open(config_path) as f:
    content = f.read()

# Check for lorekeeper key specifically under the mcp_servers block (not a broad file search)
mcp_match = re.search(r'^(mcp_servers:\s*\n)((?:[ \t]+[^\n]*\n)*)', content, re.MULTILINE)
if mcp_match and re.search(r'^[ \t]+lorekeeper\s*:', mcp_match.group(0), re.MULTILINE):
    print("skip")
    sys.exit(0)

new_entry = (
    "  lorekeeper:\n"
    f"    command: uv\n"
    f"    args: [run, --directory, {repo_dir}, lorekeeper]\n"
    "    env:\n"
    f"      LORE_DATA_DIR: {data_dir}\n"
    f"      LOREKEEPER_SETUP_VERSION: {setup_ver}\n"
)

if mcp_match:
    # Insert at the end of the existing mcp_servers block (inside it, not after)
    insert_pos = mcp_match.end()
    content = content[:insert_pos] + new_entry + content[insert_pos:]
else:
    content = content.rstrip() + "\nmcp_servers:\n" + new_entry

with open(config_path, "w") as f:
    f.write(content)
print("added")
PYEOF
)
    echo "$result"
}

# Inject lorekeeper MCP entry into a JSON config (Claude Code / Cursor).
# Prints: added | skip | error
_inject_mcp_json() {
    local config="$1"
    mkdir -p "$(dirname "$config")"
    [ -f "$config" ] || echo '{}' > "$config"
    local result setup_ver
    setup_ver="$(_prompt_version)"
    result=$(python3 - "$config" "$REPO_DIR" "$DATA_DIR" "$setup_ver" <<'PYEOF'
import sys, json, os, shutil

config_path, repo_dir, data_dir, setup_ver = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

try:
    with open(config_path) as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"error: {config_path} contains invalid JSON ({e}) — fix it manually before re-running setup", file=sys.stderr)
    sys.exit(1)

if "lorekeeper" in data.get("mcpServers", {}):
    print("skip")
    sys.exit(0)

backup = config_path + ".setup-bak"
shutil.copy2(config_path, backup)
try:
    data.setdefault("mcpServers", {})["lorekeeper"] = {
        "command": "uv",
        "args": ["run", "--directory", repo_dir, "lorekeeper"],
        "env": {"LORE_DATA_DIR": data_dir, "LOREKEEPER_SETUP_VERSION": setup_ver},
    }
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.remove(backup)
except Exception as e:
    shutil.move(backup, config_path)
    print(f"error: failed to write {config_path}: {e}", file=sys.stderr)
    sys.exit(1)
print("added")
PYEOF
)
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        warn "MCP injection failed for $config — see error above"
        echo "error"
        return
    fi
    echo "$result"
}

# Inject/replace ## Lorekeeper section in a target prompt file.
# Prints: added | updated | skip | missing
_inject_prompt() {
    local target="$1"
    [ -f "$target" ] || { echo "missing"; return; }
    local src_ver installed_ver
    src_ver="$(_prompt_version)"
    installed_ver="$(_installed_version "$target")"
    [ "$installed_ver" = "$src_ver" ] && { echo "skip"; return; }
    python3 - "$target" "$PROMPT_FILE" <<'PYEOF'
import re, sys

target_path, prompt_path = sys.argv[1], sys.argv[2]

# Extract prompt body (strip YAML frontmatter)
with open(prompt_path) as f:
    raw = f.read()
parts = raw.split('---', 2)
body = parts[2].strip() if len(parts) >= 3 else raw.strip()

# Load target and replace/append ## Lorekeeper section
with open(target_path) as f:
    content = f.read()

if re.search(r'(?:^|\n)## Lorekeeper\b', content):
    # Strip the section. If Lorekeeper is at the very start, the pattern matches
    # with no leading \n — use lstrip() after to avoid a leading blank line.
    content = re.sub(r'(?:^|\n)## Lorekeeper\b.*?(?=\n## |\Z)', '', content, flags=re.DOTALL)
    content = content.lstrip('\n')

content = content.rstrip() + '\n\n' + body + '\n'

with open(target_path, 'w') as f:
    f.write(content)
PYEOF
    if [ -n "$installed_ver" ]; then
        echo "updated ($installed_ver → $src_ver)"
    else
        echo "added ($src_ver)"
    fi
}

# Install user-facing skills (assets/skills/) to a target directory.
# Uses copies so the target doesn't depend on this repo's path.
# Per-skill progress lines go to stderr (shown on terminal).
# Echoes a summary token to stdout for capture: synced | "updated N" | "installed N" | none
_install_user_skills() {
    local dst="$1"
    [ -d "$SKILLS_USER" ] || { echo "  → (no assets/skills/)" >&2; echo "none"; return; }
    mkdir -p "$dst"
    local any=0 n_updated=0 n_installed=0
    for skill_dir in "$SKILLS_USER"/*/; do
        [ -d "$skill_dir" ] || continue
        any=1
        local skill_name src_ver installed_ver target
        skill_name="$(basename "$skill_dir")"
        src_ver="$(_skill_version "$skill_dir/SKILL.md")"
        target="$dst/$skill_name"
        installed_ver="$(_skill_version "$target/SKILL.md")"
        if [ -n "$src_ver" ] && [ "$installed_ver" = "$src_ver" ]; then
            echo "  → $skill_name — already up to date ($src_ver)" >&2
        else
            rm -rf "$target"
            cp -r "$skill_dir" "$target"
            if [ -n "$installed_ver" ] && [ "$installed_ver" != "$src_ver" ]; then
                echo "  ✓ $skill_name — updated ($installed_ver → $src_ver)" >&2
                n_updated=$((n_updated + 1))
            else
                echo "  ✓ $skill_name — installed ($src_ver)" >&2
                n_installed=$((n_installed + 1))
            fi
        fi
    done
    if [ "$any" -eq 0 ]; then
        echo "  → (no skills found)" >&2
        echo "none"
    elif [ "$n_updated" -gt 0 ] && [ "$n_installed" -gt 0 ]; then
        echo "updated $n_updated, installed $n_installed"
    elif [ "$n_updated" -gt 0 ]; then
        echo "updated $n_updated"
    elif [ "$n_installed" -gt 0 ]; then
        echo "installed $n_installed"
    else
        echo "synced"
    fi
    return 0
}

# Install dev skills (.hermes/skills/) to Hermes with category subdirs (symlinks).
_install_dev_skills_hermes() {
    local dst="$1"
    [ -d "$SKILLS_DEV" ] || { echo "  → (no .hermes/skills/)"; return; }
    mkdir -p "$dst"
    _skill_category() {
        case "$1" in
            lorekeeper-dev|after-changes|backlog-management|commit-convention) echo "software-development" ;;
            lorekeeper-pm) echo "product" ;;
            ui-ux-pro-max) echo "creative" ;;
            github-pr) echo "software-development" ;;
            *) echo "misc" ;;
        esac
    }
    for skill_dir in "$SKILLS_DEV"/*/; do
        [ -d "$skill_dir" ] || continue
        local skill_name cat target_dir target_path
        skill_name="$(basename "$skill_dir")"
        cat="$(_skill_category "$skill_name")"
        target_dir="$dst/$cat"
        target_path="$target_dir/$skill_name"
        mkdir -p "$target_dir"
        if [ -L "$target_path" ] && [ "$(readlink "$target_path")" = "$skill_dir" ]; then
            echo "  → $cat/$skill_name — already linked"
        else
            [ -e "$target_path" ] && rm -rf "$target_path"
            ln -sf "$skill_dir" "$target_path"
            echo "  ✓ $cat/$skill_name → linked"
        fi
    done
}

# Format summary cell: add/skip/missing/error → display string
_cell() {
    # Returns a plain-text token for summary table cells (no ANSI codes).
    # Color is applied at print time but padding is computed on visible chars only.
    case "$1" in
        added*)            printf "✓ added" ;;
        updated\ *|updated) printf "✓ updated" ;;
        "updated "*|"installed "*) printf "✓ %s" "$1" ;;
        synced)            printf "→ synced" ;;
        none)              printf "→ none" ;;
        skip)              printf "→ skip" ;;
        missing)           printf "— N/A" ;;
        error)             printf "✗ failed" ;;
        "")                printf "—" ;;
        *)                 printf "%s" "$1" ;;
    esac
}

# ══════════════════════════════════════════════════════════════════════════════
# ── 5. Agent detection ─────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

title "Scanning for agents..."

# Parallel arrays — one entry per detected agent
AGENT_NAMES=()   # display name
AGENT_TYPES=()   # hermes_main | hermes_profile | claude | cursor
AGENT_DIRS=()    # primary config directory for agent

# Hermes main
if [ -d "$HOME/.hermes" ]; then
    AGENT_NAMES+=("Hermes (main)")
    AGENT_TYPES+=("hermes_main")
    AGENT_DIRS+=("$HOME/.hermes")
fi

# Hermes profiles
if [ -d "$HOME/.hermes/profiles" ]; then
    for profile_dir in "$HOME/.hermes/profiles"/*/; do
        [ -d "$profile_dir" ] || continue
        profile_name="$(basename "$profile_dir")"
        AGENT_NAMES+=("Hermes (profile: $profile_name)")
        AGENT_TYPES+=("hermes_profile")
        AGENT_DIRS+=("$profile_dir")
    done
fi

# Claude Code
if [ -d "$HOME/.claude" ] || [ -f "$HOME/.claude/settings.json" ]; then
    AGENT_NAMES+=("Claude Code")
    AGENT_TYPES+=("claude")
    AGENT_DIRS+=("$HOME/.claude")
fi

# Cursor
if [ -d "$HOME/.cursor" ] || [ -f "$HOME/.cursor/mcp.json" ]; then
    AGENT_NAMES+=("Cursor")
    AGENT_TYPES+=("cursor")
    AGENT_DIRS+=("$HOME/.cursor")
fi

if [ "${#AGENT_NAMES[@]}" -eq 0 ]; then
    warn "No agents detected. Skipping agent configuration."
    warn "Install Hermes (~/.hermes/), Claude Code (~/.claude/), or Cursor (~/.cursor/) first."
else
    echo ""
    echo "Found ${#AGENT_NAMES[@]} agent(s):"
    for i in "${!AGENT_NAMES[@]}"; do
        echo "  ☑ ${AGENT_NAMES[$i]}  — ${AGENT_DIRS[$i]}"
    done
    echo ""
    printf "Configure these? [Y/n] "
    read -r CONFIRM </dev/tty || CONFIRM="Y"
    case "${CONFIRM:-Y}" in
        [nN]*) echo "Skipping agent configuration."; AGENT_NAMES=() ;;
    esac
fi

# ══════════════════════════════════════════════════════════════════════════════
# ── 6. Configure each agent ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

SUMMARY_NAMES=()
SUMMARY_MCP=()
SUMMARY_PROMPT=()
SUMMARY_SKILLS=()

for i in "${!AGENT_NAMES[@]}"; do
    name="${AGENT_NAMES[$i]}"
    type="${AGENT_TYPES[$i]}"
    dir="${AGENT_DIRS[$i]}"

    echo ""
    echo -e "  ${BOLD}$name${NC}"

    # ── MCP injection ──────────────────────────────────────────────────────
    printf "    MCP:    "
    case "$type" in
        hermes_main|hermes_profile)
            mcp_result="$(_inject_mcp_yaml "$dir/config.yaml")"
            ;;
        claude)
            mcp_result="$(_inject_mcp_json "$dir/settings.json")"
            ;;
        cursor)
            mcp_result="$(_inject_mcp_json "$dir/mcp.json")"
            ;;
    esac
    case "$mcp_result" in
        added)   echo -e "${GREEN}✓ added${NC}" ;;
        skip)    echo "→ already configured" ;;
        missing) echo -e "${YELLOW}! config file not found — skipped${NC}" ;;
        error)   echo -e "${RED}✗ failed — see error above${NC}" ;;
    esac

    # ── Prompt injection ───────────────────────────────────────────────────
    printf "    Prompt: "
    prompt_result="missing"
    case "$type" in
        hermes_main|hermes_profile)
            prompt_result="$(_inject_prompt "$dir/soul.md")"
            ;;
        claude)
            # Inject into ~/.claude/CLAUDE.md in the root directory (if present).
            prompt_result="$(_inject_prompt "$dir/CLAUDE.md")"
            ;;
        cursor)
            # Inject into ~/.cursor/AGENTS.md in the root directory (if present).
            prompt_result="$(_inject_prompt "$dir/AGENTS.md")"
            ;;
    esac
    case "$prompt_result" in
        *added*)   echo -e "${GREEN}✓ added${NC}" ;;
        *updated*) echo -e "${GREEN}✓ updated${NC}" ;;
        skip)    echo "→ already configured" ;;
        missing) echo -e "${YELLOW}! config file not found — skipped${NC}" ;;
        error)   echo -e "${RED}✗ failed — see error above${NC}" ;;
    esac

    # ── Skills installation ────────────────────────────────────────────────
    echo "    Skills:"
    case "$type" in
        hermes_main|hermes_profile)
            # User skills (copies, flat)
            skills_result="$(_install_user_skills "$dir/skills")"
            ;;
        claude)
            skills_result="$(_install_user_skills "$dir/skills")"
            ;;
        cursor)
            skills_result="$(_install_user_skills "$dir/skills")"
            ;;
    esac

    SUMMARY_NAMES+=("$name")
    SUMMARY_MCP+=("$mcp_result")
    SUMMARY_PROMPT+=("$prompt_result")
    SUMMARY_SKILLS+=("$skills_result")
done

# ══════════════════════════════════════════════════════════════════════════════
# ── 7. Summary table ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

if [ "${#SUMMARY_NAMES[@]}" -gt 0 ]; then
    echo ""
    echo -e "${BOLD}Setup summary${NC}"
    printf "%-30s %-18s %-18s %-10s\n" "Agent" "MCP" "Prompt" "Skills"
    printf "%-30s %-18s %-18s %-10s\n" "──────────────────────────────" "──────────────────" "──────────────────" "──────────"
    for i in "${!SUMMARY_NAMES[@]}"; do
        printf "%-30s %-18s %-18s %-10s\n" \
            "${SUMMARY_NAMES[$i]}" \
            "$(_cell "${SUMMARY_MCP[$i]}")" \
            "$(_cell "${SUMMARY_PROMPT[$i]}")" \
            "$(_cell "${SUMMARY_SKILLS[$i]}")"
    done
    echo ""
    echo "Restart each agent to activate Lorekeeper."
fi

# ── 8. Optional: migrate from v1 ──────────────────────────────────────────────
if [ -n "${V1_JSON:-}" ] && [ -f "$V1_JSON" ]; then
    title "Migrating from v1..."
    uv run --directory "$REPO_DIR" python scripts/migrate_from_json.py \
        --source "$V1_JSON" --dest "$DATA_DIR"
    info "Migration complete"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}Setup complete.${NC}"
echo ""
echo "Start the dashboard:"
echo "  uv run --directory $REPO_DIR lorekeeper-dashboard"
echo "  → http://127.0.0.1:${LORE_DASH_PORT:-7777}"
echo ""
echo "Migrate from v1 (optional):"
echo "  V1_JSON=/path/to/memories.json bash $REPO_DIR/scripts/setup.sh"
