# Lorekeeper Growth Strategy: 10 → 1,000 → 1,000,000 Agents

> _How Lorekeeper evolves from a beta-stage memory server for a handful of agent builders into the universal memory layer for a million agents — without betraying local-first, self-improving values._

---

## Current Baseline (June 2026)

| Metric        | Value                                | Source                                                                                                                                         |
| ------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub stars  | ~tens (pre-beta)                     | Own repo                                                                                                                                       |
| PyPI installs | ~few                                 | Manual tracking                                                                                                                                |
| Active users  | ~1-3 (Jason + agents)                | Dogfooding                                                                                                                                     |
| MCP tools     | 8 core                               | `lore_search`, `lore_remember`, `lore_insert`, `lore_update`, `lore_forget`, `lore_recommend_links`, `lore_reflect`, `lore_processed_sessions` |
| Tests         | 266 unit + E2E                       | `uv run pytest`                                                                                                                                |
| Dashboard     | Functional web UI                    | Port 7777                                                                                                                                      |
| Data store    | SQLite + Chroma/LanceDB              | ~1.4GB embed model                                                                                                                             |
| Backlog       | ~15 active proposals                 | `backlogs/`                                                                                                                                    |
| Marketing     | README marketing pass done (LKPR-71) | Screenshots, use-cases, benchmarks                                                                                                             |
| Positioning   | Manifesto written                    | `docs/positioning-manifesto.md`                                                                                                                |

### North Star

> **A team's agents get smarter together about their specific context — without sharing anything with strangers.**

Not a general-purpose knowledge base. Not a Wikipedia for agents. **Your fleet, your codebase, your project, your team** — every agent's feedback loop cross-pollinates quality signals inside your namespace. Memory that 10 agents on your team have marked useful for "deploy pipeline" surfaces higher for the 11th agent asking about deploys. The collective gets sharper without anyone manually curating.

### Market Context (2026)

- **4.2M weekly active Claude Code users** — 131K GitHub stars, writes 4% of all public GitHub commits
- **4.7M GitHub Copilot paid subscribers** — $2B ARR
- **Cursor at $60B valuation** — $2B ARR
- **MCP ecosystem: 97M monthly SDK downloads**, 9,600+ server records. Growing 232% per 6 months
- **Memory server category exploded** — claude-mem (46K★), agentmemory (21.7K★), MemPalace (41K★), sqlite-memory, Neural Memory
- **mem0: 55K★, $24M raised, 14M+ PyPI downloads, 186M API calls/quarter** — the funded incumbent
- **$6-9.5B total AI coding tool market (2026)**, 22% CAGR

---

## Phase A: Beta Validation (10 → 100 Users)

**Goal:** Prove people want self-improving local memory for their agents. Fix the friction that kills the first impression. Get to 100 GitHub stars and 10 weekly active users.

**Estimated duration:** 4-6 weeks from beta launch.

### The 10-User Product

**Who these users are:** Fellow agent builders, open-source tinkerers, Claude Code / Cursor power users who already use or build memory servers. They'll try anything that promises "one command." They're technically generous — they'll file issues, not just leave.

**What differentiates at 10 users:** Technical quality + zero friction. Early adopters compare architecture, not marketing. They want to see:

- Does the search actually work?
- Is the feedback loop real?
- Can I look under the hood?

### Critical Path — What Must Ship for Beta Launch

| Priority | Feature                                                                                 | Why                                                                                                                 | Evidence                                                                       |
| -------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **P0**   | `lorekeeper setup` auto-detect + inject for Claude Code, Cursor, Copilot, Hermes, Codex | Without this, the user has to manually edit config files. kills conversion.                                         | Our memory says "empty dashboard + no pip install are biggest friction points" |
| **P0**   | `uvx lorekeeper` ephemeral zero-install mode                                            | Show a friend with a single command. No git clone, no pip.                                                          | Memory: "uvx lorekeeper is a high-impact distribution vector"                  |
| **P0**   | Seed prompt on first run                                                                | On first install, show a paste-able prompt that populates ~10 seed memories instantly. Empty state kills retention. | LKPR-55 done                                                                   |
| **P1**   | Dashboard empty state (fixed)                                                           | Fresh install shouldn't show blank panels. Show "this is what memories look like" sample.                           | LKPR-56 in progress                                                            |
| **P2**   | README marketing pass                                                                   | Screenshots, use-cases, benchmark table, 3-second sell.                                                             | LKPR-71 done                                                                   |
| **P2**   | Benchmark eval script                                                                   | "Lorekeeper saved X tokens vs raw context" — reproducible, verifiable claims.                                       | LKPR-70 in progress                                                            |

### Distribution Plan (Beta)

| Channel                                    | Action                                                                                                | Expected Impact                                                                |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Hacker News launch**                     | Write launch post: "Show HN: Lorekeeper — self-improving AI agent memory, one command"                | 500-2K stars in 48h, drives initial traffic                                    |
| **GitHub Trending**                        | Time launch for HN + X virality simultaneously                                                        | "Day 5 on GitHub Trending All Languages" is the pattern (agentmemory did this) |
| **Reddit**                                 | Post comparison on r/ClaudeAI, r/MCP, r/Python. "How Lorekeeper's feedback loop handles memory decay" | Lower direct conversion, starts discussions                                    |
| **MCP Registry**                           | List Lorekeeper on `mcpservers.org`, `awesome-mcp-servers`, `mcpmarket.com`                           | Discoverability from every MCP client                                          |
| **agentmemory mem0 claude-mem comparison** | "What Lorekeeper does that agentmemory can't" — the feedback loop. Published on X + blog.             | The "X% fewer tokens" comparative framing worked for agentmemory (21.7K stars) |

### Success Criteria (Phase A Exit)

```
- 100 GitHub stars
- 10 weekly active users (WAU)
- < 5% crash rate on install
- < 30s median time from pip install to first memory
- 3+ issues filed by external users (signals engagement)
```

### What NOT to Build (Phase A)

- Multi-user features (wait for validation)
- Cloud sync (contradicts local-first values at this stage)
- Plugin system (too far ahead)
- Enterprise features (wrong audience)
- More MCP tools (8 is fine — resist bloat)

---

## Phase B: Team Tier — Shared Server (1,000 → 10,000 Users)

**Goal:** Move from "cool project" to "engineering team essential." Ship the team shared server — one Lorekeeper instance serving a team's entire agent fleet. Establish the bottom-up PLG motion (individual → team → org). Get to 1,000 GitHub stars and first team-tier revenue.

**This is the critical transition.** The product thesis shifts from "memory for your agent" to "memory for your team's agents." The knowledge that matters most — internal service quirks, deployment gotchas, undocumented APIs — is never written down. At team scale, Lorekeeper propagates it automatically across the team's agent fleet.

**Estimated duration:** 3-6 months after beta launch.

### The Product at Team Scale

Engineer A's Claude Code discovers that payment-service silently drops requests with unicode idempotency keys → stores the memory → Engineer B's Cursor agent surfaces it next day when touching the same service. Nobody briefed B. Nobody wrote a Confluence doc. The knowledge propagated on its own.

| Tier                     | Offering                      | Auth                 | Data Model                                       | First Customer    |
| ------------------------ | ----------------------------- | -------------------- | ------------------------------------------------ | ----------------- |
| **Individual** (current) | pip install, single namespace | None                 | Local SQLite + vector                            | Solo devs         |
| **Team** (Phase B)       | Shared server per team        | Token auth (LKPR-39) | Namespaced: `{team}/shared`, `{team}/{engineer}` | 5–50 person teams |

### What Differentiates at Team Scale

Competitors at this scale: mem0 (library, needs integration), claude-mem (single-user Node), agentmemory (single-user, Node), Zep (cloud, expensive for teams).

Lorekeeper's edge: **Your team's agents get smarter together about your specific codebase — without sharing anything externally.** No competitor offers cross-agent quality signal inside a team namespace.

### Critical Path — What Ships for Phase B

| Priority | Feature                         | Ticket             | Why                                                                                                                                                               |
| -------- | ------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P0**   | Token / namespace auth          | LKPR-39            | Enterprise gate. No team will use a shared server with plain env var scoping. Also unblocks CI/CD + remote deployment. Build this before any team-tier marketing. |
| **P0**   | Provenance tagging              | LKPR-18            | Metadata foundation for trust in shared namespaces. Agents need to know "who discovered this" to calibrate whether to trust an org-shared memory.                 |
| **P0**   | Org namespaces                  | LKPR-40            | `{team}/shared` visible by all team agents, `{team}/{engineer}` private. Isolates project/team/personal memories.                                                 |
| **P1**   | Multi-reader, controlled-writer | Extends LKPR-39/40 | 10 agents read the shared KB, 2 write. Trust per namespace per agent.                                                                                             |
| **P1**   | Herd memory awareness           | New                | `lore_search` shows "3 agents in your namespace also found this relevant" — social proof from within your team                                                    |
| **P1**   | Memory health dashboard tab     | New                | Which memories are active vs. stale? Hit rate per agent? Where are agents forgetting?                                                                             |
| **P2**   | Self-hosted deployment docs     | New (gap)          | Dockerfile + Helm chart + deployment guide. Orgs won't send internal data to an external server.                                                                  |
| **P2**   | Memory quality governance       | New (gap)          | Write permissions + quality gates for shared namespaces. Auto-flag low-confidence memories before they propagate to org/shared.                                   |
| **P2**   | Import/export                   | LKPR-53 / LKPR-68  | Migrate from mem0, claude-mem, JSON, markdown                                                                                                                     |

**Build order:** LKPR-39 (token auth) → LKPR-40 (namespaces) → LKPR-18 (provenance) → quality governance → deployment docs. Ship team server as MVP after LKPR-39 + LKPR-40. Everything else is polish.

**What to deprioritize (Phase B):**

- Plugin system (ecosystem depends on critical mass — not yet)
- Cloud sync (still pure local-first)
- Multi-instance federation (sharding is a Phase C problem)

### Distribution Plan (Phase B)

| Channel                               | Tactic                                                                                                            | Why This Works Now                                                                                        |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Comparative benchmarks**            | "Lorekeeper vs agentmemory vs mem0: retrieval accuracy over 100 sessions"                                         | With 100 users, you have real data. Publish reproducible benchmarks. agentmemory did this — worked.       |
| **Technical blog posts**              | "How we built a self-improving memory loop" (deep architecture post on dev.to)                                    | Developers at this scale read architecture blogs. The feedback loop is interesting enough to write about. |
| **YouTube setup demo**                | 2-min video: pip install → agent config → first memory → dashboard. No talking, just screen.                      | Visual proof converts. "Show, don't tell."                                                                |
| **Agent-specific setup guides**       | "Lorekeeper for [Claude Code / Cursor / Hermes / Copilot / Codex]" — one dedicated guide per agent                | SEO surface area. Users search "memory for Claude Code" not "MCP memory server"                           |
| **Reddit FAQ farming**                | Answer "what memory server should I use" questions on r/claudeai, r/mcp, r/cursor with calm, informed comparisons | Long-tail conversions. Be the helpful answer, not the ad.                                                 |
| **Open-source contribution workflow** | Label issues `good-first-issue`, `help-wanted`. Accept PRs.                                                       | Community ownership drives retention.                                                                     |
| **X/Twitter virality thread**         | "Thread: 4 months of building an agent memory server that improves itself" — narrative arc                        | Human story of building (Jason's story) resonates more than product features                              |

### Growth Mechanics (Phase B)

**The viral loop that makes this phase work:**

```
Developer installs Lorekeeper
  → Agent remembers better
  → Developer sees improvement in daily work
  → Team member asks "how is your agent so fast?"
  → pip install lorekeeper (referral, no effort)
  → Shared namespace makes team memory compound
```

**Network effects kick in at this scale:**

| Metric                 | User-Level                        | Team-Level                                                      |
| ---------------------- | --------------------------------- | --------------------------------------------------------------- |
| Memory quality         | Improves with use (feedback loop) | Improves faster (more agents → more feedback → more refinement) |
| Retrieval accuracy     | Good                              | Better — shared context disambiguates                           |
| Knowledge completeness | What one agent learned            | What the whole team learned                                     |
| Switching cost         | Low (single user)                 | High (team context is in the memory)                            |

### Success Criteria (Phase B Exit)

```
- 1,000 GitHub stars
- 1,000 pip installs/month
- 100 weekly active users (WAU)
- 5+ teams using shared namespace server (self-hosted)
- Team server MVP shipped: LKPR-39 (auth) + LKPR-40 (namespaces)
- < 1% uninstall rate per 30 days
- 30+ closed issues from external users
- 5+ external contributors (PRs accepted)
- Retrieval accuracy benchmark: 85%+ precision@5 (up from baseline)
```

### Revenue Consideration (Phase B — Stack as Option, Don't Charge)

At team scale, the bottom-up PLG motion is the engine:

```
Engineer installs personally (free)
  → "My agent is noticeably better than my colleague's"
  → Colleague installs
  → Small team of 5 wants shared server
  → First team-tier evaluation
```

**Do not charge individuals.** The individual free tier is the acquisition channel. If a team offers to pay for early-access team features (token auth, shared namespace), take it as a design partnership — the learnings are worth more than the money.

Pricing anchoring for when team tier ships: $50/seat/month (benchmark: Confluence $5, Notion $10, Datadog $15; agent memory is more specialized than a wiki, less critical than monitoring — revisit when selling).

---

## Phase C: Platform & Ecosystem (1,000,000 Agents)

**Goal:** Become the default memory layer for AI agents — the "Wikipedia of agent experience." Transition from open-source project to sustainable platform. 50,000+ GitHub stars. 10,000+ WAU.

**Estimated duration:** 12-24 months after beta launch.

### The Market Shift (Phase C)

At this scale, the world looks different:

- **AI agents are not a novelty** — they handle 20%+ of an engineer's workload (industry projection for 2027)
- **Every developer runs 5+ agents** — coding, PM, testing, documentation, design
- **Every team runs 20+ agents** — multiple devs, multiple workflows, one shared context
- **"MCP" is no longer a niche protocol** — it's the standard, like HTTP for LLMs
- **Enterprise is buying** — Fortune 500 teams need compliant, auditable agent memory
- **Platform memory is the lock-in** — Anthropic, OpenAI, Google are building closed memory into their agent platforms

### What Differentiates at 1M Agents

The question shifts from "does it work?" to "does my entire agent fleet get smarter together?"

**Lorekeeper's edge: Cross-agent quality signal within your namespace.** A memory that 10 agents on your team have rated useful for "deploy pipeline" surfaces higher for the 11th agent — even if that agent has never seen it before. The collective quality signal bootstraps new agents into the team's context instantly.

This is NOT generic internet knowledge ("strangers sharing facts"). It's **your agents, your codebase, your team's patterns** — cross-pollinated inside your namespace. No competitor can offer this because:

- **Single-user memory servers** (claude-mem, agentmemory) — only one agent, no signal to aggregate
- **Cloud services** (Zep, mem0 Cloud) — they have the data but they'd sell it as generic knowledge, not your team's signal
- **File-based** (CLAUDE.md) — manual curation, doesn't scale
- **Platform built-in** (Anthropic, OpenAI) — locked to one provider, can't aggregate across your heterogeneous fleet

Lorekeeper already has the infrastructure: `lore_update`, score drift, confidence EMA. The missing piece is an **opt-in cross-agent score aggregation layer** — anonymized within your namespace, privacy-preserving, zero-config.

### Architectural Evolution

**The 1M-agent product looks nothing like the beta product:**

```
                    Phase A                        Phase C
                    ───────                        ───────
Data model          Single SQLite                  Sharded + Replicated
Vector store        Local Chroma/LanceDB           Federated vector index
Search              Single-threaded                Distributed, sub-ms
                  No caching                     Multi-tier cache (L1: local, L2: namespace, L3: federation)
Security            None (single user)            RBAC + audit + E2EE
Deployment          pip install                    pip + Helm chart + Kubernetes operator
Sync                None                           Multi-device E2EE sync
Federation          None                           Opt-in knowledge sharing across instances
Plugin system       None                           3rd-party memory processors
Business model      Free                           Free core + paid sync + enterprise
```

### What Ships in Phase C

| Feature                              | Why                                                                                                                                                       | Design Constraint                                                                                 |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Sub-millisecond search**           | 1M concurrent queries requires a completely different search path. Shard by namespace, cache hot memories in LMDB/RocksDB, write-behind merge.            | Must degrade gracefully for single-user installs — no architectural bifurcation                   |
| **Multi-device E2EE sync**           | Users run agents on laptop + CI server + cloud VM. Memories must follow them.                                                                             | End-to-end encrypted, zero-knowledge server. Sync via existing file (git!), not proprietary cloud |
| **Federated knowledge**              | "What do 10K agents know about deploying Kubernetes?" Aggregate patterns without exposing individual memories. Differential privacy on aggregate queries. | Opt-in only. Anonymized. Can be disabled entirely.                                                |
| **Plugin ecosystem**                 | Third-party memory processors: image→text extraction, structured log analysis, compliance filters.                                                        | Sandboxed WASM plugins. MCP tools register themselves.                                            |
| **Memory marketplace**               | Curated knowledge packs: "Rust compilation errors," "AWS IAM patterns," "ML training gotchas." Published by domain experts.                               | Free marketplace, optional paid packs.                                                            |
| **Consensus-based correction**       | When 100 agents mark a memory as outdated, auto-demote it. Self-healing without human curation.                                                           | Threshold-based, configurable by namespace.                                                       |
| **Enterprise tier**                  | SSO, audit logs, retention policies, compliance reports, usage analytics dashboard.                                                                       | API-compatible with core. Bolt-on, not fork.                                                      |
| **Helm chart + Kubernetes operator** | Enterprise teams running 100+ agents in CI/CD pipelines need orchestrated deployment.                                                                     | Stateless server + persistent volume. Scale horizontally.                                         |

### Business Model (Phase C)

**The Obsidian playbook:**

| Tier            | Price          | Features                                                                                                      |
| --------------- | -------------- | ------------------------------------------------------------------------------------------------------------- |
| **Free (Core)** | $0             | Local-first MCP server, all 8 tools, dashboard, feedback loop, namespace isolation. Same as Phase B. Forever. |
| **Sync**        | $4-8/mo        | Multi-device E2EE sync. Memories follow your agents across machines.                                          |
| **Team**        | $15-30/seat/mo | Shared team memory, RBAC, health dashboard, admin controls, priority support.                                 |
| **Enterprise**  | Custom         | SSO, audit logs, compliance, SLA, Helm chart, dedicated support, on-prem deployment.                          |

**Revenue projections at 1M agents:**

| Tier       | % of Users | Count                    | Monthly Revenue                      |
| ---------- | ---------- | ------------------------ | ------------------------------------ |
| Free       | 90%        | 900K agents (180K users) | $0                                   |
| Sync       | 7%         | 70K agents (14K users)   | $56K-$112K                           |
| Team       | 2.5%       | 25K agents (5K users)    | $75K-$150K                           |
| Enterprise | 0.5%       | 5K agents (1K users)     | $50K-$100K+                          |
| **Total**  |            | **1M agents**            | **$181K-$362K/mo → $2.2M-$4.3M ARR** |

At Obsidian's margins (7-person team, zero meetings), ~$3M ARR is a very comfortable business.

### Distribution Plan (Phase C)

| Channel                            | Tactic                                                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **MCP protocol standard meetings** | Lorekeeper maintainer participates in MCP working groups. Influence protocol direction to favor memory federation. |
| **Enterprise sales**               | Targeted outreach to Fortune 500 AI platform teams. "Your agents shouldn't forget everything every session."       |
| **Conference talks**               | Submit talks about the feedback loop, federation architecture, and "what we learned running memory for 1M agents." |
| **Academic publishing**            | Paper on agent memory quality benchmarks. Federated knowledge graph for agent collectives.                         |
| **Ecosystem partnerships**         | Claude Code, Cursor, Hermes, Codex all bundle Lorekeeper setup as recommended memory layer.                        |
| **Marketplace curation**           | Top knowledge packs get promoted. Domain experts become Lorekeeper advocates.                                      |
| **Cloud marketplace**              | AWS/GCP/Azure marketplace listing for managed Lorekeeper (enterprise path of least resistance).                    |

### Competitive Positioning at Scale

| Competitor                    | Position                   | Lorekeeper's Angle                                                                 |
| ----------------------------- | -------------------------- | ---------------------------------------------------------------------------------- |
| **Anthropic built-in memory** | Locked to Claude ecosystem | "Your memory shouldn't fire your other agents. Lorekeeper works with every agent." |
| **OpenAI memory**             | Locked to ChatGPT/Codex    | Same argument. Multi-agent, multi-provider.                                        |
| **mem0 Cloud**                | Cloud-dependent            | "Your data stays local. Sync is optional, not required."                           |
| **Zep**                       | Cloud, expensive           | "Free for what Zep charges for. And we get better with use."                       |
| **agentmemory**               | Single-user Node           | "Python-native, team-ready. And the feedback loop is real."                        |

### Success Criteria (Phase C Exit)

```
- 50,000+ GitHub stars
- 10,000+ weekly active users
- 1,000,000+ active agent instances
- 50+ community plugins in marketplace
- $2M+ ARR from sync/team/enterprise
- 80%+ market awareness among AI-coded developers
- MCP protocol co-maintainer status
```

---

## Risk Register

| Risk                                                   | Phase | Likelihood | Mitigation                                                                                                                                                                        |
| ------------------------------------------------------ | ----- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Anthropic/OpenAI ship free built-in memory**         | B-C   | High       | Multi-agent + local-first moat. Their memory is locked to their ecosystem. Ours works with every agent.                                                                           |
| **Agent framework ships its own memory**               | B     | Medium     | Stay MCP-protocol-aligned. Frameworks come and go, protocol is durable.                                                                                                           |
| **Tensor size grows linearly with users**              | B-C   | Medium     | Sharding + federation. Single-user install stays fast. Scale cost is the namespace operator's concern.                                                                            |
| **Embedding model dependency (1.4GB) blocks adoption** | A     | Medium     | Phase B feature: make embedding model optional (use lightweight or cloud embedding). Talk about it honestly — own the trade-off.                                                  |
| **Competitor clones feedback loop**                    | B-C   | Low-Medium | The loop requires the whole system: hybrid search, score drift, confidence EMA, soft-delete, dedup, auto-link. Cloning one piece without all of them is worse than not having it. |
| **Enterprise wants cloud-only compliance**             | C     | Medium     | Always support fully air-gapped deployment. Sync and federation are optional. Core server works with no network.                                                                  |
| **MCP protocol evolves in incompatible direction**     | A-C   | Low        | We're MCP-native. Protocol evolution is our platform getting better. Track working groups, contribute early.                                                                      |

---

## Milestone Summary

```
                    Phase A (Now → Jul 2026)       Phase B (Jul 2026 → Jan 2027)   Phase C (2027-2028)
                    ─────────────────────────       ─────────────────────────     ──────────────────
Product             Individual (free)               Team server (self-hosted)      Org platform (managed + enterprise)
Stars               100                             1,000                           50,000
WAU                 10                              100                             10,000
Agent instances     ~50                             ~5,000                          1,000,000
Revenue             $0                              $0 (design partnerships)        $2-4M ARR
Team size           1-2                             design partners (2-4 eng)       6-8 eng
Key metric          Days to first memory            Teams using shared server       Network effects
Biggest risk        Empty dashboard kills            Auth scope creep delaying       Competitor platform lock-in
                     onboarding                      team server ship
Key gate            Beta launch                     LKPR-39 (token auth)            First $500K enterprise deal
                                                     + LKPR-40 (namespaces)
Build order                                         LKPR-39 → LKPR-40 →             Governance → admin → deployment
                                                     LKPR-18 → governance            docs → enterprise features
```

---

## Appendix A: Funnel Math

### Projected conversion at each phase

```
                                   Phase A          Phase B          Phase C
                                   ────────         ────────         ────────
GitHub visitors/mo                 5,000            50,000           500,000
→ Stars (5% conversion)           250              2,500            25,000
→ pip installs (20% of stars)     50               500              5,000
→ First use (40%)                 20               200              2,000
→ WAU (30% of first use)          6                60               600
```

### What drives each phase's growth

- **Phase A:** HN launch + GitHub Trending + MCP Registry listings
- **Phase B:** Technical blog posts + agent-specific guides + Reddit + word of mouth from 100 users
- **Phase C:** Ecosystem partnerships + enterprise sales + conference talks + marketplace effects

---

## Appendix B: Competitive Landscape Updates

### Direct MCP Memory Servers (Current — June 2026)

| Product        | Stars    | Stage             | Notes                                  |
| -------------- | -------- | ----------------- | -------------------------------------- |
| claude-mem     | ~46K     | v13+              | Node.js/Bun, lifecycle hooks           |
| agentmemory    | ~21.7K   | Active            | TypeScript, viral growth, Product Hunt |
| MemPalace      | ~41K     | Fastest growth    | Doubled in 2 months                    |
| sqlite-memory  | New      | Launched Jun 2026 | Markdown-based                         |
| Neural Memory  | —        | Active            | 28 tools, spreading activation         |
| **Lorekeeper** | **< 10** | **Pre-beta**      | **Python, feedback loop, dashboard**   |

### Funded Competitors

| Product            | Funding         | Stage               | Threat Level                  |
| ------------------ | --------------- | ------------------- | ----------------------------- |
| mem0               | $24M (Series A) | 55K★, 14M downloads | Medium — library, not product |
| Zep                | $15M+           | Enterprise memory   | Low — cloud-only, expensive   |
| Anthropic built-in | Infinite        | Beta                | High — ecosystem lock-in risk |
| OpenAI built-in    | Infinite        | Alpha               | High — same                   |

---

## Appendix C: Key Design Principles (Maintain Across All Phases)

1. **Local-first never optional** — Cloud features are add-ons, never requirements
2. **One command install** stays the default path forever
3. **The feedback loop is the moat** — protect it at all costs. No feature may degrade search quality
4. **8 MCP tools, ±2** — resist tool bloat. Every new tool must prove necessity
5. **Ratings degrade** — automatic downranking of unused/unhelpful memories. No manual cleanup needed
6. **No vendor lock-in** — export to JSON/markdown/sqlite. Running Lorekeeper shouldn't be irreversible
7. **Dogfood everything** — if we don't use it, don't ship it

---

_Written June 2026. Based on 17-source market research, competitor analysis, 36 marketing skill patterns, and the existing positioning manifesto at `docs/positioning-manifesto.md`._

_This is a living document. Update after every major milestone._
