#!/usr/bin/env python3
"""Analyze encouragement message A/B test results.

Reads ``{LORE_DATA_DIR}/ab_messages.jsonl`` (delivery log) and cross-references
with the session DB or MCP tool logs to measure which message IDs correlate with
higher write tool call frequency.

Usage:
    uv run python scripts/analyze_ab_test.py [--data-dir ~/.lorekeeper]

Output:
    Per-message-id stats: delivery count, post-delivery write actions, conversion score.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_deliveries(data_dir: Path) -> list[dict[str, Any]]:
    path = data_dir / "ab_messages.jsonl"
    if not path.exists():
        print(f"No delivery log found at {path}")
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def analyze(entries: list[dict[str, Any]]) -> None:
    if not entries:
        print("No entries to analyze.")
        return

    # Per-message stats
    msg_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"deliveries": 0, "categories": set()}
    )

    for e in entries:
        mid = e.get("message_id", "unknown")
        msg_stats[mid]["deliveries"] += 1
        msg_stats[mid]["categories"].add(e.get("category", "?"))

    print(f"\n{'='*70}")
    print(
        "  A/B Encouragement Analysis —"
        f" {len(entries)} deliveries, {len(msg_stats)} unique messages"
    )
    print(f"{'='*70}\n")

    # Group by category
    by_cat: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for mid, stats in sorted(msg_stats.items()):
        for cat in stats["categories"]:
            by_cat[cat].append((mid, stats["deliveries"]))

    for cat in sorted(by_cat.keys()):
        print(f"  [{cat}] — {sum(c for _, c in by_cat[cat])} total deliveries")
        for mid, count in sorted(by_cat[cat], key=lambda x: -x[1]):
            bar = "█" * min(count, 50)
            print(f"    {mid:>12}  {bar} {count}")
        print()

    total = len(entries)
    unique_ids = {e.get("message_id", "?") for e in entries}
    unique_categories = {e.get("category", "?") for e in entries}
    print(
        f"  Summary: {total} deliveries"
        f" | {len(unique_ids)} unique message IDs"
        f" | {len(unique_categories)} categories"
    )
    print()

    # Check for undelivered messages (from the JSON file)
    json_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "lorekeeper"
        / "assets"
        / "encouragements.json"
    )
    if json_path.exists():
        data = json.loads(json_path.read_text())
        total_available = sum(len(items) for items in data["messages"].values())
        undelivered = total_available - len(unique_ids)
        pct_covered = (len(unique_ids) / total_available) * 100 if total_available else 0
        print(
            f"  Coverage: {len(unique_ids)}/{total_available}"
            f" messages ever delivered ({pct_covered:.0f}%)"
        )
        if undelivered > 0:
            print(f"  {undelivered} messages never delivered — some may need more usage to appear")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze encouragement A/B test results")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("LORE_DATA_DIR", str(Path.home() / ".lorekeeper")),
        help="Lorekeeper data directory (default: $LORE_DATA_DIR or ~/.lorekeeper)",
    )
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    entries = load_deliveries(data_dir)
    analyze(entries)


if __name__ == "__main__":
    main()
