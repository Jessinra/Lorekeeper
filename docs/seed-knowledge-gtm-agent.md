# Lorekeeper — GTM Agent Seed Knowledge

> **Compiled:** June 14, 2026
> **Source files:** README.md, docs/growth-strategy.md, docs/positioning-manifesto.md, docs/launch/launch-plan.md, docs/launch/diana-tasks.md, docs/launch/hn-post.md, docs/launch/x-thread.md, docs/launch/devto-post.md, docs/ARCHITECTURE.md, docs/quickstart.md, docs/api-reference.md, docs/research/2026-06-11-retrieval-benchmark-results.md, ~/.hermes/memories/USER.md, ~/.hermes/memories/MEMORY.md, Lorekeeper memory store (competitive landscape, positioning, moat records)

---

## 1. Product Description

**Tagline:** *Self-improving memory for AI agents. One command, no cloud, no config.*

**One-liner:** Lorekeeper is a local MCP memory server that gives AI agents persistent, self-improving memory. Install with `pip install lorekeeper-mcp`, connect your agent, and it starts remembering — and gets better the more you use it.

**Category:** Local MCP memory server for AI coding agents.

**License:** Apache 2.0

**Current version:** v0.3.0 (beta/pre-beta)

**GitHub:** https://github.com/Jessinra/Lorekeeper
**Docs:** https://jessinra.github.io/Lorekeeper/
**PyPI:** `pip install lorekeeper-mcp`

---

## 2. Key Features

### 8 MCP Tools (Full Memory Lifecycle)

| Tool | Purpose |
|------|---------|
| `lore_search` | Hybrid semantic + keyword search with relevance scores |
| `lore_remember` | Fast one-shot memory save (auto-titles, auto-links) |
| `lore_insert` | Bulk structured insert with custom scores and links |
| `lore_update` | Feedback loop — rate memories, drive quality |
| `lore_forget` | Soft-delete wrong or outdated memories |
| `lore_reflect` | End-of-session: extract learnings, auto-save discoveries |
| `lore_processed_sessions` | Check which sessions are already processed |
| `lore_recommend_links` | Suggest candidate links between related memories |

### Core Differentiators

- **Hybrid search** — semantic vectors + BM25 keyword + time-decay + usage frequency + memory score, all ranked by a weighted formula (`0.45·semantic + 0.30·keyword + 0.15·(score/10) + 0.10·log_usage_norm`)
- **Self-improving feedback loop** — `lore_update` adjusts scores. Bad memories fade (confidence ≤ 2 + not useful → soft-delete). Good ones rise. Compounds over time.
- **Auto-linking** — new memories automatically link to closest semantic neighbor. Knowledge graph forms without effort.
- **Duplicate detection** — `0.6·semantic + 0.4·keyword >= 0.85` blocks near-identical inserts. Override with `force=true`.
- **Dashboard** — full web UI on port 7777 (FastAPI + uvicorn). 7 tabs: Memories, Detail, Links, Query, Sessions, Config, Backup.
- **Universal MCP** — works with Claude Code, Cursor, Hermes, Copilot, OpenCode, Codex — any MCP-compatible agent.
- **Local-first** — SQLite + LanceDB (or ChromaDB). Data stays on your machine. No cloud, no API keys.
- **Namespaces** — multiple agents share one store with isolated namespaces.
- **Reflection** — agents auto-extract learnings from sessions. Discoveries and lessons become searchable memories.

### Quick Install

```bash
pip install lorekeeper-mcp
lorekeeper setup   # auto-detects Claude Code, Cursor, Hermes
lorekeeper         # starts the MCP server
```

Ephemeral mode: `uvx lorekeeper-mcp`

### Benchmarks (LongMemEval-S, 500 questions)

| Metric | Value | Latency |
|--------|-------|---------|
| R@1 | **84.6%** | 32.9 ms |
| R@3 | **93.6%** | — |
| R@5 | **96.6%** | — |
| R@10 | **98.8%** | — |

Lorekeeper's 96.6% R@5 beats agentmemory's 95.2% R@5 on the same benchmark, using the standard `all-MiniLM-L6-v2` (no proprietary embeddings).

### Tech Stack

Python, SQLite + LanceDB (or ChromaDB), sentence-transformers (`all-MiniLM-L6-v2`, 384-dim), BM25, FastMCP. ~1.4GB for the embedding model (same weight class as any local embedding solution).

---

## 3. Competitive Landscape (June 2026)

### Market Context

- **4.2M weekly active Claude Code users** — 131K GitHub stars, writes 4% of all public GitHub commits
- **4.7M GitHub Copilot paid subscribers** — $2B ARR
- **Cursor at $60B valuation** — $2B ARR
- **MCP ecosystem: 97M monthly SDK downloads**, 9,600+ server records. Growing 232% per 6 months
- **Memory server category exploded** — claude-mem (46K★), agentmemory (21.7K★), MemPalace (41K★)
- **mem0: 55K★, $24M raised, 14M+ PyPI downloads, 186M API calls/quarter** — the funded incumbent
- **$6-9.5B total AI coding tool market (2026)**, 22% CAGR

### Direct MCP Memory Servers

| Product | Stars | Stage | Notes |
|---------|-------|-------|-------|
| **claude-mem** (thedotmack) | ~46K+ | v13+ | Node.js/Bun, lifecycle hooks. Most direct competitor. 81.2K stars in earlier count. Plugin-based, deeply integrated into Claude Code internals. Has web viewer, citation system, $CMEM token. |
| **agentmemory** (rohitg00) | ~21.7K | Active | TypeScript, `npx install`, viral growth. Auto-captures tool calls via hooks. Real-time viewer. Benchmark-driven. Biggest new entrant (May 2026). 53 MCP tools claim. |
| **MemPalace** | ~41K | Fastest growing | Doubled in 2 months. Vector-only, no hooks/MCP/multi-agent. |
| **sqlite-memory** | New | Launched Jun 2026 | Markdown-based, semantic search. |
| **Neural Memory** | — | Active | 28 MCP tools, spreading activation. Feature-heavy. |
| **ai-memory** | — | Active | FTS5 keyword-first. Fast but no semantic. |
| **Anthropic official MCP memory** | — | Active | Entity-relation graph. Simple but basic. |
| **phloem** (CanopyHQ) | — | Active | Local-first, causal graphs, citation verification. |
| **Supermemory** | — | Active | API-based embedder. |
| **MCP Backpack** | — | Active | Key-value only. No semantic search. |

### Funded / Engine Competitors

| Product | Funding | Notes |
|---------|---------|-------|
| **Mem0** | $24M (Series A) | 55K★, 14M downloads. Library, not a product. Need to write MCP wrapper. New algorithm (April 2026): LoCoMo 91.6%, LongMemEval 94.8%. |
| **Zep** | $15M+ | Enterprise memory. Cloud-only, expensive. |
| **Anthropic built-in** | Infinite | Beta. High risk — ecosystem lock-in. |
| **OpenAI built-in** | Infinite | Alpha. High risk — same. |

### Lorekeeper's Position Among Competitors

**The unique gap:** No competitor has all three of **simple setup** × **smart retrieval** × **self-improving** simultaneously.

- File-based (CLAUDE.md, .cursorrules): Simple setup ✓, smart retrieval ✗, self-improving ✗
- Cloud services (Mem0 Cloud, Zep): Smart retrieval ✓, self-improving ✗, simple setup ✗
- Docker servers (Hindsight): Smart retrieval ✓, simple setup ✗, self-improving ✗
- Library-based (Mem0): Smart retrieval ✓, simple setup ✗, self-improving ✗
- **Lorekeeper: Simple setup ✓, smart retrieval ✓, self-improving ✓**

### Key Differentiators vs Each Competitor

| vs | Lorekeeper's Angle |
|----|-------------------|
| **claude-mem** | Pure MCP server (more portable) vs plugin/hook. Python vs Node/Bun. Standard MCP protocol vs deep Claude Code internals. |
| **agentmemory** | Python-native, team-ready. Feedback loop is real and working (266 tests). |
| **Mem0** | MCP-native: one `uvx` command works everywhere. Library vs product. |
| **Anthropic/OpenAI** | "Your memory shouldn't fire your other agents." Multi-agent, multi-provider. |
| **Zep** | "Free for what Zep charges for." Local-first vs cloud-only. |

### Lorekeeper's Moats

1. **The feedback loop** (quality loop) — compounds over time. A 3-month-old install is a different product. Requires the whole system: hybrid search, score adjustment, confidence EMA, soft-delete, auto-linking, dedup.
2. **Built by agents, for agents** — dogfooding at the product level. Every tool schema shaped by actual agent usage.
3. **MCP-native from day one** — not an afterthought library wrapper.
4. **Dashboard** — full web UI (7 tabs). Other memory servers are CLI-only or have basic viewers.
5. **Reflection system** — auto-extract learnings from sessions.
6. **31 done tickets, 266 tests** — battle-tested through real use.

### Strategy: Fast Follower, Quality Winner

> *"Let the fast movers educate the market. We watch what works, what users complain about, what the category converges on. Then we execute — better, simpler, with the feedback loop they can't replicate."*

---

## 4. Target Audience / ICP

### Primary ICP: Solo developers using AI coding agents

- Uses Claude Code, Cursor, Hermes, OpenCode, Codex, or Copilot CLI
- Frustrated by agents forgetting context between sessions
- Values simplicity over features
- Wants local-first, no cloud dependency
- Technical enough to run `pip install` and edit an MCP config file
- Not interested in maintaining memory infrastructure
- Probably already tried or knows about CLAUDE.md, .cursorrules

### Secondary ICP: Agent framework users

- Building multi-agent systems
- Need shared, namespace-isolated memory
- Want a drop-in MCP server, not another framework

### Explicitly NOT for (yet):

- Enterprise teams (need RBAC, audit, SSO — not there yet)
- Consumer AI apps (wrong distribution model)
- Non-technical users (MCP isn't there yet)

### Funnel for Phase A (Beta)

Who these users are: Fellow agent builders, open-source tinkerers, Claude Code / Cursor power users who already use or build memory servers. They'll try anything that promises "one command." They're technically generous — they file issues, not just leave.

---

## 5. Growth Phases

### Phase A: Beta Validation (Now → Jul 2026)
**Goal:** 100 GitHub stars, 10 weekly active users
**Duration:** 4-6 weeks from beta launch

**Critical path (must ship for beta):**
- P0: `lorekeeper setup` auto-detect + inject for Claude Code, Cursor, Copilot, Hermes, Codex
- P0: `uvx lorekeeper` ephemeral zero-install mode
- P0: Seed prompt on first run (LKPR-55 done)
- P1: Dashboard empty state fixed (LKPR-56 in progress)
- P2: README marketing pass (LKPR-71 done)
- P2: Benchmark eval script (LKPR-70 in progress)

**Success criteria:**
- 100 GitHub stars
- 10 weekly active users (WAU)
- < 5% crash rate on install
- < 30s median time from pip install to first memory
- 3+ issues filed by external users

**What NOT to build:**
- Multi-user features
- Cloud sync
- Plugin system
- Enterprise features
- More MCP tools (8 is fine — resist bloat)

### Phase B: Team Tier (Jul 2026 → Jan 2027)
**Goal:** 1,000 GitHub stars, 100 WAU, first team-tier revenue
**Duration:** 3-6 months after beta launch

**Critical path:**
- P0: Token/namespace auth (LKPR-39)
- P0: Provenance tagging (LKPR-18)
- P0: Org namespaces (LKPR-40)
- P1: Multi-reader, controlled-writer
- P1: Herd memory awareness (social proof in namespace)
- P2: Self-hosted deployment docs, Memory quality governance

**Product thesis at this scale:** "Your team's agents get smarter together about your specific codebase — without sharing anything externally."

**Revenue (Phase B):** Design partnerships only. Do not charge individuals. Free tier is the acquisition channel.

### Phase C: Platform & Ecosystem (2027-2028)
**Goal:** 50K+ GitHub stars, 10K+ WAU, 1M+ agent instances, $2-4M ARR
**Duration:** 12-24 months after beta launch

**What ships:** Sub-ms search, multi-device E2EE sync, federated knowledge, plugin ecosystem, memory marketplace, enterprise tier, Helm chart + K8s operator.

**Business model (Obsidian playbook):** Free core ($0), Sync ($4-8/mo), Team ($15-30/seat/mo), Enterprise (Custom). Projected: $181K-$362K/mo → $2.2M-$4.3M ARR at 1M agents.

---

## 6. Current Priorities & Readiness

### Launch Readiness (June 2026)

| Asset | Status |
|-------|--------|
| GitHub README | ✅ Good — comparison table, install, screenshots |
| Documentation site | ✅ Live at lorekeeper.dev, MkDocs |
| PyPI package | ✅ Published — `lorekeeper-mcp` v0.3.0 |
| `uvx` install | ✅ Verified ephemeral mode |
| Banner logos | ✅ Fixed with official SVG |
| SECURITY.md | ✅ Added |
| MCP topic tag | ✅ `mcp-server` |
| License | ✅ Apache 2.0 |
| GitHub Actions CI | ✅ Setup |
| Official MCP Registry | ❌ Missing — needs `mcp-publisher` submission |
| Glama listing | ❌ Missing |
| mcp.so listing | ❌ Missing |
| PulseMCP listing | ❌ Missing |
| awesome-mcp-servers | ❌ Missing — PR not submitted |
| Dev.to post | ⏳ Drafted — 7 variations exist |
| X thread | ⏳ Drafted — no account to post |
| HN post | ⏳ Drafted — account restricted |

### Key Principles (Maintain Across All Phases)

1. **Local-first never optional** — cloud features are add-ons, never requirements
2. **One command install** stays the default path forever
3. **The feedback loop is the moat** — protect at all costs. No feature may degrade search quality
4. **8 MCP tools, ±2** — resist tool bloat. Every new tool must prove necessity
5. **Ratings degrade** — automatic downranking of unused/unhelpful memories. No manual cleanup
6. **No vendor lock-in** — export to JSON/markdown/sqlite
7. **Dogfood everything** — if we don't use it, don't ship it

**Akane's design principles:** High value changes over busywork. Keep solutions simple. Extend existing APIs before creating new endpoints. Don't act prematurely on speculative problems. Keep MCP tool count minimal.

---

## 7. Tone & Style Preferences

### Core Rules

- **Cooperative tone always** — never attack competitors. "Here's how we're different" not "competitors are bad."
- **Jason's principle:** "Don't burn bridges — tech ecosystems thrive when there's a lot of contribution from open source and adoption." Applies to all competitor positioning, marketing copy, and README comparisons.
- **Lead with the problem:** "Your agent forgets everything between sessions" → "Here's the fix in one command."
- **Show, don't tell:** GIF of `lore_remember` + `lore_search` across sessions is worth 1000 words.
- **Name-drop competitors generously** in comparison content. No "X is bad" framing.
- **Use "paid" instead of "not free" or "closed source."**
- **No agent names (Diana, Akane) in public marketing copy.**
- **No hype language** ("revolutionary", "game-changing").
- **Honest about trade-offs** — own the ~1.4GB embedding model weight. Never hide a trade-off behind marketing language.

### Message Hierarchy

| Channel | Primary Message |
|---------|----------------|
| README top | "Memory for AI agents that gets smarter the more you use it." |
| HN post | "Local MCP memory server. Feedback loop makes it better with use." |
| dev.to | Comparison: "5 AI Agent Memory Systems Compared (2026)" |
| Reddit | "How Lorekeeper's feedback loop handles memory decay" |
| X/Twitter | 5-tweet thread: problem → feedback loop → benchmarks → features → link |

### Install Commands to Reference

- `pip install lorekeeper-mcp && lorekeeper setup`
- `uvx lorekeeper-mcp` (ephemeral, no install)

---

## 8. Launch Info

### Distribution Channels (Priority Order for Phase A)

1. **Hacker News** — "Show HN: Lorekeeper — self-improving AI agent memory, one command" (HN account restricted currently)
2. **GitHub Trending** — time launch for HN + X virality simultaneously
3. **MCP Directory Submissions** (10 directories): Official Registry (auto-ingests to Glama, Smithery, PulseMCP), Glama (105K visits), mcp.so (238K), PulseMCP (277K), MCP Market (1.4M, #1), mcpservers.org (504K), ClaudePluginHub (168K), MCP.Directory (134K), awesome-claude (187K), awesome-mcp-servers PR (27K★)
4. **dev.to** — "5 AI Agent Memory Systems Compared (2026) — and the one that self-improves" (listicle/comparison format, proven best performer)
5. **Reddit** — r/ClaudeAI, r/MCP, r/Python
6. **X/Twitter** — 5-tweet thread drafted, no account yet

### Existing Marketing Materials

- **dev.to post:** 7 draft variations in `docs/launch/post-sample-*.md` (benchmark, narrative, tutorial, listicle, why-I-built, numbered reasons, hot take)
- **X thread:** `docs/launch/x-thread.md` — 5 tweets
- **HN post:** `docs/launch/hn-post.md`
- **Banners:** `docs/launch/lorekeeper-banner-1200x630.png`, `-square.png`, `-thumb.png`
- **Directory submission template:** In `docs/launch/diana-tasks.md`
- **Server.json (MCP Registry):** In `docs/launch/diana-tasks.md`

### The Viral Loop

```
Developer installs Lorekeeper
  → Agent remembers better
  → Developer sees improvement in daily work
  → Team member asks "how is your agent so fast?"
  → pip install lorekeeper (referral, no effort)
  → Shared namespace makes team memory compound
```

**Key insight:** Comparative benchmarking (against agentmemory/mem0) is the proven viral pattern — agentmemory's "92% fewer tokens" framing drove 21.7K stars.

---

## 9. Risks

| Risk | Phase | Likelihood | Mitigation |
|------|-------|------------|------------|
| Anthropic/OpenAI ship free built-in memory | B-C | High | Multi-agent + local-first moat |
| Agent framework ships its own memory | B | Medium | Stay MCP-protocol-aligned |
| Tensor size grows linearly | B-C | Medium | Sharding + federation |
| Embedding model dependency (1.4GB) blocks adoption | A | Medium | Make embedding optional, own the trade-off |
| Competitor clones feedback loop | B-C | Low-Med | Requires whole system — hard to clone partially |
| Enterprise wants cloud-only compliance | C | Medium | Always support air-gapped deployment |
| MCP protocol evolves incompatibly | A-C | Low | MCP-native, track working groups |

---

## 10. Operational Context

- **Creator/Product owner:** Jason (jessinra)
- **Telegram:** Prefers concise messages. Squash-merge to main. Files symptoms first, not diagnoses. Prefers judgment over persistence — don't brute-force dead ends, flag as blocker.
- **No X/Twitter account** — don't plan launch activities there.
- **Marketing autonomy granted** — full autonomy. Flow: research → doc → delegate to Diana with steps. Prefers automation over manual work.
- **Product ideation filter:** Ideas must serve a Phase A objective (onboarding velocity, feedback loop visibility, narrative creation, distribution). Must align with growth strategy. Extend existing MCP tools before proposing new ones.
- **Agent team:** Akane (PM), Diana (eng), Bella (PA), Chisa (GTM/content) — all AI agents. Profiles under `~/.hermes/profiles/`.
- **Diana:** Senior engineer. Files tickets with precise ACs for Diana, stop. No prototypes. Never touch tags, releases, version bumps, or PyPI without explicit instruction.