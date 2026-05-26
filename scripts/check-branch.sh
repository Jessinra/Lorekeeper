#!/usr/bin/env bash
# Pre-commit branch guard: block commits directly on main.
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo ""
    echo "🚫  BLOCKED: Direct commit to '$BRANCH' is not allowed."
    echo "    All changes must go through a feature branch and PR."
    echo "    Use: git checkout -b <branch-name>"
    echo ""
    exit 1
fi
