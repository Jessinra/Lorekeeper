#!/usr/bin/env bash
# lore-capture.sh — companion script for auto-capture from agent lifecycle hooks
#
# Usage:
#   ./scripts/lore-capture.sh "Your memory text here"
#   echo "memory text" | ./scripts/lore-capture.sh
#
# Drop this into your agent's startup/teardown hooks or lifecycle scripts.
# One script works with every agent — Claude Code, Cursor, Hermes, Codex, Gemini CLI.
#
# Requirements: lorekeeper-mcp installed and running (lorekeeper must be in PATH)
#
# Example hook (Claude Code ~/.claude/settings.json):
#   "hooks": {
#     "Stop": [{"matcher": "", "hooks": [{"type": "command",
#       "command": "echo 'Session ended at $(date)' | ~/.local/bin/lore-capture.sh"}]}]
#   }

set -euo pipefail

LORE_CAPTURE_NAMESPACE="${LORE_CAPTURE_NAMESPACE:-default}"

# Read thought from arg or stdin
if [[ $# -ge 1 ]]; then
    THOUGHT="$*"
elif ! [ -t 0 ]; then
    THOUGHT=$(cat -)
else
    echo "Usage: lore-capture.sh <thought>" >&2
    echo "  Or pipe text: echo 'thought' | lore-capture.sh" >&2
    exit 1
fi

# Skip empty input
if [[ -z "${THOUGHT// }" ]]; then
    exit 0
fi

# Use lorekeeper Python MCP client (lorekeeper must be installed and running)
python3 -c "
import sys, json, subprocess, os

thought = sys.argv[1]
namespace = os.environ.get('LORE_CAPTURE_NAMESPACE', 'default')

# Construct a minimal MCP JSON-RPC call to lore_remember
request = json.dumps({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'tools/call',
    'params': {
        'name': 'lore_remember',
        'arguments': {'thought': thought}
    }
})

result = subprocess.run(
    ['lorekeeper'],
    input=request,
    capture_output=True,
    text=True,
    timeout=10
)

if result.returncode == 0 and result.stdout:
    try:
        resp = json.loads(result.stdout.strip().split('\n')[-1])
        mem_id = resp.get('result', {}).get('content', [{}])[0].get('text', '')
        print(f'[lorekeeper] stored: {thought[:60]}...', file=sys.stderr)
    except Exception:
        pass  # silent on parse error
" "$THOUGHT"
