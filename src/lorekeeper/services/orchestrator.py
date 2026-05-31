from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from lorekeeper.config import Settings
from lorekeeper.models import RELATION_TYPES, Memory, MemoryLink
from lorekeeper.services.config_store import ConfigStore
from lorekeeper.services.dedup import is_duplicate
from lorekeeper.services.feedback import (
    apply_score_delta,
    compute_running_confidence,
    should_soft_delete,
)
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_engine import MemoryEngine
from lorekeeper.services.memory_store import MemoryStore
from lorekeeper.services.metrics_store import MetricsStore
from lorekeeper.services.reflection_store import ReflectionStore
from lorekeeper.services.search import SearchResult, rank_results

log = structlog.get_logger()


class MemoryService:
    """Memory orchestration — search, insert, remember, update, reflect."""

    @staticmethod
    def _extract_title(thought: str) -> str:
        """Smart title: first complete word at or after ~80 chars,
    ending at sentence boundary if possible.
    """
        max_len = 80
        max_extended = 120
        trimmed = thought.strip()
        if len(trimmed) <= max_len:
            return trimmed

        chunk = trimmed[:max_len]
        # Try sentence boundary first
        for end_char in ".!?":
            idx = chunk.rfind(end_char)
            if idx > max_len // 2:
                return chunk[:idx + 1].strip()
        # Try last space within first max_len chars
        idx = chunk.rfind(" ")
        if idx > 0:
            return chunk[:idx].strip()
        # No space found in first max_len — look forward for next word boundary
        rest = trimmed[max_len:max_extended]
        next_space = rest.find(" ")
        if next_space > 0:
            return trimmed[:max_len + next_space].strip()
        # No word boundary found anywhere — return as much as we can
        return trimmed[:max_extended].strip()

    def __init__(
        self,
        engine: MemoryEngine,
        memories: MemoryStore,
        links: LinkStore,
        reflections: ReflectionStore,
        metrics: MetricsStore,
        config: ConfigStore,
        keyword_index: KeywordIndex,
        settings: Settings,
    ) -> None:
        self._engine = engine
        self.memories = memories
        self.links = links
        self.reflections = reflections
        self.metrics = metrics
        self.config = config
        self._kw = keyword_index
        self.settings = settings
        self._namespace: str = settings.namespace
        # Namespace filter for all read/write operations: None = no filter (shared sees all).
        self._ns_filter: list[str] | None = (
            None if self._namespace == "shared" else [self._namespace, "shared"]
        )

    def _all_memories(self, include_deleted: bool = False) -> dict[str, Memory]:
        # None → no filter → reads all rows (backward-compat for the default "shared" agent).
        # Non-shared agents scope reads to their own namespace + the shared pool.
        namespaces = self._ns_filter
        rows = self.memories.all_memory_rows(include_deleted=include_deleted, namespaces=namespaces)
        return {r["id"]: _row_to_memory(r) for r in rows}

    def _rebuild_kw(self) -> None:
        mems = list(self._all_memories(include_deleted=True).values())
        self._kw.rebuild(mems)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _increment_metric(self, tool_name: str) -> None:
        try:
            self.metrics.increment_metric(tool_name)
        except sqlite3.Error:
            # Metrics must never break a real call, but the failure should be
            # observable. Log at WARNING (not ERROR) — metric write is degraded,
            # not a request failure.
            log.warning("metric_increment_failed", tool_name=tool_name, exc_info=True)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int | None = None,
        min_score: float = 0.1,
        include_links: bool = True,
        include_deleted: bool = False,
        refine_from: list[str] | None = None,
    ) -> list[SearchResult]:
        self._increment_metric("lore_search")
        sem_hits = self._engine.search(query, limit=200)
        kw_hits = self._kw.search_normalized(query)
        memories = self._all_memories(include_deleted=include_deleted)

        if limit is None:
            limit = self.settings.search_limit

        links_by_id: dict[str, list[MemoryLink]] = {}
        if include_links:
            max_links = self.settings.max_links_per_memory
            for mid in memories:
                all_links = self.links.links_for_memory(mid)
                links_by_id[mid] = all_links[:max_links]

        results = rank_results(
            sem_hits, kw_hits, memories, links_by_id,
            self.settings, limit, min_score, include_deleted,
            refine_from=refine_from,
        )

        # Increment usage on returned memories
        for r in results:
            self.memories.update_memory_fields(r.memory.id, usage_count=r.memory.usage_count + 1)

        return results

    # ── Insert ────────────────────────────────────────────────────────────────

    def insert(
        self,
        memories: list[dict],
        links: list[dict],
        force: bool = False,
    ) -> dict:
        self._increment_metric("lore_insert")
        inserted_memories: list[dict] = []
        inserted_links: list[dict] = []
        duplicates: list[dict] = []
        errors: list[dict] = []

        for m in memories:
            try:
                # Shallow copy to avoid mutating caller-provided dicts
                m = dict(m)
                # Extract and validate inline links format before insert
                inline_links = m.pop("links", None)
                if inline_links is not None:
                    if not isinstance(inline_links, list):
                        raise ValueError(
                            f"memory '{m.get('title', '')}' has invalid 'links': "
                            f"expected a list, got {type(inline_links).__name__}"
                        )
                    for i, ld in enumerate(inline_links):
                        if not isinstance(ld, dict):
                            raise ValueError(
                                f"memory '{m.get('title', '')}' inline link at index {i}: "
                                f"expected a dict, got {type(ld).__name__}"
                            )
                        if not ld.get("target_memory_id"):
                            raise ValueError(
                                f"memory '{m.get('title', '')}' inline link at index {i}: "
                                f"missing required field 'target_memory_id'"
                            )
                        if not ld.get("relation_type"):
                            raise ValueError(
                                f"memory '{m.get('title', '')}' inline link at index {i}: "
                                f"missing required field 'relation_type'"
                            )

                result = self._insert_one_memory(m, force)
                if result.get("duplicate"):
                    duplicates.append(result["duplicate"])
                else:
                    lore_id = result["inserted"]["id"]
                    inserted_memories.append(result["inserted"])

                    # Auto-link this new memory to similar existing ones
                    try:
                        link_text = (
                            f"{m.get('title', '')} {m.get('description', '')} "
                            f"{m.get('content', '')}"
                        )
                        self._auto_link(link_text.strip(), lore_id, source="insert")
                    except Exception:
                        log.warning("auto_link_failed", lore_id=lore_id, exc_info=True)

                    # Normalize inline links to standard format and delegate to _insert_one_link
                    if inline_links:
                        for link_def in inline_links:
                            try:
                                # Validate target exists and is within scoped namespaces
                                target_row = self.memories.get_memory_row(
                                    link_def["target_memory_id"],
                                    namespaces=self._ns_filter,
                                )
                                if target_row is None:
                                    raise ValueError(
                                        f"link target memory_id"
                                        f" '{link_def['target_memory_id']}' not found"
                                    )
                                normalized = {
                                    "source_memory_id": lore_id,
                                    "target_memory_id": link_def["target_memory_id"],
                                    "relation_type": link_def["relation_type"],
                                    "reason": link_def.get("reason") or "",
                                }
                                inserted = self._insert_one_link(normalized)
                                inserted_links.append(inserted)
                            except Exception as e:
                                errors.append({
                                    "input": f"memory '{m.get('title', '')}' → link {link_def}",
                                    "error": str(e),
                                })
            except Exception as e:
                errors.append({"input": m.get("title", ""), "error": str(e)})

        # Rebuild KW index after all memory inserts
        if inserted_memories:
            self._rebuild_kw()

        for lnk in links:
            try:
                inserted = self._insert_one_link(lnk)
                inserted_links.append(inserted)
            except Exception as e:
                errors.append({"input": str(lnk), "error": str(e)})

        return {
            "inserted_memories": inserted_memories,
            "inserted_links": inserted_links,
            "duplicates": duplicates,
            "errors": errors,
        }

    # ── Remember (fast one-shot insert) ────────────────────────────────────────

    def remember(self, thought: str) -> dict:
        """Fast one-shot insert with auto-extracted fields and auto-linking."""
        self._increment_metric("lore_remember")
        title = self._extract_title(thought)
        description = title
        score = self.settings.new_memory_default_score

        result = self._insert_one_memory({
            "title": title,
            "description": description,
            "content": thought,
            "score": score,
        }, force=False)

        if "duplicate" in result:
            dup = result["duplicate"]
            return {
                "id": dup["existing_memory"]["id"],
                "title": title,
                "linked_to": None,
            }

        lore_id = result["inserted"]["id"]

        # Rebuild KW index after the insert
        self._rebuild_kw()

        linked_to = self._auto_link(thought, lore_id)
        return {"id": lore_id, "title": title, "linked_to": linked_to}

    def _auto_link(self, text: str, lore_id: str, source: str = "remember") -> dict | None:
        """Auto-link a new memory to its nearest neighbor above threshold.

        Uses settings for k (candidate count) and threshold. Checks link_store
        before inserting to prevent duplicate links. Tracks metrics for observability.

        Creates at most one link per call (first candidate above threshold that is
        not a duplicate). Intentional — bulk inserts could produce noisy graph edges
        if multiple links were created per call.

        ``auto_link_candidates`` metric is incremented once per invocation (tracks
        auto-link calls, not total candidates evaluated — ``_increment_metric`` has
        no count param).

        Never raises — all failures are caught and logged so callers (remember,
        insert) are never broken by a bad auto-link.

        Args:
            text: Content to search against (thought or concatenated memory fields).
            lore_id: The new memory's ID to link from.
            source: Origin label for the reason string ("remember" or "insert").
        """
        if not self.settings.auto_link_enabled:
            return None

        if not text or not text.strip():
            return None

        # Clamp k to [1, 200] — non-positive values crash some vector backends
        k = max(1, min(self.settings.auto_link_k, 200))
        threshold = self.settings.auto_link_threshold

        try:
            sem_hits = self._engine.search(text, limit=k)
        except Exception:
            log.warning("auto_link: engine.search failed", exc_info=True)
            return None

        self._increment_metric("auto_link_candidates")

        # Pre-compute the set of IDs already linked to lore_id (both directions)
        try:
            existing_links = self.links.links_for_memory(lore_id)
            linked_ids: set[str] = set()
            for link in existing_links:
                linked_ids.add(link.target_memory_id)
                if link.source_memory_id != lore_id:
                    linked_ids.add(link.source_memory_id)
        except Exception:
            log.warning("auto_link: links_for_memory failed", exc_info=True)
            return None

        for hit in sem_hits:
            if hit["lore_id"] == lore_id or hit["score"] < threshold:
                continue

            if hit["lore_id"] in linked_ids:
                continue

            # Verify target memory exists, is not soft-deleted, and is within scoped namespaces
            try:
                target_row = self.memories.get_memory_row(
                    hit["lore_id"], namespaces=self._ns_filter
                )
                if target_row is None or target_row["soft_deleted"]:
                    continue
            except Exception:
                log.warning(
                    "auto_link: get_memory_row failed for %s (target %s)",
                    lore_id,
                    hit["lore_id"],
                    exc_info=True,
                )
                continue

            raw_score = round(hit["score"], 4)
            try:
                self.links.insert_link(
                    source_memory_id=lore_id,
                    target_memory_id=hit["lore_id"],
                    relation_type="related_to",
                    reason=f"auto-linked from lore_{source}: {raw_score:.2f}",
                )
            except Exception:
                log.warning("auto_link: insert_link failed", exc_info=True)
                continue

            self._increment_metric("auto_linked")
            return {"id": hit["lore_id"], "score": raw_score}
        return None

    def _insert_one_memory(self, m: dict, force: bool) -> dict:
        if "title" not in m:
            raise ValueError("memory dict missing required field: 'title'")
        title = m["title"]
        description = m.get("description", "")
        content = m.get("content", "")
        score = float(m.get("score", self.settings.new_memory_default_score))
        text = f"{title} {description} {content}"

        if not force:
            # Shared agent checks across all namespaces (no filter) to preserve
            # pre-existing global dedup behavior. Non-shared agents scope checks
            # to their own namespace + the shared pool.
            ns_filter = self._ns_filter
            # Exact title match is a definitive duplicate — skip semantic search
            existing_by_title = self.memories.get_memory_row_by_title(title, namespaces=ns_filter)
            if existing_by_title:
                return {"duplicate": {
                    "input_title": title,
                    "existing_memory": dict(existing_by_title),
                    "similarity": 1.0,
                }}

            sem_hits = self._engine.search(text, limit=5)
            kw_hits = self._kw.search_normalized(text)
            for hit in sem_hits:
                lid = hit["lore_id"]
                sem = hit["score"]
                kw = kw_hits.get(lid, 0.0)
                if is_duplicate(sem, kw, self.settings):
                    existing_row = self.memories.get_memory_row(lid, namespaces=ns_filter)
                    if existing_row:
                        return {"duplicate": {
                            "input_title": title,
                            "existing_memory": dict(existing_row),
                            "similarity": round(0.6 * sem + 0.4 * kw, 4),
                        }}

        lore_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._engine.add(text, lore_id)
        self.memories.upsert_memory_row(
            id=lore_id, title=title, description=description, content=content,
            created_at=now, updated_at=now, score=score, namespace=self._namespace,
        )
        log.info("memory_inserted", lore_id=lore_id, title=title)
        return {"inserted": {"id": lore_id, "title": title}}

    def _insert_one_link(self, lnk: dict) -> dict:
        self._validate_relation_type(lnk.get("relation_type", ""))
        link = self.links.insert_link(
            source_memory_id=lnk["source_memory_id"],
            target_memory_id=lnk["target_memory_id"],
            relation_type=lnk["relation_type"],
            reason=lnk["reason"],
            score=float(lnk.get("score", 1.0)),
        )
        return {
            "id": link.id,
            "source_memory_id": link.source_memory_id,
            "target_memory_id": link.target_memory_id,
            "relation_type": link.relation_type,
        }

    @staticmethod
    def _validate_relation_type(relation: str) -> None:
        """Validate that relation is one of the known relation types.

        Raises ValueError with a clear message if invalid.
        Used by _insert_one_link for both inline and top-level links.
        """
        if relation not in RELATION_TYPES:
            raise ValueError(
                f"invalid relation_type '{relation}': "
                f"must be one of {sorted(RELATION_TYPES)}"
            )

    # ── Import (backup restore) ───────────────────────────────────────────────

    def import_dump(
        self,
        memories: list[dict],
        links: list[dict],
        dry_run: bool = False,
    ) -> dict:
        memories_inserted = 0
        memories_skipped = 0
        links_inserted = 0
        links_skipped = 0
        links_error = 0
        errors: list[str] = []
        preview_memories: list[dict] = []
        preview_links: list[dict] = []

        # Track IDs that exist or were just inserted (for FK validation)
        valid_ids: set[str] = {r["id"] for r in self.memories.all_memory_rows(include_deleted=True)}

        for m in memories:
            mid = m.get("id", "")
            if not mid:
                errors.append(f"memory missing id: {m.get('title', '?')}")
                continue
            if mid in valid_ids:
                memories_skipped += 1
                continue
            if dry_run:
                preview_memories.append({
                    "id": mid,
                    "title": m.get("title", ""),
                    "description": m.get("description", ""),
                    "type": m.get("type", ""),
                })
            else:
                try:
                    text = f"{m.get('title', '')} {m.get('description', '')} {m.get('content', '')}"
                    self._engine.add(text, mid)
                    self.memories.upsert_memory_row(
                        id=mid,
                        title=m.get("title", ""),
                        description=m.get("description", ""),
                        content=m.get("content", ""),
                        created_at=m.get("created_at", ""),
                        updated_at=m.get("updated_at", ""),
                        usage_count=int(m.get("usage_count", 0)),
                        score=float(m.get("score", 1.0)),
                        soft_deleted=bool(m.get("soft_deleted", False)),
                        confidence=m.get("confidence"),
                        confidence_count=int(m.get("confidence_count", 0)),
                        namespace=m.get("namespace", self._namespace),
                    )
                    log.info("import_memory_inserted", lore_id=mid, title=m.get("title", ""))
                except Exception as e:
                    errors.append(f"memory {mid}: {e}")
                    continue
            valid_ids.add(mid)
            memories_inserted += 1

        if not dry_run and memories_inserted:
            self._rebuild_kw()

        existing_link_ids: set[str] = {lnk.id for lnk in self.links.all_links()}

        for lnk in links:
            lid = lnk.get("id", "")
            if not lid:
                errors.append(f"link missing id: {lnk}")
                continue
            if lid in existing_link_ids:
                links_skipped += 1
                continue
            src = lnk.get("source_memory_id", "")
            tgt = lnk.get("target_memory_id", "")
            if src not in valid_ids or tgt not in valid_ids:
                links_error += 1
                continue
            if dry_run:
                preview_links.append({
                    "id": lid,
                    "source_memory_id": src,
                    "target_memory_id": tgt,
                    "relation_type": lnk.get("relation_type", "related_to"),
                    "reason": lnk.get("reason", ""),
                })
            else:
                try:
                    self.links.insert_link(
                        id=lid,
                        source_memory_id=src,
                        target_memory_id=tgt,
                        relation_type=lnk.get("relation_type", "related_to"),
                        reason=lnk.get("reason", ""),
                        score=float(lnk.get("score", 1.0)),
                        created_at=lnk.get("created_at"),
                        updated_at=lnk.get("updated_at"),
                        usage_count=int(lnk.get("usage_count", 0)),
                        confidence=lnk.get("confidence"),
                        confidence_count=int(lnk.get("confidence_count", 0)),
                    )
                except Exception as e:
                    errors.append(f"link {lid}: {e}")
                    continue
            links_inserted += 1

        return {
            "memories_inserted": memories_inserted,
            "memories_skipped": memories_skipped,
            "links_inserted": links_inserted,
            "links_skipped": links_skipped,
            "links_error": links_error,
            "errors": errors,
            "preview_memories": preview_memories,
            "preview_links": preview_links,
        }

    # ── Update (feedback) ────────────────────────────────────────────────────

    def update(
        self,
        memory_feedback: list[dict],
        link_feedback: list[dict],
    ) -> dict:
        self._increment_metric("lore_update")
        updated_memories = 0
        updated_links = 0
        soft_deleted = 0
        errors: list[dict] = []

        for fb in memory_feedback:
            try:
                mid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                row = self.memories.get_memory_row(mid, namespaces=self._ns_filter)
                if row is None:
                    errors.append({"id": mid, "error": "not found"})
                    continue

                new_score = apply_score_delta(
                    row["score"], useful, confidence, self.settings
                )
                fields: dict = {"score": new_score, "usage_count": row["usage_count"] + 1}

                if confidence is not None:
                    new_conf = compute_running_confidence(
                        row["confidence"], row["confidence_count"],
                        confidence, self.settings.confidence_window_size,
                    )
                    fields["confidence"] = new_conf
                    fields["confidence_count"] = row["confidence_count"] + 1

                threshold = self.settings.soft_delete_confidence_threshold
                if should_soft_delete(useful, confidence, threshold):
                    fields["soft_deleted"] = 1
                    soft_deleted += 1

                self.memories.update_memory_fields(mid, **fields)
                updated_memories += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        for fb in link_feedback:
            try:
                lid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                link = self.links.get_link(lid)
                if link is None:
                    errors.append({"id": lid, "error": "not found"})
                    continue

                new_score = apply_score_delta(
                    link.score, useful, confidence, self.settings
                )
                fields = {"score": new_score, "usage_count": link.usage_count + 1}

                if confidence is not None:
                    new_conf = compute_running_confidence(
                        link.confidence, link.confidence_count,
                        confidence, self.settings.confidence_window_size,
                    )
                    fields["confidence"] = new_conf
                    fields["confidence_count"] = link.confidence_count + 1

                self.links.update_link_fields(lid, **fields)
                updated_links += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        return {
            "updated_memories": updated_memories,
            "updated_links": updated_links,
            "soft_deleted_memories": soft_deleted,
            "errors": errors,
        }


    # ── Reflect ───────────────────────────────────────────────────────────────

    def submit_reflection(
        self,
        session_id: str,
        session_date: str | None,
        topic: str | None,
        task_type: str | None,
        what_was_done: str | None,
        decisions: str | None,
        lessons_learnt: list[str],
        good_patterns: list[str],
        user_profile_updates: list[str],
        factual_discoveries: list[str],
        summary: str,
        memory_ids: list[str],
    ) -> dict:
        self._increment_metric("lore_reflect")

        # Guard: if this session has already been processed, return idempotent no-op.
        # Root cause confirmed (LKPR-1): without this check, every duplicate call inserts a
        # fresh orphaned reflection row and overwrites the session's reflection_id pointer.
        existing_session = self.reflections.get_session(session_id)
        if existing_session is not None:
            log.info(
                "reflection_already_processed",
                session_id=session_id,
                existing_reflection_id=existing_session["reflection_id"],
            )
            return {
                "reflection_id": existing_session["reflection_id"],
                "session_id": session_id,
                "created_at": existing_session["reviewed_at"],
                "already_processed": True,
            }

        reflection_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        def _bullets(items: list[str]) -> str | None:
            return "\n".join(f"- {item}" for item in items) if items else None

        self.reflections.insert_reflection(
            id=reflection_id,
            created_at=now,
            session_count=1,
            lessons_learnt=_bullets(lessons_learnt) or "",
            good_patterns=_bullets(good_patterns),
            user_profile_updates=_bullets(user_profile_updates),
            factual_discoveries=_bullets(factual_discoveries),
            summary=summary,
            memory_ids=json.dumps(memory_ids) if memory_ids else None,
        )

        self.reflections.upsert_session(
            session_id=session_id,
            reviewed_at=now,
            session_date=session_date,
            topic=topic,
            task_type=task_type,
            reflection_id=reflection_id,
            what_was_done=what_was_done,
            decisions=decisions,
            lessons_learnt=_bullets(lessons_learnt),
            good_patterns=_bullets(good_patterns),
            user_profile=_bullets(user_profile_updates),
            discoveries=_bullets(factual_discoveries),
        )

        log.info("reflection_submitted", reflection_id=reflection_id, session_id=session_id)
        return {
            "reflection_id": reflection_id,
            "session_id": session_id,
            "created_at": now,
        }

    def get_processed_session_ids(self) -> list[str]:
        self._increment_metric("lore_processed_sessions")
        return list(self.reflections.all_processed_session_ids())


def _row_to_memory(row: Any) -> Memory:
    return Memory(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        content=row["content"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        usage_count=row["usage_count"],
        score=row["score"],
        soft_deleted=bool(row["soft_deleted"]),
        confidence=row["confidence"],
        confidence_count=row["confidence_count"],
        last_used=row["last_used"] if "last_used" in row.keys() else None,
        namespace=row["namespace"] if "namespace" in row.keys() else "shared",
    )
