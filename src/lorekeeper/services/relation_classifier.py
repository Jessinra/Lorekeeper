"""Stage 2: LLM-based relation type classifier. No side-effects — candidates only."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import structlog

if TYPE_CHECKING:
    from lorekeeper.config import Settings
    from lorekeeper.services.link_candidate import LinkCandidate

log = structlog.get_logger()

VALID_RELATION_TYPES = {
    "related_to",
    "used_in",
    "used_for",
    "used_by",
    "used_as",
    "contradicts",
    "supersedes",
    "depends_on",
}

CLASSIFY_SYSTEM_PROMPT = """You are a memory link classifier.
Given two memory texts, determine the best relation type between them.

Relation types:
- related_to: general thematic connection
- used_in: source concept is used in the target context
- used_for: source is used for the purpose described in target
- used_by: source is used by the agent/entity in target
- used_as: source serves as a role described in target
- contradicts: the two memories make conflicting claims
- supersedes: source memory is a newer/updated version that replaces target
- depends_on: source memory requires or builds upon target
- none: no meaningful link — discard this candidate

Respond ONLY with a JSON object: {"relation": "<type>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}"""


class LLMRelationClassifier:
    """Optional Stage 2 classifier. No-op when LORE_LINK_CLASSIFIER_BASE_URL is empty."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_key = settings.link_classifier_api_key

    def _is_available(self) -> bool:
        return bool(self._settings.link_classifier_base_url)

    def classify_batch(
        self,
        source_text: str,
        candidates: list[LinkCandidate],
        candidate_texts: dict[str, str],
    ) -> None:
        """Classify each candidate in-place. Mutates proposed_relation,
        classifier_confidence, classifier_reasoning.

        Candidates classified as "none" get weighted_score = -1.0 for discard.
        """
        if not self._is_available():
            log.info(
                "relation_classifier_skipped",
                reason="LORE_LINK_CLASSIFIER_BASE_URL not set",
            )
            return

        for cand in candidates:
            target_text = candidate_texts.get(cand.target_lore_id, "")
            if not target_text:
                continue
            result = self._classify_one(source_text, target_text)
            if result:
                relation, confidence, reasoning = result
                if relation == "none":
                    cand.weighted_score = -1.0  # Mark for discard — caller filters
                    cand.proposed_relation = "none"
                else:
                    cand.proposed_relation = relation
                cand.classifier_confidence = confidence
                cand.classifier_reasoning = reasoning

    def _classify_one(self, source: str, target: str) -> tuple[str, float, str] | None:
        url = self._settings.link_classifier_base_url.rstrip("/") + "/chat/completions"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._settings.link_classifier_model,
            "messages": [
                {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Memory A:\n{source}\n\nMemory B:\n{target}",
                },
            ],
            "temperature": 0.0,
            "max_tokens": 150,
        }
        try:
            resp = httpx.post(
                url,
                json=payload,
                timeout=self._settings.link_classifier_timeout,
                headers=headers,
            )
            resp.raise_for_status()
            parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
            relation = parsed.get("relation", "related_to")
            if relation not in VALID_RELATION_TYPES and relation != "none":
                relation = "related_to"
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")
            return relation, confidence, reasoning
        except Exception:
            log.warning("relation_classifier_call_failed", exc_info=True)
            return None
