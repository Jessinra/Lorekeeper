---
date: 2026-05-20
session_id: 20260520_215425_9fb6e503
transcript: /Users/jessin.donnyson/.hermes/sessions/20260520_215425_9fb6e503.jsonl
topic: hermes-copilot-model-config
task_type: build
---

## What was done

Configured Hermes to use GitHub Copilot provider with `gpt-5-mini` model. Added `COPILOT_GITHUB_TOKEN` to `~/.hermes/.env`. Provider was already set to `github-copilot` in `config.yaml`. Set model to `gpt-5-mini` after initial `gpt-4o` setup.

## Decisions made

- GitHub Copilot provider as the primary model backend
- `gpt-5-mini` as the working model (settled on after starting with `gpt-4o`)

## Corrections / discoveries

- `hermes model` command requires a fully interactive PTY and cannot be driven via tool interface — must be done manually
- `COPILOT_GITHUB_TOKEN` env var is needed for GitHub Copilot provider (can also use `GH_TOKEN`)

## Lessons learnt

- **Hermes CLI model configuration is PTY-only** — the `hermes model` command doesn't work through non-interactive tool execution
- **GitHub Copilot env var**: Use `COPILOT_GITHUB_TOKEN` or `GH_TOKEN`

## Good patterns observed

- (None — straightforward config session)

## What I learned about the user

- Jason configures his agent infrastructure with specific model preferences (GitHub Copilot → gpt-5-mini)

## Proposed updates

- Memory: Hermes model command is PTY-only, cannot be driven via tool interface
- Memory: COPILOT_GITHUB_TOKEN env var for GitHub Copilot provider
