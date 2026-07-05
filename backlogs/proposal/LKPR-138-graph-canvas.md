---
id: LKPR-138
title: Graph Canvas (Links Graph View)
type: feature
sprint: ~
rice_score: ~
filed_by: Hermes
filed_date: 2026-07-05
github_issue: 303
---

# LKPR-138: Graph Canvas (Links Graph View)

**Status:** 🔴 Blocked | **Depends on:** LKPR-132 | **Next:** _(blocked — no scheduled next)_

## Problem

The Links page needs a graph visualization of memory nodes connected by relation-colored edges. The v1 dashboard has no graph view at all. However, the graph layout algorithm and rendering strategy for production-scale data is undesigned (spec §6.4).

## Solution

Build an SVG graph canvas with memory nodes (radius ∝ score), relation-colored edges, node selection with dimmed unconnected nodes, and a 300px side panel showing direct connections. **Blocked** — see design gaps below.

## Acceptance Criteria

- [ ] Graph view toggle in SegmentedControl (alongside Links table view) — per spec §3.3
- [ ] SVG canvas: memory nodes (radius scales with score) connected by relation-colored edges (colors per spec §2.5) — per spec §3.3
- [ ] Click a node → dims everything except it and its direct connections — per spec §3.3
- [ ] Node selected → 300px side panel appears: memory's title, ns/score chips, list of direct connections (directional arrow + relation + other memory's title)
- [ ] Click empty canvas → clears selection — per spec §3.3
- [ ] Side panel: each connection is clickable — opens RelationshipDrawer
- [ ] Empty state when no graph data: centered icon + "No links to display" — per spec §2.10
- [ ] TODO: Interactive placement — allow drag if using force layout
- [ ] TODO: Pan/zoom support

## Components to Build

- `src/dashboard_v2/src/components/graph/GraphView.svelte` — SVG canvas, node rendering, edge drawing, click handling
- `src/dashboard_v2/src/components/graph/NodeDetail.svelte` — side panel for selected node

## API Dependencies

- `GET /api/links` — exists (returns all links with source/target titles)

## Required Updates

- None — this is a new component, no existing code to update. However, the graph layout algorithm (§6.4) requires a design decision before implementation can proceed.

## Design Gaps (BLOCKERS)

**Gap 6.4 — Graph scalability is undesigned. Resolve before building:**

1. **Layout algorithm**: The mockup uses seeded pseudo-random jitter-grid (mulberry32) for ~18 nodes. Real system has thousands. Choose:
   - Force-directed (d3-force or similar) — interactive, auto-layout, but expensive at scale
   - Hierarchical/clustered — group by namespace, expand on click
   - "Top N by centrality" — limit visible nodes to most-connected, with "load more" option
2. **Rendering strategy**: SVG is fine for hundreds of nodes. For thousands, consider Canvas or WebGL.

3. **Pan/Zoom/Drag**: Required for usability but not included in mockup. D3-zoom for pan/zoom, d3-drag for node repositioning.

4. **Initial view**: Which nodes load by default? All? Filtered by namespace/relation? Top-N?

## Recommended Approach (When Unblocked)

- Use d3-force for layout, d3-zoom for pan/zoom, d3-drag for node repositioning
- Render as SVG (good for tooltips and interaction)
- Filter by relation type via existing FilterChip component
- Show max 200 nodes by default (most connected), "Load more" button at bottom

## Testing

- Nodes render with correct radius = f(score)
- Edges render with correct relation colors
- Click node → highlights connections, dims others
- Click empty canvas → clears selection
- Side panel populates with correct data

## Design Ref

- Spec §3.3 (Links / Graph)
- Spec §2.5 (RelationPill colors)
- Mockups: `design/visuals/page-links.png`, `design/visuals/component-graph-view.png`
