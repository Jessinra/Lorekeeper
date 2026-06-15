# Lorekeeper v0.3.0 Beta Launch Plan

**Status:** Draft | **Owner:** Akane (strategy) → Diana (execution)
**Target:** Phase A exit (100 stars, 10 WAU)

---

## 1. Competitive Landscape & Positioning

### The Market

| Competitor | GitHub Stars | Type | Our Advantage |
|------------|-------------|------|---------------|
| **Mem0** | ~55K | General memory SDK (Python lib) | MCP-native: one `uvx` command works everywhere |
| **Letta (MemGPT)** | ~12K | Agent platform (Docker) | Zero ops: no Docker, no cloud |
| **Zep** | ~? | Temporal knowledge graphs (cloud) | Local-first: data never leaves your machine |
| **Supermemory / Cognee** | ~2-5K | Various | Feedback loop: memory self-improves with use |

### Our Positioning

> **"Self-improving memory for AI agents — one command, no cloud, no config."**

Key differentiators:
1. **MCP-first architecture** — `uvx lorekeeper-mcp` makes it the simplest memory to add to any agent (Claude Desktop, Cursor, VS Code, Codex)
2. **Feedback loop** — `lore_reflect` automatically creates memories that get sharper with use (proven: LongMemEval-S R@1 84.6%)
3. **`lorekeeper setup`** — auto-detects agents, injects MCP config in one command (claude-mem setup is manual)
4. **No API keys, no cloud, no Docker** — `% pip install lorekeeper-mcp` and go

### The Gap We Fill

No MCP server dominates the AI memory niche. The comparison articles (published every few weeks) list Mem0, Letta, Zep, Cognee — **none are MCP servers**. There are memory MCP servers listed on directories but none have significant traction. This is our window.

---

## 2. Distribution Strategy (4 Phases)

### Phase 0: Foundation (NOW — this weekend)
*Do these before any public launch*

| # | Action | Details |
|---|--------|---------|
| 0.1 | ✅ Fix banner logos | Done — exact official logo now renders in all 3 sizes |
| 0.2 | ✅ Add SECURITY.md | Done — vulnerability disclosure policy |
| 0.3 | **Submit to official MCP Registry** | `mcp-publisher` CLI. Feeds Glama, PulseMCP, Smithery. Use `gh` OIDC or GitHub token |
| 0.4 | **Submit to Glama.ai** | ~105K monthly visits, quality score 0-100. Add server via `glama.ai/mcp/servers` → "Add Server" |
| 0.5 | **Submit to mcp.so** | ~238K visits. Free submit form |
| 0.6 | **Submit to PulseMCP** | ~277K visits, auto-ingests from official registry |
| 0.7 | **Submit to mcpservers.org** | ~504K visits (already submitted earlier — pending review) |
| 0.8 | **Submit to MCP Market** | ~1.4M visits (#1 by traffic). Free listing tier exists |
| 0.9 | **PR to awesome-mcp-servers** | punkpeye/awesome-mcp-servers (27K⭐) — PR via GitHub |
| 0.10 | **Submit to ClaudePluginHub** | 168K visits. Free listing |
| 0.11 | **Submit to MCP.Directory** | 134K visits. Free listing |
| 0.12 | **Submit to Awesome Claude** | 187K visits. Free listing |

**Effort:** ~2h total for all submissions. Diana should batch these.

### Phase 1: Content Launch (Week 1)
*Drive awareness through developer-targeted content*

**Primary channel: dev.to** — strongest for dev tools
- **Post format:** Comparison/listicle (proven format: 1,846 reactions for top posts)
- **Title angle:** "5 AI Agent Memory Systems Compared (2026) — and the one that self-improves"
- **Banner:** Our 1200×630 PNG (logo fixed)
- **Tone:** Cooperative, educational. Name-drop competitors generously. No "X is bad" framing.
- **Call-to-action:** `pip install lorekeeper-mcp && lorekeeper setup`

**Secondary: Reddit**
- r/ClaudeAI (largest audience for MCP users)
- r/MCP (niche but targeted)
- r/Python (broad dev audience)
- **Timing:** Day 2 after dev.to post

**Tertiary: X thread** (when account available)
- 5-tweet thread already drafted in `docs/launch/x-thread.md`

### Phase 2: SEO & Directory Presence (Ongoing)
*Build long-term discoverability*

- Get listed in comparison articles (contact writers of "Mem0 vs Letta vs Zep" pieces)
- **lorekeeper.dev** domain authority (DR currently low — backlinks from MCP directories help)
- Blog benchmark results as follow-up piece
- daily.dev syndication

### Phase 3: HN Launch (When Account Eligible)
*Timed for maximum impact*

- Show HN post: "Show HN: Lorekeeper — self-improving AI agent memory, one command"
- Coordinate with X thread + GitHub release simultaneously
- Monitor comments, respond immediately

---

## 3. Current Readiness Audit

| Asset | Status | Action Needed |
|-------|--------|---------------|
| GitHub README | ✅ Good | README has comparison table, install instructions, screenshots |
| Documentation site | ✅ Live | lorekeeper.dev, MkDocs, linked from README |
| PyPI package | ✅ Published | `lorekeeper-mcp` v0.3.0 |
| `uvx` install | ✅ Verified | `uvx lorekeeper-mcp` works ephemerally |
| Banner logos | ✅ Fixed | Official logo, 3 sizes |
| SECURITY.md | ✅ Added | Vulnerability disclosure policy |
| MCP topic tag | ✅ Added | `mcp-server` on GitHub repo |
| License | ✅ Apache 2.0 | Glama prefers MIT but Apache is acceptable |
| GitHub Actions CI | ✅ Setup | Build + test matrix |
| **Official MCP Registry** | ❌ Missing | Need `mcp-publisher` submission |
| **Glama listing** | ❌ Missing | Not listed at all |
| **mcp.so listing** | ❌ Missing | Not listed |
| **PulseMCP listing** | ❌ Missing | Not listed |
| **awesome-mcp-servers** | ❌ Missing | PR not submitted |
| **Dev.to post** | ⏳ Drafted | 7 variations exist, need to choose one |
| **X thread** | ⏳ Drafted | Ready but no account to post |
| **HN post** | ⏳ Drafted | Ready but account restricted |

---

## 4. Recommended Action Sequence

### For Diana (this weekend):

**Day 1 — Foundation:**
1. Install `mcp-publisher`: `go install github.com/modelcontextprotocol/registry/cmd/mcp-publisher@latest`
2. Authenticate via GitHub token: `mcp-publisher auth login`
3. Create `server.json` with Lorekeeper metadata
4. Publish: `mcp-publisher publish server.json`
5. Submit to Glama: https://glama.ai/mcp/servers → "Add Server"
6. Submit to mcp.so: https://mcp.so/submit
7. Submit to PulseMCP: https://pulsemcp.com/submit
8. Submit to MCP Market: https://mcpmarket.com/submit
9. Submit to ClaudePluginHub, MCP.Directory, Awesome Claude
10. Open PR to punkpeye/awesome-mcp-servers

**Day 2 — Content:**
1. Choose best dev.to post variation (recommend: #4 listicle or #7 hot take)
2. Publish to dev.to with banner image
3. On Day 3, post Reddit threads (r/ClaudeAI, r/MCP, r/Python)

### For Me (Akane):
- Monitor MCP directory submissions confirmation
- Track dev.to post engagement (views, reactions, comments)
- Watch for comparison article opportunities
- Prepare HN strategy for when account becomes eligible

---

## 5. Success Metrics

| Metric | Current | Phase A Target | Timeline |
|--------|---------|----------------|----------|
| GitHub stars | ~? | 100 | 30 days |
| Weekly active users | ~? | 10 | 30 days |
| MCP directories listed | 0 | 10+ | 7 days |
| Dev.to post views | 0 | 1,000+ | 7 days |
| PyPI downloads/week | ~? | 100+ | 30 days |