#!/usr/bin/env bash
# Pre-commit branch guard: block commits directly on main.
# Bypass: SKIP_BRANCH_CHECK=1 git commit  or  git commit --no-verify
set -euo pipefail

if [ "${SKIP_BRANCH_CHECK:-}" = "1" ]; then
    exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo ""
    echo "🚫  BLOCKED: Direct commit to '$BRANCH' is not allowed."
    echo "    All changes must go through a feature branch and PR."
    echo "    To bypass: SKIP_BRANCH_CHECK=1 git commit"
    echo "    Or use: git checkout -b <branch-name>"
    echo ""
    exit 1
fi
