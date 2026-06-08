# Lorekeeper Positioning Manifesto

> **Self-improving memory for AI agents. One command, no cloud, no config.**

---

## 1. The Problem

AI agents have amnesia. Every new session is a blank slate.

You re-explain project context. You re-state preferences. You re-teach patterns. The agent starts fresh, makes the same mistakes, asks the same questions. This is the single biggest gap between "impressive demo" and "daily driver" for AI coding agents.

The problem is universal — every Claude Code, Cursor, Hermes, Copilot, and Codex user hits it. And it's painful enough that developers will install _something_ to fix it, if the fix is simple enough.

---

## 2. The Landscape

The "AI agent memory" category exploded in 2025-2026. Here's what exists:

### File-based (built-in)

- **CLAUDE.md, .cursorrules, AGENTS.md** — hand-written context files
- **Claude Code auto-memory** — writes notes automatically
- **Trade-off:** Manual curation, no search, no decay, no dedup. Scales to ~dozens of notes, then breaks.

### Cloud memory services

- **Mem0 Cloud** — library-first, pushing managed cloud
- **Zep** — cloud with knowledge graph
- **Trade-off:** Data leaves your machine, requires API keys, ongoing cost. Good for production apps, overkill for a solo developer.

### Docker-based memory servers

- **Hindsight (Vectorize)** — state-of-the-art claims, Docker deployment
- **Trade-off:** Requires Docker. Ops overhead for what should be a simple tool. Not wrong for teams, but not frictionless.

### Library-based (build your own)

- **Mem0** — 41k stars, 14M downloads, AWS adopters. The dominant engine.
- **Trade-off:** You're not done after `pip install mem0ai`. You still need to write integration code, build an MCP wrapper, manage embeddings, handle errors. It's a library, not a product.

### Other MCP memory servers (the new wave)

- **agentmemory (rohitg00)** — 21.7k stars. Node.js, `npx` install. Auto-captures tool calls via hooks. Real-time viewer (dashboard). Benchmark-driven, 11-language README. Viral growth since mid-May 2026. **The biggest new entrant.**
- **sqlite-memory (sqliteai)** — launched May 2026. Markdown-based, semantic search.
- **Neural Memory** — 28 MCP tools, spreading activation. Feature-heavy.
- **ai-memory (alphaonedev)** — FTS5 keyword-first. Fast but no semantic.
- **Anthropic's official MCP memory** — entity-relation graph. Simple but basic.
- **MCP Backpack** — key-value only. No semantic search.
- **Supermemory** — API-based embedder.
- **phloem (CanopyHQ)** — local-first, causal graphs, citation verification.

### The pattern

Every solution picks **at most two** from:

- Simple setup
- Smart retrieval
- Self-improving

File-based: simple setup ✓, smart retrieval ✗, self-improving ✗
Cloud services: smart retrieval ✓, self-improving ✗, simple setup ✗ (needs API keys + config)
Docker servers: simple setup ✗, smart retrieval ✓, self-improving ✗
Library-based: smart retrieval ✓, simple setup ✗, self-improving ✗

**Nobody has all three.**

---

## 3. Our Position

> **Self-improving memory for AI agents. One command, no cloud, no config.**

Lorekeeper is the **install-and-forget** memory server. You don't integrate it. You don't configure it. You don't maintain it. You `pip install` it, connect your agent, and it starts remembering — and **gets better the more you use it.**

### Positioning statement (internal)

_For developers using AI coding agents who are tired of their agents forgetting context between sessions, Lorekeeper is a local-first MCP memory server that gives agents persistent, self-improving memory. Unlike cloud services or library-based solutions, Lorekeeper installs in one command, requires zero configuration, and gets smarter every time you use it — with bad memories decaying and good memories rising automatically._

### Positioning statement (external / README top)

> **Memory for AI agents that gets smarter the more you use it.**
>
> `pip install lorekeeper` → connect your agent → it remembers.  
> No cloud. No config. No maintenance.

---

## 4. Our Values

These guide every product decision — what to build, what to say no to, how to design.

### 4.1 Zero friction is the feature

The hardest thing in developer tools is getting someone to try it. Every extra step — Docker, API key, cloud config, integration code — loses 50% of potential users.

**Rule:** A new user should go from `pip install` to their first stored memory in under 2 minutes. Any feature that adds setup friction must justify itself with extreme value.

### 4.2 Self-improving, not just self-storing

Most "memory" solutions are just write-and-read. Lorekeeper's feedback loop (`lore_update` → score adjustment → confidence EMA → soft-delete + auto-link) means memory gets _better_ with use, not just _bigger_.

**Rule:** Every feature should either (a) directly improve retrieval quality, or (b) reduce friction. Cosmetic features are debt.

### 4.3 Local-first always

Your data belongs on your machine. No cloud dependency, no vendor lock-in, no API keys, no data leaving your network. Cloud features can be _added_ later as optional extras, never required.

**Rule:** The offline, local install is always the primary experience. Cloud is an optional add-on, never a requirement.

### 4.4 Universal, not exclusive

One MCP server works with every agent. Not just Claude Code, not just Cursor, not just Hermes — any MCP-compatible client. We don't pick winners.

**Rule:** Never optimize for one agent at the expense of others. The protocol (MCP) is the abstraction.

### 4.5 Simple beats clever

Resist the urge to add "one more tool" or "one more config option." The 8 MCP tools Lorekeeper has today cover the full memory lifecycle. Every new tool must prove it's necessary, not just possible.

**Rule:** New features must be:

- Observed pain (not predicted)
- Measurable improvement (not speculative)
- Simpler than the alternative (not compensating for poor design)

### 4.6 Honest about trade-offs

Don't pretend to be something we're not. We use local embeddings (sentence-transformers + PyTorch). That's ~1.4GB. Own it. Document it. Make it clear what the user is getting for that weight.

**Rule:** Never hide a trade-off behind marketing language. Users will discover it anyway, and trust lost is hard to regain.

---

## 5. Our Moat

Features are copyable. The quality loop is not.

### Built by agents, for agents

Lorekeeper is developed _using_ AI agents — Claude Code, Hermes, Diana, and the PM agent (Akane) all participate in the development cycle. The development process itself is a working example of what we sell:

```
agent builds feature → uses memory → captures learnings →
improves memory quality → shares insight across agents →
builds the next feature better
```

Every design decision in Lorekeeper comes from **actual agent usage**, not theoretical assumptions. The tools are shaped by the agents that use them daily — and the agents that build them.

This means:

- **Dogfooding at the product level** — we've been using Lorekeeper to develop Lorekeeper since day one. Every pain point we fix is a real agent pain.
- **Agent-native design** — not a library retrofitted for MCP, not a human UI tool with an API bolted on. The tool schemas, return types, and workflows are shaped by what agents actually need.
- **The development is the demo** — the agentic loop documented in the repo isn't aspirational copy; it's how we work.

### The feedback loop (defensible)

```
agent uses memories → lore_update scores relevance →
score drifts up/down → unreliable memories soft-delete →
search results improve → agent trusts it more → uses it more
```

This compounds. A fresh install and a 3-month-old install are **different products**. No competitor has this because it requires the _whole system_ working together:

- Hybrid search (semantic + BM25 + score + usage + time-decay)
- Score adjustment (delta driven by confidence-weighted feedback)
- Confidence EMA (20-window rolling average)
- Soft-delete (confidence ≤ 2 + useful=false → gone forever)
- Auto-linking (duplicate-guarded, configurable threshold)
- Dedup (blocks insert of near-identical memories)

### Network effects (emerging)

More usage → better memory quality → more reliable agent → more usage. The system feeds itself. This is a _product_ moat, not a technology moat — and the hardest kind to replicate.

### Also defensible:

| Asset                       | Why hard to copy                                                               |
| --------------------------- | ------------------------------------------------------------------------------ |
| **31 done tickets**         | Maturity. 266 tests. Battle-tested through real use.                           |
| **Dashboard**               | Full web UI. Other memory servers are CLI-only.                                |
| **Reflection system**       | Auto-extract learnings from sessions. Requires feedback loop integration.      |
| **MCP-native from day one** | Not an afterthought library wrapper. The whole system was designed around MCP. |

---

## 6. Our Audience

### Primary: Solo developers using AI coding agents

- Uses Claude Code, Cursor, Hermes, OpenCode, Codex, or Copilot CLI
- Frustrated by agents forgetting context
- Values simplicity over features
- Wants local-first, no cloud dependency
- Technical enough to edit an MCP config file
- Not interested in maintaining a memory infrastructure

### Secondary: Agent framework users

- Building multi-agent systems
- Need shared, namespace-isolated memory
- Want a drop-in MCP server, not another framework

### Not for (yet):

- Enterprise teams (need RBAC, audit, SSO — Lorekeeper doesn't have these)
- Consumer AI apps (wrong distribution model)
- Non-technical users (MCP isn't there yet)

---

## 7. Distribution Strategy

### Primary channel: GitHub

README is the landing page. It must:

- Sell in 3 seconds (hero section + screenshot)
- Convince in 30 seconds (value prop + quick demo)
- Convert in 2 minutes (pip install + agent config)
- Retain through quality (documentation, examples, community)

### Secondary channels:

| Channel              | Tactic                                                                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **PyPI**             | `pip install lorekeeper`. Must be the default install path.                                                                              |
| **Reddit**           | r/ClaudeAI, r/MCP, r/ClaudeCode — share comparisons, answer questions.                                                                   |
| **MCP server lists** | awesome-mcp-servers, mcpservers.org, mcpmarket.com — be listed everywhere.                                                               |
| **YouTube**          | 2-minute setup demo. Show pip install → agent config → first memory.                                                                     |
| **Word of mouth**    | Users who try it and it _just works_ tell other developers. This is the strongest channel — invest in the experience, not the marketing. |

### Positioning on these channels:

**Don't attack competitors.** Comparison tables are fine, but the tone is "here's how we're different" not "our competitors are bad."

**Lead with the problem.** "Your agent forgets everything between sessions." → "Here's the fix in one command."

**Show, don't tell.** A GIF of `lore_remember` + `lore_search` across sessions is worth 1000 words.

### The Crowding Space

Agent memory is getting crowded fast. agentmemory (21.7k stars, May 2026) and sqlite-memory (June 2026) launched within weeks of each other. The category is being validated — which means more entrants, not fewer.

**Our strategy is not to out-pace them. It's to out-quality them.**

Let the fast movers educate the market. We watch what works for them, what users complain about, and what the category is converging on. Then we execute — better, simpler, with the feedback loop they can't replicate.

**Fast follower, not fast mover. Quality winner, not quantity winner.**

---

## 8. Our Future

### Phase 1: Beta (this week)

- ✅ Core MCP tools working
- ✅ Dashboard functional
- ✅ 266 tests passing
- ✅ Self-improving feedback loop
- ✅ `pip install lorekeeper` (PyPI)
- ✅ Compelling README that converts

### Phase 2: Launch (post-beta)

- Lighter dependency profile (embedding model optional)
- More agent-specific setup guides
- Community contributions
- Bug reports from real users

### Phase 3: Growth

- Optional cloud sync (read-only on free tier, full on paid)
- Team namespaces
- Hooks for custom feedback pipelines
- Integration with more MCP clients

### Phase 4: Sustainable

Honest monetization that aligns with values:

- Local-first always free
- Optional paid features: cloud backup, team management, priority support
- Never paywall existing features

---

## 9. Comparison Matrix

For the README — positioned neutrally, not as "us vs them":

|                     | File-based | Cloud services   | Docker servers | Library (Mem0) | Lorekeeper                                            |
| ------------------- | ---------- | ---------------- | -------------- | -------------- | ----------------------------------------------------- |
| **Setup**           | Built-in   | API key + config | Docker compose | Write code     | `pip install`                                         |
| **Data location**   | Local      | Cloud            | Local          | Your call      | Local                                                 |
| **Search**          | grep       | Vector           | Vector         | Vector         | Hybrid (semantic + BM25 + time-decay + score + usage) |
| **Self-improving**  | ❌         | ❌               | ❌             | ❌             | ✅ (feedback loop)                                    |
| **Knowledge graph** | ❌         | Paid             | ❌             | Paid           | ✅ Free (auto-link)                                   |
| **Dashboard**       | ❌         | ✅               | ❌             | ❌             | ✅                                                    |
| **Multi-agent**     | ❌         | ✅               | Limited        | ✅             | ✅ (namespace isolation)                              |
| **Dependencies**    | None       | ~300MB           | ~2GB           | ~1.4GB         | ~1.4GB (same as Mem0)                                 |
| **Maintenance**     | Manual     | None             | Ops            | You build it   | None                                                  |

---

## 10. What We Say No To

- **No cloud requirement** — local-first always
- **No API keys** — no signup, no account
- **No Docker** — a memory server shouldn't need container orchestration
- **No feature bloat** — 8 focused tools > 28 mediocre ones
- **No lock-in** — works with every MCP agent
- **No data exfiltration** — your memories stay on your machine
- **No paywalled basics** — auto-linking, search, dashboard are free

---

_Written June 2026 — for beta launch of Lorekeeper v2._
_Source of truth for README positioning, distribution strategy, and product decisions._
