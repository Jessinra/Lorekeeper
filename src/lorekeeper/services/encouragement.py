"""Encouraging messages for MCP write responses — loaded from static JSON.

Messages are stored in ``assets/encouragements.json`` as a static data file.
Each write response can include a ``message`` / ``message_id`` field at the tool response
root level. This is a generic injection point — currently carries encouragement, but can
carry prompts, instructions, or any agent-directed signal in future.

Rate: controlled by ``LORE_ENC_RATE`` (0.0-1.0). At 1.0, every write response includes a message.
At 0.3, ~30% of calls include it — useful for avoiding desensitisation.

A/B tracking: every delivered message is logged to ``{LORE_DATA_DIR}/ab_messages.jsonl``
so effectiveness can be measured by correlating message IDs with subsequent tool usage.
"""

from __future__ import annotations

import json
import logging
import os
import random
import secrets
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_INJECTION_RATE: float = 1.0  # set by set_rate() at startup

# Cache: category -> list of {"id": str, "text": str}
_MESSAGES: dict[str, list[dict[str, str]]] | None = None


def set_rate(rate: float) -> None:
    """Set the injection rate (0.0-1.0) for guidance responses."""
    global _INJECTION_RATE
    _INJECTION_RATE = max(0.0, min(1.0, rate))


def _data_dir() -> Path:
    """Resolve LORE_DATA_DIR for A/B log writes."""
    raw = os.environ.get("LORE_DATA_DIR") or str(Path.home() / ".lorekeeper")
    return Path(raw)


def _load() -> dict[str, list[dict[str, str]]]:
    """Load encouragements from the static JSON asset file."""
    json_path = Path(__file__).resolve().parent.parent / "assets" / "encouragements.json"
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        raw = data["messages"]
        # Normalise: JSON might have string lists (old format) or dict lists
        result: dict[str, list[dict[str, str]]] = {}
        for cat, items in raw.items():
            normalised: list[dict[str, str]] = []
            for item in items:
                if isinstance(item, str):
                    normalised.append({"id": f"legacy-{cat}", "text": item})
                else:
                    normalised.append(item)
            result[cat] = normalised
        return result
    except Exception as exc:
        log.warning("encouragement_load_failed", exc_info=exc)
        return {}


def _cat(category: str) -> list[dict[str, str]]:
    global _MESSAGES
    if _MESSAGES is None:
        _MESSAGES = _load()
    return _MESSAGES.get(category, [])


def _pick(category: str) -> dict[str, str]:
    """Return a random message dict from the category."""
    pool = _cat(category)
    if not pool:
        return {"id": "fallback", "text": "You're building knowledge that lasts. Keep going."}
    return secrets.choice(pool)


def _log_delivery(message_id: str, category: str, session_context: str = "") -> None:
    """Log a message delivery for A/B analysis."""
    try:
        path = _data_dir() / "ab_messages.jsonl"
        entry = {
            "ts": time.time(),
            "message_id": message_id,
            "category": category,
            "session_context": session_context,
        }
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # never break the MCP tool over analytics


def get_guidance(category: str) -> dict[str, Any]:
    """Return a dict with 'message' (text) and 'message_id' for the category.

    Respects the configured injection rate — may return an empty dict.
    Also logs the delivery for A/B analysis. Prefer the categorical helpers below.
    """
    if _INJECTION_RATE < 1.0 and random.random() > _INJECTION_RATE:
        return {}
    msg = _pick(category)
    _log_delivery(msg["id"], category)
    return {"message": msg["text"], "message_id": msg["id"]}


def for_remember() -> dict[str, Any]:
    return get_guidance("remember")


def for_insert(memory_count: int = 0, link_count: int = 0) -> dict[str, Any]:
    """Return guidance for insert.

    Links-only inserts get link-themed guidance; otherwise insert-themed.
    """
    cat = "links" if memory_count == 0 and link_count > 0 else "insert"
    return get_guidance(cat)


def for_reflect(already_processed: bool = False) -> dict[str, Any]:
    cat = "reflect_already" if already_processed else "reflect"
    return get_guidance(cat)


def for_update() -> dict[str, Any]:
    return get_guidance("update")


def for_forget(count: int = 0) -> dict[str, Any]:
    return get_guidance("forget")
