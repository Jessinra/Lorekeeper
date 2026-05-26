---
id: LKPR-32
title: Encrypted export/import for distribution-safe backups
type: feature
status: S:proposal
priority: P2:medium
sprint: ~
rice_score: 10.0 # R:5 I:8 C:50% E:2w
filed_by: Jason
filed_date: 2026-05-25
---

# [LKPR-32] Encrypted export/import for distribution-safe backups

## Problem

Current export is plain JSON — anyone who accesses the file reads all memories verbatim. This blocks the distribution goal: if Lorekeeper is shared or deployed for others, unencrypted backups leak private memory data. A user could accidentally import someone else's backup into their own instance, corrupting their memory store with foreign data.

No mechanism exists to verify that imported data belongs to this instance.

## Solution

Add optional symmetric encryption (AES-256 via Fernet) to export/import. Opt-out by default — local dev users see no change. When encryption is enabled:

**Export flow:**

- Dashboard checkbox "Encrypt export" (default unchecked)
- On first use, backend generates a Fernet key and returns it once via the API
- Dashboard shows the key in a one-time modal with copy + download-as-.key-file buttons
- The key is scoped to the browser session (sessionStorage) — subsequent exports in the same session don't regen
- Backend encrypts the JSON payload with the key before streaming
- File extension: `.lorekeeper.enc` instead of `.json`

**Import flow:**

- File picker accepts both `.json` and `.lorekeeper.enc`
- If the file starts with a Fernet header (detected server-side), backend returns `encrypted: true`
- Dashboard shows an inline password field: "This file is encrypted — enter the encryption key"
- User pastes the key → backend decrypts → proceeds with existing preview/confirm flow
- Wrong key → clear error "Decryption failed — invalid key"

**Key properties:**

- Symmetric (same key encrypts and decrypts) — no key management server needed
- Fernet (AES-128-CBC + HMAC-SHA256) via `cryptography` library — standard, audited, widely used
- Key shown exactly once in dashboard UI; user must save it (copy/download)
- No server-side key storage — server encrypts with a key provided per-request
- Export with key "abc123" → must import with same key "abc123"

## Acceptance Criteria

- [ ] Backend: encrypt endpoint accepts optional `encryption_key` query param; decrypt detected on import preview
- [ ] Backend: key generation endpoint (`POST /api/backup/key`) returns a new Fernet key
- [ ] Backend: `_parse_dump()` detects Fernet header and decrypts before parsing; returns 422 on bad key
- [ ] Frontend: "Encrypt export" checkbox in Backup tab; when checked, generates/show key once in a modal
- [ ] Frontend: import detects encrypted files and shows key input field inline
- [ ] File picker accepts `.lorekeeper.enc` alongside `.json`
- [ ] `cryptography` added as an optional dependency under `[project.optional-dependencies] dashboard`
- [ ] Error messages for: missing key, wrong key, corrupted file, non-encrypted file tagged as `.enc`
- [ ] Existing unencrypted export/import continues working with zero changes

## Affected Files

**Backend:**

- `src/lorekeeper/dashboard/app.py` — `/api/export` accepts `encryption_key` param; `_parse_dump` decrypts Fernet payload; new `POST /api/backup/key` endpoint
- `src/lorekeeper/dashboard/crypto.py` (new) — `encrypt_payload()`, `decrypt_payload()`, `is_encrypted()`, `generate_key()`
- `pyproject.toml` — add `cryptography` to `dashboard` extra deps

**Dashboard (frontend):**

- `src/lorekeeper/dashboard/static/js/backup.js` — triggerExport sends key param; import flow handles encrypted detection + key prompt
- `src/lorekeeper/dashboard/static/index.html` — encrypt checkbox, key modal, key input field for import
- `src/lorekeeper/dashboard/static/css/styles.css` — modal styles

## Dependencies

_None_ — self-contained. No other ticket blocks this.

## Required Updates

- **CLAUDE.md**: [ ] Add note about `cryptography` dep for dashboard; document encryption flow
- **README.md**: [ ] Document encrypted backup/restore feature with key management warning
- **Skills**: [ ] `after-changes` — add crypto files to verification checklist; `lorekeeper-dashboard-verify` — add encrypted export scenario
- **Backlog**: [ ] Consider follow-up ticket for CLI-based encryption (for headless/hermes-cron backup scripts)

## Open Questions

- Should the key be derivable from a passphrase (PBKDF2) instead of a random key? Trade-off: human-memorable vs brute-force resistant.
- For CLI usage (cron job auto-backup), should there be a config.yaml setting for a stored encryption key? (deferred — dashboard-first)
- What file extension for encrypted exports? `.lorekeeper.enc` is verbose but explicit. `.lkb` shorter.
- Should the "key shown once" persist across dashboard restarts via localStorage, or is session-only stricter? (session-only is safer)

## Notes

Filed by Jason as a distribution enabler. Encryption is opt-out (default off) so existing users see no friction. The key management UX is the riskiest part — losing the key means losing the backup. The one-time modal + .key file download pattern follows established conventions (Bitwarden export, GPG key generation).

Fernet (used by `cryptography` lib) wraps AES-128-CBC with HMAC-SHA256 authentication — prevents tampering as well as reading. The backend never stores keys; the key is ephemeral per export session. This means two exports with the same checkbox clicked produce different keys — each file must be decrypted with its own key.

Trade-off accepted: no password-based derivation (PBKDF2) in v1. Random 128-bit keys are simpler and eliminate weak-password risk. Password derivation can follow in a phase 2 if users request it.
