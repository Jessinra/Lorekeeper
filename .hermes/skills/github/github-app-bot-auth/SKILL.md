---
name: github-app-bot-auth
description: "GitHub App bot authentication — setup, token rotation, and cron refresh for jessinra-megumi-dev[bot]"
version: 1.1.0
author: Megumi Akane
platforms: [macos]
---

# GitHub App Bot Auth — `jessinra-megumi-dev[bot]`

## What This Is

The Lorekeeper ecosystem uses a **GitHub App** (`jessinra-megumi-dev`) for bot-authorized `gh` operations — PR creation, code pushes, API calls. The bot identity is separate from Jason's personal account, giving cleaner audit trails on PRs.

## Key Facts

| Item             | Value                                                |
| ---------------- | ---------------------------------------------------- |
| App ID           | `3823074`                                            |
| Installation ID  | `134866394`                                          |
| Account          | `Jessinra` (User, selected repos)                    |
| Bot display name | `jessinra-megumi-dev[bot]`                           |
| Private key      | `~/.hermes/keys/jessinra-megumi-dev.private-key.pem` |
| Auth file        | `~/.config/gh/hosts.yml`                             |
| Token prefix     | `ghs_` (installation token)                          |

## Authentication Flow

```
Private Key (.pem)
    → Sign JWT (RS256, App ID 3823074, 10min expiry)
    → POST /app/installations/134866394/access_tokens
    → Installation token (ghs_..., 1hr expiry)
    → Written to ~/.config/gh/hosts.yml
```

## Token Rotation

Installation tokens expire in **1 hour**. A cron job refreshes them automatically:

- **Script:** `~/.hermes/scripts/gh-token-refresh.py`
- **Schedule:** Every 45 minutes (`*/45 * * * *`)
- **Mode:** `no_agent=True` (pure script, no LLM cost)
- **Delivery:** `local` (silent — no Telegram spam)

The script:

1. Reads the PEM key from `~/.hermes/keys/jessinra-megumi-dev.private-key.pem`
2. Generates a JWT signed with RS256 (PyJWT preferred, falls back to `openssl dgst -sha256 -sign`)
3. Exchanges for an installation token via GitHub API
4. Writes `~/.config/gh/hosts.yml` with the fresh token inline
5. **Pushes the token into gh's keyring** via `gh auth login --with-token` (with `GH_TOKEN`/`GITHUB_TOKEN` unset)
6. Verifies `gh auth token` resolves a valid `ghs_` token

**Why step 5 matters (the critical fix):** on macOS, `gh` stores credentials in the **Keychain** and prefers the keyring over `hosts.yml`. Writing `hosts.yml` alone (the old behaviour) left `gh` authenticating with a **stale keyring token** — the recurring `The token in default is invalid` failure. The `--with-token` step keeps the keyring in sync so `gh` and git self-heal on every cron tick. No manual `logout`/`login` dance is needed anymore.

**Output behaviour:** SILENT on success (empty stdout — the `no_agent` cron delivers nothing, so no Telegram spam). LOUD on failure only (one actionable line + exit 1, surfaced by the cron watchdog). The openssl fallback captures the signature with `subprocess` — no binary ever leaks to stdout.

**Paths are hardcoded to `/Users/jessinra`, not `Path.home()`** — profile crons (e.g. diana) remap `HOME` to `~/.hermes/profiles/<name>/home/`, so `Path.home()` would resolve wrong. The GitHub App key + gh config are user-level shared resources.

## Manual Refresh (if cron fails)

```bash
python3 ~/.hermes/scripts/gh-token-refresh.py
```

## Verification

```bash
gh auth status
# Should show: ✓ Logged in to github.com account jessinra-megumi-dev[bot] (keyring)

gh api repos/Jessinra/Lorekeeper --jq '.full_name'
# Should return: Jessinra/Lorekeeper
```

## Failed Token Fallback

If the bot token expires and the cron job didn't run (e.g. machine was off), `gh` has **two accounts** configured:

```
✓ Logged in to github.com account jessinra-megumi-dev[bot] (keyring)  ← active
✓ Logged in to github.com account Jessinra (keyring)                   ← fallback
```

The active account is `jessinra-megumi-dev[bot]`. If the token is invalid, `gh` will still try and fail for that specific call, but the Jessinra account is still available as a fallback. To switch back to personal:

```bash
gh auth switch --user Jessinra
```

## Cron Setup (for any Hermes profile)

All agents share the same user-level `~/.config/gh/hosts.yml` **and** gh keyring, so one cron job system-wide is sufficient in principle. In practice there are two: the **default profile** job (`6183c59abea6`) is the source of truth, and a **diana profile** job (`f0f841b4e394`) runs the same logic.

**Profile crons can't reach user-level scripts directly** — the runner blocks any script path that resolves outside the profile's own `scripts/` dir (and symlinks are rejected too). For the diana job, `~/.hermes/profiles/diana/scripts/gh-token-refresh.py` is a thin **wrapper** that `os.execv`'s the canonical user-level script, so all real logic stays single-source at `~/.hermes/scripts/gh-token-refresh.py`.

If setting up per-profile:

```bash
hermes cron create \
  --name gh-bot-token-refresh \
  --script gh-token-refresh.py \
  --schedule "*/45 * * * *" \
  --profile <profile_name> \
  --no-agent \
  --deliver local
```

## Efficient `gh` CLI Operations

### Auth & Identity

```bash
# Check current auth status
gh auth status

# Switch between bot and personal accounts (both are configured)
gh auth switch --user jessinra-megumi-dev[bot]
gh auth switch --user Jessinra

# Get raw token (for debugging or API calls outside gh)
gh auth token
```

### PR Lifecycle (common patterns)

```bash
# Create a PR from current branch
gh pr create --base main --title "[LKPR-N] type: title" --body "## Summary\n\nChanges:\n- ...\n\nCloses LKPR-N"

# Create a PR with Copilot reviewer
gh pr create --base main --title "[LKPR-N] type: title" --body "..." --reviewer @copilot

# View PR details
gh pr view 12                          # specific PR number
gh pr view --json title,body,state     # raw JSON fields

# Get the PR diff for review
gh pr diff 12

# List open PRs
gh pr list --author @me
gh pr list --state open --limit 10

# Check CI/checks status
gh pr checks 12
gh pr checks 12 --watch                # poll until complete

# Merge (squash preferred)
gh pr merge 12 --squash --delete-branch
gh pr merge 12 --auto --squash         # enable auto-merge (merges when checks pass)

# Add a comment
gh pr comment 12 --body "Addressed in latest push"

# Close without merging
gh pr close 12
```

### Reading Inline Review Comments

`gh pr view` doesn't show inline comments. Use the API:

```bash
gh api repos/Jessinra/Lorekeeper/pulls/12/comments --jq '.[] | {path, body, line}'
```

### GitHub API Calls (general purpose)

```bash
# GET requests
gh api repos/Jessinra/Lorekeeper                         # repo info
gh api repos/Jessinra/Lorekeeper/pulls                    # list PRs
gh api repos/Jessinra/Lorekeeper/issues                   # list issues
gh api repos/Jessinra/Lorekeeper/contents/CLAUDE.md       # file content

# POST/PATCH requests
gh api repos/Jessinra/Lorekeeper/pulls -X POST -f title="..." -f head=branch -f base=main
gh api repos/Jessinra/Lorekeeper/issues/1/comments -X POST -f body="..."

# Filter with jq
gh api repos/Jessinra/Lorekeeper/pulls --jq '.[] | {number, title, state, created_at}'
gh api repos/Jessinra/Lorekeeper/pulls/12 --jq '.head.ref'   # get the branch name

# Pagination
gh api repos/Jessinra/Lorekeeper/pulls --paginate --jq '.[].title'
```

### Working with the Lorekeeper Repo

```bash
# Quick branch info
git branch --show-current                                  # current branch
git log --oneline -5                                       # recent commits
git diff main...HEAD --stat                                # what's changed on this branch

# Push a branch and open PR (one-liner)
git push -u origin HEAD && gh pr create --base main --title "[LKPR-N] type: title" --body "..."

# Get the PR URL (useful for sharing with Jason)
gh pr view --json url --jq '.url'

# See who's ahead
git log --oneline origin/main..HEAD                        # local commits not on main
git log --oneline HEAD..origin/main                        # remote commits not local
```

### Troubleshooting

**First thing to try — just run the refresh script.** It now re-syncs the keyring too, so it fixes the `token in default is invalid` error on its own:

```bash
python3 ~/.hermes/scripts/gh-token-refresh.py   # silent = success; prints + exits 1 on failure
gh auth status                                   # confirm: ✓ Logged in ... (keyring)
gh api repos/Jessinra/Lorekeeper --jq '.full_name'
```

If `gh auth status` still shows the token as invalid after a refresh, the keyring write failed — check the script's stderr (run it directly, it will print the failing step). Legacy manual dance (rarely needed now):

```bash
# Fall back to personal account
gh auth switch --user Jessinra

# Nuclear reset
unset GH_TOKEN
gh auth logout -h github.com -u "jessinra-megumi-dev[bot]"
python3 ~/.hermes/scripts/gh-token-refresh.py    # re-mints + re-logs-in via keyring
```
