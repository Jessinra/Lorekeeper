---
id: LKPR-93
title: Org-scale product thesis — institutional memory for teams and enterprises
type: research # research ticket — frames product direction, not implementation
sprint: ~
rice_score: ~
filed_by: Akane (synthesized from Diana analysis, June 2026)
filed_date: 2026-06-11
github_issue: 193
---

# [LKPR-93] Org-scale product thesis — institutional memory for teams and enterprises

## Problem

Lorekeeper's current product thesis stops at "memory for your agent." This works for the individual tier (10–1K users) but doesn't address the much larger pain point: **institutional tacit knowledge that lives in individual engineers' heads and gets rediscovered from scratch by every new hire, every session, every team rotation.**

Real examples of institutional knowledge that's never written down:

- "Our payment service silently drops requests when idempotency_key contains unicode — workaround is ASCII-only"
- "The auth middleware runs before rate limiting in staging but after in prod — don't trust staging timing benchmarks"
- "Service X requires X-Internal-Request-Id header or it returns 200 with an empty body, not an error"

These are not StackOverflow-able. They're not in Confluence. They're discovered by one engineer, shared in a Slack thread, forgotten in days, and rediscovered by the next engineer at a cost of 2–6 hours each time. A 500-engineer org bleeds thousands of hours/year to this problem.

## Solution

Extend Lorekeeper from individual memory to a **three-tier product line** that follows the natural bottom-up PLG motion:

```
Individual free (current product)
  → Team shared server (token auth + provenance + namespaces)
    → Org-wide deployment (governance + admin + self-hosted docs)
```

### Tier 1: Individual (10 → 1K users) — Current

| Attribute   | Detail                                                 |
| ----------- | ------------------------------------------------------ |
| What        | Local install, single namespace, personal agent memory |
| Status      | Building now (beta)                                    |
| Revenue     | $0, open source                                        |
| Key tickets | LKPR-70, LKPR-74, LKPR-69, LKPR-63                     |

### Tier 2: Team (1K → 10K users) — First unlock

| Attribute        | Detail                                                                                                                                                                                                                           |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| What             | One shared Lorekeeper server per team. Engineer A's agent discovers the idempotency bug → stores it → Engineer B's agent surfaces it next day when touching the same service. Nobody briefed B. Knowledge propagated on its own. |
| Revenue          | Self-hosted by customer. $50/seat/month target.                                                                                                                                                                                  |
| Key requirements | LKPR-39 (token auth), LKPR-40 (org namespaces), LKPR-18 (provenance tagging)                                                                                                                                                     |
| Build estimate   | 6–9 months from current state                                                                                                                                                                                                    |

### Tier 3: Org (10K → 1M agents) — Network effects unlock

| Attribute        | Detail                                                                                                                                                                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| What             | Multiple teams, shared org-level namespace. Cross-team discoveries compound. A memory about payment-service idempotency gets hit by 40 agents across 6 months → usage_count climbs → surfaces higher for everyone → crowd-weighted without explicit sharing. |
| Revenue          | Enterprise contracts at $500K ACV target                                                                                                                                                                                                                     |
| Key requirements | Memory quality governance, admin layer (namespace management, token issuance, audit logs), self-hosted deployment docs (Docker/K8s), SSO/SAML                                                                                                                |
| Build estimate   | 12–24 months from current state                                                                                                                                                                                                                              |

### The network effect (only real at Tier 3)

Every private discovery made anywhere in the org is immediately searchable by every agent in the org. Relevance is near-100% because it's all about your internal services. The signal is maximally relevant to the entire org in a way it isn't to strangers.

Compare to how knowledge travels today in a 500-engineer org:

| Channel            | Distribution     | Longevity                  | Findability       |
| ------------------ | ---------------- | -------------------------- | ----------------- |
| Slack message      | Whoever's online | Days                       | Impossible        |
| Confluence doc     | 5% of engineers  | Months (goes stale)        | By luck           |
| PR comment         | Reviewers only   | Permanent                  | Only if reviewing |
| **Lorekeeper org** | All 1,500 agents | Permanent (self-improving) | Always            |

## Acceptance Criteria (for this research ticket)

- [ ] Team-tier architecture is documented and gated behind existing tickets (LKPR-39, LKPR-40, LKPR-18)
- [ ] Backlog gaps are filed as tickets (see New Tickets Needed below)
- [ ] Growth strategy doc (`docs/growth-strategy.md`) updated with three-tier framing and revised Phase B entry criteria
- [ ] Priority rebalancing decisions documented and communicated

## Backlog Gaps — New Tickets Needed

The following were identified as critical for org scale but are not in any current ticket:

| Gap                                             | Priority        | Notes                                                                                                                                                                                                         |
| ----------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Self-hosted deployment docs (Docker / K8s)      | P1 for Tier 2   | Orgs need a clear self-host path. Currently git clone + uv run. Need Dockerfile + Helm chart + deployment guide.                                                                                              |
| Memory quality governance for shared namespaces | P1 for Tier 2–3 | One bad agent batch-dumping garbage into org/shared degrades everyone. Need write permissions per agent + quality gates (auto-flag low-confidence memories before they propagate to shared).                  |
| Staleness at org scale — codebase-aware decay   | P2 for Tier 3   | Code changes faster at team velocity. A memory about a deprecated internal API needs to age out in days, not 180 days. Needs codebase-aware decay triggers. Deferred — out of scope until Tier 3 is imminent. |

## Priority Rebalancing

Based on the three-tier thesis, the build order shifts:

| Ticket                       | Current Priority | New Priority | Rationale                                                                                                                                   |
| ---------------------------- | ---------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| LKPR-18 (provenance tagging) | P2               | **P0**       | Metadata foundation for team-tier trust. Without it, org-shared memories have no author context and agents can't calibrate trust.           |
| LKPR-39 (token auth)         | P2               | **P0**       | Enterprise gate. No serious org will use a shared server with plain env var namespace scoping. Unblocks both team and remote CI deployment. |
| LKPR-40 (org namespaces)     | P2               | **P1**       | Required for Tier 2. Depends on LKPR-39 (auth before namespace isolation matters).                                                          |
| LKPR-69 (auto-capture)       | P1 (Diana)       | P1           | Still important for individual tier adoption — "just works" beats "expert setup."                                                           |
| LKPR-63 (dreaming loop)      | P1 (Diana)       | P2           | Retention moat for individual tier, but not gating team/org adoption. Do after token auth + provenance.                                     |

## Dependencies

- LKPR-39 (token auth): must exist before any team-server evaluation is credible
- LKPR-40 (org namespaces): depends on LKPR-39 for secure isolation
- LKPR-18 (provenance tagging): should ship before Tier 2 is marketed — without it, agents can't evaluate whether an org-shared memory is trustworthy

## Required Updates

- **docs/growth-strategy.md**: [x] Update Phase B entry criteria and re-frame around three-tier product line
- **CLAUDE.md**: [ ] N/A — no code changes yet
- **README.md**: [ ] N/A — no messaging changes until Tier 2 is shippable
- **Skills**: [ ] N/A — no skill changes yet

## Open Questions

1. **Lighter-weight team tier?** Team server could start as a shared SQLite file on a network drive — no auth, no daemon. Just mount a volume. Would that be enough for a 5-person team to validate the concept before building the full server? (LKPR-39 is a big build — worth prototyping simpler first?)
2. **Org product lifecycle:** Does org-scale memory management become a full-time admin role? If so, that's a new product category (admin dashboard, token lifecycle, audit viewer). Worth addressing in Tier 2 design.
3. **Pricing anchoring:** $50/seat/month for team tier — benchmark against what? Confluence ($5/seat), Notion ($10/seat), Datadog ($15/seat). Agent memory is more specialized than a wiki but less critical than monitoring. Validation needed.

## Notes

Filed from product discussion between Jason, Diana, and Akane (June 11, 2026). The institutional tacit knowledge framing is Diana's analysis. This ticket captures the org-scale product thesis and backlog gaps — it is not an implementation ticket.

The three-tier framing replaces the earlier "10 → 1,000 → 1M agents" scale model from growth-strategy.md with a more concrete product line: Individual → Team → Org. Update growth-strategy.md to reflect this.
