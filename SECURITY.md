# Security Policy

## Reporting a Vulnerability

Lorekeeper is in pre-beta. Security is taken seriously — if you find something, please report it privately.

**Do not** open a public GitHub issue for security vulnerabilities.

**Report via:** [GitHub Security Advisory](https://github.com/Jessinra/Lorekeeper/security/advisories/new)

Or email: jessinra.kai@gmail.com

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected version(s) — commit hash or release tag
- Any relevant logs, screenshots, or proof-of-concept

## Response

- **Acknowledgment** within 48 hours
- **Assessment and fix plan** within 5 business days for confirmed vulnerabilities
- **Disclosure** coordinated with the reporter — we aim for public disclosure within 30 days of fix

## Scope

- Lorekeeper MCP server (`src/lorekeeper/`)
- Dashboard web UI (`src/lorekeeper/dashboard/`)
- Official client integration scripts

**Out of scope:** Theoretical attacks requiring physical access, dependency CVEs already tracked by Dependabot, social engineering of the maintainer.

## Supported Versions

| Version | Supported                    |
| ------- | ---------------------------- |
| main    | ✅                           |
| < 1.0   | ⚠️ Best-effort — pre-release |

## Hall of Fame

We don't have one yet. First reporter gets their name/alias added here if they want.
