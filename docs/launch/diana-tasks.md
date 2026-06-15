---
title: Lorekeeper v0.3.0 Beta — Diana launch execution
status: S:Ready
priority: P1:high
labels: ["S:Ready", "P1:high", "marketing"]
---

# Lorekeeper v0.3.0 Beta Launch — Diana Execution Guide

## Overview

Everything you need to get Lorekeeper listed on every MCP directory plus publish
the dev.to article and Reddit posts. Akane already handled: banner logos fixed
with official SVG, SECURITY.md added, competitive research done, launch plan
drafted, 7 post variations written.

**Core message (use everywhere):**
> Self-improving memory for AI agents. One command, no cloud, no config.

**Install commands to reference:**
- `pip install lorekeeper-mcp && lorekeeper setup`
- `uvx lorekeeper-mcp` (ephemeral, no install)

**Links:**
- GitHub: https://github.com/Jessinra/Lorekeeper
- Docs: https://lorekeeper.dev
- PyPI: https://pypi.org/project/lorekeeper-mcp/

---

## Day 1 — MCP Directory Submissions

---

### 1. Official MCP Registry

**Why:** This is the source of truth. Glama, Smithery, and PulseMCP auto-ingest
from it. One submission feeds five directories.

**Time:** ~15 min

**Steps:**

```bash
# Install the publisher CLI
go install github.com/modelcontextprotocol/registry/cmd/mcp-publisher@latest

# Add to PATH (if not already)
export PATH=$PATH:$(go env GOPATH)/bin

# Authenticate with GitHub token
# Generate token at: https://github.com/settings/tokens/new
# Scope: repo, write:packages
mcp-publisher auth login
```

Create a `server.json` file in the lorekeeper repo root with this content:

```json
{
  "name": "io.github.jessinra/lorekeeper",
  "version": "0.3.0",
  "description": "Self-improving memory for AI agents. One command, no cloud, no config.",
  "long_description": "Lorekeeper is an MCP server that gives AI agents persistent, self-improving memory. Install with one command, no cloud, no API keys. Features include hybrid semantic+keyword search, a feedback loop that automatically improves memory quality over time, interactive dashboard for browsing memories, auto-linking between related memories, and namespace isolation.",
  "homepage": "https://github.com/Jessinra/Lorekeeper",
  "docs_url": "https://lorekeeper.dev",
  "license": "Apache-2.0",
  "runtime": "python",
  "install_command": "pip install lorekeeper-mcp && lorekeeper setup",
  "repository": "https://github.com/Jessinra/Lorekeeper",
  "categories": ["ai", "memory", "developer-tools", "mcp"],
  "tags": ["mcp-server", "ai-memory", "agent-memory", "python"],
  "tools": [
    "lore_search - Hybrid semantic and keyword search across memories",
    "lore_remember - Fast single-thought memory insert",
    "lore_insert - Structured memory insert with links",
    "lore_update - Provide feedback to improve memory quality scores",
    "lore_forget - Soft-delete unwanted memories",
    "lore_recommend_links - Discover relationships between memories",
    "lore_reflect - Reflect on a session to auto-create memories"
  ]
}
```

Then:
```bash
mcp-publisher publish server.json
```

**Verify:** Search for "lorekeeper" at https://registry.modelcontextprotocol.io/
— should appear in results. If you get errors, check the [docs](https://github.com/modelcontextprotocol/registry).

---

### 2. Glama (105K monthly visits)

**URL:** https://glama.ai/mcp/servers

**Steps:**
1. Click "Add Server" button (top-right)
2. Enter GitHub URL: `https://github.com/Jessinra/Lorekeeper`
3. If auto-discovery works — done. If not, fill manually:
   - Name: Lorekeeper — Self-Improving Memory for AI Agents
   - Description: Self-improving memory for AI agents. One command, no cloud, no config.
   - Install: `pip install lorekeeper-mcp && lorekeeper setup`
   - PyPI: lorekeeper-mcp
4. After submission, wait ~1 hour then check Glama score
5. **Score must be ≥ 70** — below 70 means buried in search results
6. Glama checks: README quality ✔, LICENSE (Apache 2.0) ✔, CI ✔, SECURITY.md ✔
7. If score < 70, investigate what Glama flags and fix

**Verify:** Search "lorekeeper" on Glama — our server (not the D&D one) should appear.

---

### 3. mcp.so (238K monthly visits)

**URL:** https://mcp.so/submit

**Form fields:**
| Field | Value |
|-------|-------|
| Server Name | Lorekeeper — Self-Improving Memory for AI Agents |
| Description | Self-improving memory for AI agents. One command, no cloud, no config. |
| GitHub URL | https://github.com/Jessinra/Lorekeeper |
| Website | https://lorekeeper.dev |
| Install Command | `pip install lorekeeper-mcp && lorekeeper setup` |
| Tags | mcp-server, ai-memory, python, agent |

**Verify:** Search "lorekeeper" on mcp.so after 24h.

---

### 4. PulseMCP (277K monthly visits)

**URL:** https://pulsemcp.com/submit

**Steps:**
1. Fill in the form with same info as above
2. PulseMCP also auto-ingests from the Official Registry, so if #1 is done,
   this may already populate automatically within a week

**Verify:** Search "lorekeeper" on PulseMCP.

---

### 5. MCP Market (1.4M monthly visits — #1 by traffic)

**URL:** https://mcpmarket.com/submit

**Tiers:** Free and paid ($29). Try free tier first.

**Steps:**
1. Go to the submit page
2. If you see a free option, use it with the standard template
3. If only paid tier is available and free queue isn't accessible, skip for now
   (user decision on paying)

**Verify:** Search "lorekeeper" on MCP Market after approval.

---

### 6. mcpservers.org (504K monthly visits)

**URL:** https://mcpservers.org

**Action:** Check if the earlier submission went through:
1. Search "lorekeeper" on mcpservers.org
2. If listed — done
3. If not listed or status pending, resubmit
4. If the submit page requires login, create account

**Template for listing:**
- Name: Lorekeeper — Self-Improving Memory for AI Agents
- One-liner: Self-improving memory for AI agents. One command, no cloud, no config.
- Install: `pip install lorekeeper-mcp && lorekeeper setup`
- Features: Hybrid search, feedback loop auto-improves, interactive dashboard, auto-linking, namespace isolation
- Runtime: Python
- License: Apache 2.0

---

### 7. ClaudePluginHub (168K monthly visits)

**URL:** https://claudepluginhub.com

**Steps:**
1. Find the "Submit" or "Add" link on the site
2. Fill in the standard template
3. Submit

---

### 8. MCP.Directory (134K monthly visits)

**URL:** https://mcp.directory

**Steps:**
1. Find the submit link
2. Fill in the standard template
3. Submit

---

### 9. Awesome Claude (187K monthly visits)

**URL:** https://awesomeclaude.ai

**Steps:**
1. Find the "Submit" link
2. Use the standard template
3. Submit

---

### 10. punkpeye/awesome-mcp-servers — PR (27,000+ stars)

**URL:** https://github.com/punkpeye/awesome-mcp-servers

**Steps:**
1. Fork the repo
2. Edit `README.md` (or appropriate category file)
3. Add under a "Memory" or "AI" section:

```markdown
- [Lorekeeper](https://github.com/Jessinra/Lorekeeper) - Self-improving memory for AI agents. One command, no cloud, no config.
```

4. Open a PR with title: `Add Lorekeeper — self-improving memory for AI agents`

**Verify:** PR is open (may take days/weeks for maintainer to merge — this is normal).

---

### Directory Submission Template (copy-paste for every listing)

```
Name:             Lorekeeper — Self-Improving Memory for AI Agents
One-liner:        Self-improving memory for AI agents. One command, no cloud, no config.
Install:          pip install lorekeeper-mcp && lorekeeper setup
Features:         Hybrid semantic+keyword search | Feedback loop auto-improves memory |
                  Interactive dashboard | Auto-linking between related memories |
                  Namespace isolation (per-agent) | One-command setup (lorekeeper setup)
GitHub:           https://github.com/Jessinra/Lorekeeper
Docs:             https://lorekeeper.dev
PyPI:             https://pypi.org/project/lorekeeper-mcp/
Runtime:          Python (uv / pip)
License:          Apache 2.0
Tags:             mcp-server, ai-memory, agent-memory, claude-code, codex, self-improving
```

---

## Day 2 — Content Launch

### 11. Choose & Publish Dev.to Post

**Location:** https://dev.to

**Assets ready:**
- `docs/launch/post-sample-1.md` (benchmark/comparison)
- `docs/launch/post-sample-2.md` (narrative)
- `docs/launch/post-sample-3.md` (tutorial)
- `docs/launch/post-sample-4.md` (listicle — **recommended**)
- `docs/launch/post-sample-5.md` (why I built)
- `docs/launch/post-sample-6.md` (numbered reasons)
- `docs/launch/post-sample-7.md` (hot take)
- `docs/launch/lorekeeper-banner-1200x630.png` (banner image)
- `docs/launch/lorekeeper-banner-square.png` (square variant)

**Recommendation:** Post variant #4 (listicle/comparison). It's the format
that performs best on dev.to — top posts in this format get 1,846 reactions.

**How to publish:**
1. Log in to dev.to with the bot account (jessinra.kai@gmail.com)
2. Click "Write a Post" / "New Article"
3. Title: "5 AI Agent Memory Systems Compared (2026) — and the one that self-improves"
4. Upload banner image as the cover image
5. Tags: `mcp`, `python`, `ai`, `opensource`
6. Canonical URL: https://lorekeeper.dev (optional, helps SEO)
7. Preview, check formatting, then publish

**Tone rules:**
- ❌ Never say competitor X is "bad" or "broken"
- ✅ Say "paid" instead of "not free" or "closed source"
- ✅ Open with cooperative framing: "There are great tools in this space — each makes different trade-offs."
- ✅ Name-drop competitors by name (Mem0, Letta, Zep, claude-mem, agentmemory)
- ✅ Close inviting discussion: "Would love to hear what memory setup you use."
- ❌ No agent names (Diana, Akane) in the post body
- ❌ No hype language ("revolutionary", "game-changing")

---

### 12. Reddit Posts (Day 3)

**Subreddits (post in order):**
1. r/ClaudeAI — https://reddit.com/r/ClaudeAI (largest, most relevant)
2. r/MCP — https://reddit.com/r/MCP (niche, highly targeted)
3. r/Python — https://reddit.com/r/Python (broad dev audience)

**Title options (choose one):**
- "How Lorekeeper's feedback loop handles memory decay — a comparison with agentmemory and mem0"
- "Self-improving agent memory: Lorekeeper vs the alternatives"

**Body template:**

```
There are great tools in this space — Mem0, Letta, Zep, claude-mem, agentmemory.
Each makes different trade-offs on cloud vs local, memory quality, and setup complexity.

I built Lorekeeper to fill a specific gap: an MCP server that gives agents
self-improving memory in one command, no cloud, no config.

Here's where it sits compared to the alternatives:
[Link to dev.to post or comparison table from README]

Key differentiators:
- MCP-native: `uvx lorekeeper-mcp` works with any MCP client (Claude, Cursor, VS Code, Codex)
- Feedback loop: memories get sharper with use (LongMemEval-S: R@1 84.6%)
- One-command setup: `pip install lorekeeper-mcp && lorekeeper setup`
- Fully local: no API keys, no cloud, no Docker

Would love to hear from anyone who's tried these tools — what's your memory setup?
```

**Tone:** Same as dev.to — cooperative, no undermining competitors, name-drop generously.

**Timing:** 24 hours after dev.to post (gives the dev.to post time to breathe).

---

## Day 3+ — Post-Launch Monitoring

### Checklist after all submissions are done:

- [ ] All 10 directories submitted + official registry
- [ ] Glama score checked (target ≥ 70)
- [ ] dev.to post published with banner image
- [ ] Reddit posts live on all 3 subreddits
- [ ] Monitor GitHub stars daily
- [ ] Reply to every dev.to comment and Reddit comment
- [ ] Watch for comparison article opportunities (search "Mem0 vs" weekly)
- [ ] When HN account is eligible, post the Show HN draft

### Additional ideas (optional):

- Cross-post the dev.to article to daily.dev
- Reach out to AI newsletter authors (The Neuron, TLDR AI, etc.)
- Write a follow-up post with benchmark results once data accumulates

---

## Notes for Diana

- The official registry submission is the highest-leverage single action
- Glama score is the second most important metric — check and fix
- Don't wait for all directories before publishing the dev.to post
  (dev.to is the content launch, directories are discovery infrastructure)
- If any site requires payment, skip it and flag to Jason/Akane
- Maintain the cooperative tone — it's a deliberate positioning choice