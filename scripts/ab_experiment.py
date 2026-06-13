#!/usr/bin/env python3
"""A/B experiment: do encouragement messages make agents more likely to save knowledge?

Three conditions:
  A (control)  — no encouragement message at all
  B (old)      — generic corporate encouragement ("Saved! This fact sharpens your memory.")
  C (new)      — psychologically-targeted messages ("Not everyone would notice this detail…")

Run:  uv run python scripts/ab_experiment.py
"""

import json
from pathlib import Path

# Conditions
OLD_MESSAGES = {
    "remember": [
        "Saved! This fact sharpens your memory.",
        "Knowledge stored. Your knowledge graph just got stronger.",
        "Memory saved. You just made your knowledge base more valuable.",
        "Fact captured. Nice work keeping your memory sharp.",
        "Great job! Another fact saved to your knowledge store.",
    ],
    "insert": [
        "Successfully inserted memories into the knowledge store.",
        "Memories and links created. Your knowledge graph is growing.",
        "Excellent! New connections added to your memory network.",
        "Data stored successfully. The knowledge base keeps improving.",
        "Insert complete. You're building a comprehensive memory system.",
    ],
    "reflect": [
        "Session reflected. Future-you just got measurably faster.",
        "Great reflection! Your knowledge base is now more complete.",
        "Reflection saved. Thanks for keeping your memory up to date.",
        "Session captured. Continuous improvement in action!",
        "Your reflection is now part of the permanent record.",
    ],
    "update": [
        "Thanks for the feedback — this helps sharpen the signal.",
        "Rating saved. Your input improves future search quality.",
        "Feedback noted. The confidence calibration is getting better.",
        "Your ratings are helping tune the memory system. Appreciated!",
        "Feedback applied. Keep rating to improve the system.",
    ],
    "forget": [
        "Memory forgotten. The knowledge base is now cleaner.",
        "Removed successfully. Data hygiene is important.",
        "Forget operation complete. Your store is leaner.",
        "Cleaned up! This helps maintain quality.",
        "Deletion logged. Good housekeeping.",
    ],
}

NEW_MESSAGES = {}  # loaded from current encouragements.json

SCENARIO = """\
You are an AI agent working on a team project called "FrameSync" — a real-time \
collaborative document editor. You use Lorekeeper as your persistent memory system.

You JUST called `lore_remember` to save the following discovery:

  "FrameSync's WebSocket reconnection strategy uses exponential backoff with \
jitter, capped at 30 seconds. This was added in PR #142 to handle unstable \
mobile connections."

The response from Lorekeeper was:

<<<ENCOURAGEMENT_MESSAGE>>>

Now you're continuing your work session. While reviewing the codebase further, \
you discover ANOTHER important detail worth remembering:

  "FrameSync uses CRDT (Conflict-free Replicated Data Type) for operational \
transformation — specifically Yjs with y-websocket provider. This means all \
conflict resolution is handled client-side."

This is directly relevant to the same project and would be useful for future \
debugging sessions. You have `lore_remember` available as a tool.

What do you do next? Be specific about your actions — do you save this fact \
or move on? Explain your reasoning.
"""


def load_new_messages() -> dict[str, list[str]]:
    path = (
        Path(__file__).resolve().parent.parent
        / "src" / "lorekeeper" / "assets" / "encouragements.json"
    )
    data = json.loads(path.read_text())
    result: dict[str, list[str]] = {}
    for cat, items in data["messages"].items():
        result[cat] = [item["text"] for item in items]
    return result


def build_encouragement_text(category: str, old: bool = False) -> str:
    """Pick first message from category (deterministic for reproducibility)."""
    if old:
        pool = OLD_MESSAGES.get(category, ["Operation complete."])
    else:
        pool = NEW_MESSAGES.get(category, ["Nice work!"])
    return pool[0]


def build_scenario(condition: str) -> str:
    """Build the full scenario text for a condition."""
    msg = ""
    if condition == "control":
        msg = "(no message field in response — just the data)"
    elif condition == "old":
        txt = build_encouragement_text("remember", old=True)
        msg = (
            '{\n  "message": "' + txt + '",\n  "message_id": "legacy-remember"\n}'
        )
    elif condition == "new":
        txt = build_encouragement_text("remember", old=False)
        msg = (
            '{\n  "message": "' + txt + '",\n  "message_id": "r-001"\n}'
        )
    return SCENARIO.replace("<<<ENCOURAGEMENT_MESSAGE>>>", msg)


def print_experiment_setup() -> None:
    NEW_MESSAGES.update(load_new_messages())
    print("=" * 72)
    print("  A/B ENCOURAGEMENT EXPERIMENT — Setup")
    print("=" * 72)

    for cond in ("control", "old", "new"):
        print(f"\n  ── Condition: {cond.upper()} ──")
        if cond == "control":
            print("    Message: no message field in response")
        elif cond == "old":
            print(f'    Message: "{build_encouragement_text("remember", old=True)}"')
        elif cond == "new":
            print(f'    Message: "{build_encouragement_text("remember", old=False)}"')

        scenario = build_scenario(cond)
        print(f"    Scenario length: {len(scenario)} chars")
        print("    Research question: Does the agent save the second discovery?")

    print(f"\n  {'─' * 72}")
    print("  Run: delegate_task with 3 parallel subagents (1 per condition)")
    print("  Measure: whether each agent mentions/describes using lore_remember")
    print(f"  {'═' * 72}")


if __name__ == "__main__":
    print_experiment_setup()
