"""Background sweep that generates link suggestions from all memory pairs.

This module owns the **batch-scan logic** — iterating active memories, running
the ``LinkCandidateGenerator``, and persisting candidates to the
``LinkSuggestionStore``. It is intentionally **not** part of ``MemoryService``
(orchestrator) because it is a background maintenance task, not a user-facing
operation.

Dependencies are explicit at construction time — no coupling to
``MemoryService`` internals.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

import structlog

from lorekeeper.config import Settings
from lorekeeper.services.link_candidate import LinkCandidateGenerator
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.suggestion_store import LinkSuggestionStore

log = structlog.get_logger()


class SweepService:
    """Iterates active memories, generates link candidates, writes suggestions.

    Designed as a drop-in ``run()`` for ``PeriodicJob`` (zero-arg callable).
    """

    def __init__(
        self,
        memory_store: MemoryStore,
        link_store: LinkStore,
        suggestion_store: LinkSuggestionStore,
        link_candidate_generator: LinkCandidateGenerator,
        settings: Settings,
        metrics_store: MetricsStore,
        conn: sqlite3.Connection,
    ) -> None:
        self._memory_store = memory_store
        self._link_store = link_store
        self._suggestion_store = suggestion_store
        self._generator = link_candidate_generator
        self._settings = settings
        self._metrics_store = metrics_store
        self._conn = conn

    def _increment_metric(self, tool_name: str) -> None:
        try:
            self._metrics_store.increment_metric(tool_name)
            self._conn.commit()
        except sqlite3.Error:
            log.warning("sweep_metric_increment_failed", tool_name=tool_name)

    def run(self) -> dict[str, Any]:
        """Execute one sweep: scan → generate → store → prune.

        Split into two phases to minimise how long the SQLite writer lock is
        held:

        * **Phase 1 (compute, no write txn):** scan memories and run the
          candidate generator (embeddings + spaCy NER + BM25 — hundreds of ms
          each). These are read-only/CPU operations; in WAL mode SELECTs never
          take the writer lock. We collect the suggestions to write into an
          in-memory list and tally stats, issuing no INSERT/UPDATE here.
        * **Phase 2 (write burst):** apply all collected upserts + prune in a
          single short transaction, then commit. The writer lock is acquired on
          the first upsert and released on commit — held only for the fast
          INSERTs, never across the slow generate() calls.

        Returns stats dict with keys: memories_scanned, candidates_generated,
        high_confidence, standard, skipped_rejected, skipped_linked, expired_pruned.
        """
        self._increment_metric("lore_sweep")

        # ── Phase 1: read + compute (no writer lock held) ───────────────────
        # Read all active memories
        all_rows = self._memory_store.all_memory_rows(
            include_deleted=False, namespaces=None
        )
        all_mems = {r["id"]: r for r in all_rows}

        # Pre-load rejection, pending, and link sets
        rejected = self._suggestion_store.rejected_pairs()
        pending = self._suggestion_store.pending_pairs()
        all_links = self._link_store.all_links()
        linked_pairs: set[tuple[str, str]] = set()
        for lnk in all_links:
            src, tgt = lnk.source_memory_id, lnk.target_memory_id
            linked_pairs.add((src, tgt))
            linked_pairs.add((tgt, src))

        stats: dict[str, Any] = {
            "memories_scanned": 0,
            "candidates_generated": 0,
            "high_confidence": 0,
            "standard": 0,
            "skipped_rejected": 0,
            "skipped_pending": 0,
            "skipped_linked": 0,
            "expired_pruned": 0,
        }

        # Collected upsert payloads — written in the Phase 2 burst.
        pending_upserts: list[dict[str, Any]] = []

        for mem_id in all_mems:
            stats["memories_scanned"] += 1
            try:
                candidates = self._generator.generate(mem_id)
            except Exception:
                log.warning("sweep_generate_failed", lore_id=mem_id, exc_info=True)
                continue

            for c in candidates:
                if c.weighted_score < self._settings.link_score_threshold:
                    continue

                pair = (c.source_lore_id, c.target_lore_id)
                # Normalize to canonical order for DB pair matching
                canonical = self._suggestion_store._canonical(
                    c.source_lore_id, c.target_lore_id
                )
                if pair in linked_pairs:
                    stats["skipped_linked"] += 1
                    continue
                if canonical in rejected:
                    stats["skipped_rejected"] += 1
                    continue
                if canonical in pending:
                    stats["skipped_pending"] += 1
                    continue

                confidence = (
                    "high"
                    if c.weighted_score >= self._settings.suggest_high_confidence_score
                    else "standard"
                )

                src_row = all_mems.get(c.source_lore_id)
                tgt_row = all_mems.get(c.target_lore_id)
                pending_upserts.append(
                    {
                        "source_memory_id": c.source_lore_id,
                        "target_memory_id": c.target_lore_id,
                        "source_title": src_row["title"] if src_row else "",
                        "target_title": tgt_row["title"] if tgt_row else "",
                        "weighted_score": c.weighted_score,
                        "cosine_score": c.cosine_score,
                        "bm25_score": c.bm25_score,
                        "entity_score": c.entity_score,
                        "temporal_score": c.temporal_score,
                        "suggested_type": None,
                        "confidence": confidence,
                        "status": "pending",
                    }
                )
                stats["candidates_generated"] += 1
                if confidence == "high":
                    stats["high_confidence"] += 1
                else:
                    stats["standard"] += 1

        # ── Phase 2: write burst (writer lock held only for this block) ─────
        # The implicit BEGIN fires on the first upsert; commit() releases the
        # lock. No slow work happens between them, so the lock is held for
        # milliseconds, not the whole scan.
        for payload in pending_upserts:
            try:
                self._suggestion_store.upsert_suggestion(**payload)
            except Exception:
                log.warning(
                    "sweep_upsert_failed",
                    source=payload["source_memory_id"],
                    target=payload["target_memory_id"],
                    exc_info=True,
                )

        # Prune expired suggestions
        try:
            stats["expired_pruned"] = self._suggestion_store.prune_expired(
                self._settings.suggest_ttl_days
            )
        except Exception:
            log.warning("sweep_prune_failed", exc_info=True)

        self._conn.commit()
        self._conn.execute(
            "INSERT OR REPLACE INTO config_overrides (key, value, updated_at) VALUES (?, ?, ?)",
            (
                "sweep_last_run_at",
                json.dumps(datetime.now(UTC).isoformat()),
                datetime.now(UTC).isoformat(),
            ),
        )
        self._conn.commit()
        log.info("sweep_completed", stats=stats)
        return stats
