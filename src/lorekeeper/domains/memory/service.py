"""Memory domain service — search, insert, remember, update, forget.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5). This service
owns the Memory aggregate's use cases. It still depends on the orchestrator
instance for shared infra access (engine, keyword index, connection, cache) —
that coupling is intentional for this phase; the temporary ``MemoryService``
facade in ``orchestrator.py`` is deleted in Phase 7, at which point these
services take ownership of their own infra references directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.link.service import LinkService
from lorekeeper.domains.memory.cache import MemoryCache
from lorekeeper.domains.memory.dedup import is_duplicate
from lorekeeper.domains.memory.feedback import (
    apply_score_delta,
    compute_running_confidence,
    should_soft_delete,
)
from lorekeeper.domains.memory.models import row_to_memory
from lorekeeper.domains.memory.ranking import SearchResult, parse_iso_utc, rank_results
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.infra.database import Database
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.metrics.repository import MetricsStore

log = structlog.get_logger()


def extract_title(thought: str) -> str:
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


class MemorySearchService:
    """Search and bulk-lookup use cases for the Memory aggregate."""

    def __init__(
        self,
        engine: LanceDBEngine,
        kw: KeywordIndex,
        memories: MemoryStore,
        links: LinkStore,
        cache: MemoryCache,
        metrics: MetricsStore,
        settings: Settings,
        db: Database,
        ns_filter: list[str] | None,
    ) -> None:
        self._engine = engine
        self._kw = kw
        self._memories = memories
        self._links = links
        self._cache = cache
        self._metrics = metrics
        self._settings = settings
        self._db = db
        self._ns_filter = ns_filter

    def search(
        self,
        query: str,
        limit: int | None = None,
        min_score: float = 0.1,
        include_links: bool = True,
        include_deleted: bool = False,
        refine_from: list[str] | None = None,
        search_format: str = "full",
        created_after: datetime | None = None,
        updated_after: datetime | None = None,
        sort_by: str = "relevance",
        source_type: str | None = None,
    ) -> list[SearchResult]:
        sem_hits = self._engine.search(query, limit=200)
        kw_hits = self._kw.search_normalized(query)
        memories = self._cache.all_memories(include_deleted=include_deleted)

        if limit is None:
            limit = self._settings.search_limit

        links_by_id: dict[str, list[Any]] = {}
        if include_links and search_format != "title":
            max_links = self._settings.max_links_per_memory
            for mid in memories:
                all_links = self._links.links_for_memory(mid)
                links_by_id[mid] = all_links[:max_links]

        results = rank_results(
            sem_hits, kw_hits, memories, links_by_id,
            self._settings, limit, min_score, include_deleted,
            refine_from=refine_from,
            created_after=created_after,
            updated_after=updated_after,
            sort_by=sort_by,
            source_type=source_type,
        )

        # Increment usage on returned memories
        for r in results:
            self._memories.update_memory_fields(r.memory.id, usage_count=r.memory.usage_count + 1)
        self._db.commit()

        return results

    def search_by_ids(
        self,
        ids: list[str],
        include_deleted: bool = False,
        include_links: bool = True,
        created_after: datetime | None = None,
        updated_after: datetime | None = None,
        sort_by: str = "relevance",
        source_type: str | None = None,
    ) -> list[SearchResult]:
        """Bulk lookup by lore_id — skips vector/BM25 entirely.

        Returns SearchResult objects with zero relevance scores (SQL-only path).
        Timestamp filters and sort_by compose with the ids path.
        """
        if not ids:
            return []

        # De-duplicate while preserving order
        ids = list(dict.fromkeys(ids))

        rows = self._memories.get_memory_rows(ids, namespaces=self._ns_filter)
        results: list[SearchResult] = []
        for row in rows:
            mem = row_to_memory(row)
            if not include_deleted and mem.soft_deleted:
                continue
            # LKPR-61: apply timestamp filters on the ids path too.
            if created_after is not None:
                try:
                    if parse_iso_utc(mem.created_at) < created_after:
                        continue
                except ValueError:
                    continue
            if updated_after is not None:
                try:
                    if parse_iso_utc(mem.updated_at) < updated_after:
                        continue
                except ValueError:
                    continue
            # LKPR-18: source_type filter on the ids path.
            if source_type is not None and mem.source_type != source_type:
                continue
            links: list[Any] = []
            if include_links:
                links = self._links.links_for_memory(mem.id)[:self._settings.max_links_per_memory]
            results.append(SearchResult(
                memory=mem,
                combined_score=0.0,
                semantic_score=0.0,
                keyword_score=0.0,
                links=links,
                decay_factor=1.0,
            ))
        # LKPR-80: sort_by on the ids path.
        # Guard: a single malformed updated_at must not crash the entire sort; fall back to
        # datetime.min so the offending row sorts last rather than raising ValueError.
        if sort_by == "recent":
            def _recent_key(r: SearchResult) -> datetime:
                try:
                    return parse_iso_utc(r.memory.updated_at)
                except (ValueError, TypeError):
                    return datetime.min.replace(tzinfo=UTC)

            results.sort(key=_recent_key, reverse=True)
        elif sort_by == "frequent":
            results.sort(key=lambda r: r.memory.usage_count, reverse=True)
        else:
            # Default: preserve input ID order (original behaviour).
            result_by_id = {r.memory.id: r for r in results}
            results = [result_by_id[i] for i in ids if i in result_by_id]

        # Increment usage_count on all returned memories in one transaction
        self._memories.bulk_increment_usage_count([r.memory.id for r in results])
        self._db.commit()

        return results


class MemoryWriteService:
    """Insert, remember, update, forget, and auto-link use cases."""

    def __init__(
        self,
        engine: LanceDBEngine,
        memories: MemoryStore,
        links: LinkStore,
        cache: MemoryCache,
        metrics: MetricsStore,
        settings: Settings,
        db: Database,
        namespace: str,
        ns_filter: list[str] | None,
        link_service: LinkService,
        kw: KeywordIndex,
    ) -> None:
        self._engine = engine
        self._memories = memories
        self._links = links
        self._cache = cache
        self._metrics = metrics
        self._settings = settings
        self._db = db
        self._namespace = namespace
        self._ns_filter = ns_filter
        self._link_service = link_service
        self._kw = kw

    def insert(
        self,
        memories: list[dict[str, Any]],
        links: list[dict[str, Any]],
        force: bool = False,
    ) -> dict[str, Any]:
        inserted_memories: list[dict[str, Any]] = []
        inserted_links: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

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

                result = self.insert_one_memory(m, force)
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
                        self.auto_link(link_text.strip(), lore_id, source="insert")
                    except Exception:
                        log.warning("auto_link_failed", lore_id=lore_id, exc_info=True)

                    # Normalize inline links to standard format and delegate to _insert_one_link
                    if inline_links:
                        for link_def in inline_links:
                            try:
                                # Validate target exists and is within scoped namespaces
                                target_row = self._memories.get_memory_row(
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
                                inserted = self._link_service.insert_one_link(normalized)
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
            self._cache.rebuild_kw()

        for lnk in links:
            try:
                inserted = self._link_service.insert_one_link(lnk)
                inserted_links.append(inserted)
            except Exception as e:
                errors.append({"input": str(lnk), "error": str(e)})

        if inserted_memories or inserted_links:
            self._db.commit()

        return {
            "inserted_memories": inserted_memories,
            "inserted_links": inserted_links,
            "duplicates": duplicates,
            "errors": errors,
        }

    def remember(self, thought: str, source_type: str = "observed") -> dict[str, Any]:
        """Fast one-shot insert with auto-extracted fields and auto-linking."""
        result = self.remember_with_score(
            thought, score=self._settings.new_memory_default_score, source_type=source_type
        )
        return {
            "id": result["id"],
            "title": result["title"],
            "linked_to": result["linked_to"],
        }

    def remember_with_score(
        self, thought: str, score: float, source_type: str = "observed"
    ) -> dict[str, Any]:
        """Internal helper for remember-like insert with explicit score override.

        Returns a stable payload with created flag so callers (e.g. lore_reflect)
        can distinguish new inserts from dedup hits.
        """
        title = extract_title(thought)
        description = title

        result = self.insert_one_memory({
            "title": title,
            "description": description,
            "content": thought,
            "score": score,
            "source_type": source_type,
        }, force=False)

        if "duplicate" in result:
            dup = result["duplicate"]
            return {
                "id": dup["existing_memory"]["id"],
                "title": title,
                "linked_to": None,
                "created": False,
            }

        lore_id = result["inserted"]["id"]

        # Rebuild KW index after the insert
        self._cache.rebuild_kw()

        linked_to = self.auto_link(thought, lore_id)
        self._db.commit()
        return {"id": lore_id, "title": title, "linked_to": linked_to, "created": True}

    def auto_link(
        self, text: str, lore_id: str, source: str = "remember"
    ) -> dict[str, Any] | None:
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
        if not self._settings.auto_link_enabled:
            return None

        if not text or not text.strip():
            return None

        # Clamp k to [1, 200] — non-positive values crash some vector backends
        k = max(1, min(self._settings.auto_link_k, 200))
        threshold = self._settings.auto_link_threshold

        try:
            sem_hits = self._engine.search(text, limit=k)
        except Exception:
            log.warning("auto_link: engine.search failed", exc_info=True)
            return None

        # Pre-compute the set of IDs already linked to lore_id (both directions)
        try:
            existing_links = self._links.links_for_memory(lore_id)
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
                target_row = self._memories.get_memory_row(
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
                self._links.insert_link(
                    source_memory_id=lore_id,
                    target_memory_id=hit["lore_id"],
                    relation_type="references",
                    reason=f"auto-linked from lore_{source}: {raw_score:.2f}",
                )
            except Exception:
                log.warning("auto_link: insert_link failed", exc_info=True)
                continue

            return {"id": hit["lore_id"], "score": raw_score}
        return None

    def insert_one_memory(self, m: dict[str, Any], force: bool) -> dict[str, Any]:
        if "title" not in m:
            raise ValueError("memory dict missing required field: 'title'")
        title = m["title"]
        description = m.get("description", "")
        content = m.get("content", "")
        score = float(m.get("score", self._settings.new_memory_default_score))
        source_type = m.get("source_type", "observed")
        text = f"{title} {description} {content}"

        if not force:
            # Shared agent checks across all namespaces (no filter) to preserve
            # pre-existing global dedup behavior. Non-shared agents scope checks
            # to their own namespace + the shared pool.
            ns_filter = self._ns_filter
            # Exact title match is a definitive duplicate — skip semantic search
            existing_by_title = self._memories.get_memory_row_by_title(title, namespaces=ns_filter)
            if existing_by_title:
                return {"duplicate": {
                    "input_title": title,
                    "existing_memory": row_to_memory(existing_by_title).model_dump(),
                    "similarity": 1.0,
                }}

            sem_hits = self._engine.search(text, limit=5)
            kw_hits = self._kw.search_normalized(text)
            for hit in sem_hits:
                lid = hit["lore_id"]
                sem = hit["score"]
                kw = kw_hits.get(lid, 0.0)
                if is_duplicate(sem, kw, self._settings):
                    existing_row = self._memories.get_memory_row(lid, namespaces=ns_filter)
                    if existing_row:
                        return {"duplicate": {
                            "input_title": title,
                            "existing_memory": row_to_memory(existing_row).model_dump(),
                            "similarity": round(0.6 * sem + 0.4 * kw, 4),
                        }}

        lore_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        self._engine.add(text, lore_id)
        self._memories.upsert_memory_row(
            id=lore_id, title=title, description=description, content=content,
            created_at=now, updated_at=now, score=score, namespace=self._namespace,
            source_type=source_type,
        )
        log.info("memory_inserted", lore_id=lore_id, title=title)
        return {"inserted": {"id": lore_id, "title": title}}

    def update(
        self,
        memory_feedback: list[dict[str, Any]],
        link_feedback: list[dict[str, Any]],
    ) -> dict[str, Any]:
        updated_memories = 0
        updated_links = 0
        soft_deleted = 0
        errors: list[dict[str, Any]] = []

        for fb in memory_feedback:
            try:
                mid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                row = self._memories.get_memory_row(mid, namespaces=self._ns_filter)
                if row is None:
                    errors.append({"id": mid, "error": "not found"})
                    continue

                new_score = apply_score_delta(
                    row["score"], useful, confidence, self._settings
                )
                fields: dict[str, Any] = {"score": new_score, "usage_count": row["usage_count"] + 1}

                if confidence is not None:
                    new_conf = compute_running_confidence(
                        row["confidence"], row["confidence_count"],
                        confidence, self._settings.confidence_window_size,
                    )
                    fields["confidence"] = new_conf
                    fields["confidence_count"] = row["confidence_count"] + 1

                threshold = self._settings.soft_delete_confidence_threshold
                if should_soft_delete(useful, confidence, threshold):
                    fields["soft_deleted"] = 1
                    soft_deleted += 1

                self._memories.update_memory_fields(mid, **fields)
                updated_memories += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        for fb in link_feedback:
            try:
                lid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                link = self._links.get_link(lid)
                if link is None:
                    errors.append({"id": lid, "error": "not found"})
                    continue

                # Enforce namespace scope: verify both endpoints are accessible
                if self._ns_filter is not None:
                    source_row = self._memories.get_memory_row(
                        link.source_memory_id, namespaces=self._ns_filter
                    )
                    target_row = self._memories.get_memory_row(
                        link.target_memory_id, namespaces=self._ns_filter
                    )
                    if source_row is None or target_row is None:
                        errors.append({"id": lid, "error": "not found"})
                        continue

                new_score = apply_score_delta(
                    link.score, useful, confidence, self._settings
                )
                fields = {"score": new_score, "usage_count": link.usage_count + 1}

                if confidence is not None:
                    new_conf = compute_running_confidence(
                        link.confidence, link.confidence_count,
                        confidence, self._settings.confidence_window_size,
                    )
                    fields["confidence"] = new_conf
                    fields["confidence_count"] = link.confidence_count + 1

                self._links.update_link_fields(lid, **fields)
                updated_links += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        if updated_memories or updated_links:
            self._db.commit()
        if updated_memories:
            self._cache.invalidate()

        return {
            "updated_memories": updated_memories,
            "updated_links": updated_links,
            "soft_deleted_memories": soft_deleted,
            "errors": errors,
        }

    def update_memory_fields(self, memory_id: str, **fields: Any) -> dict[str, bool]:
        """Update a memory's scalar fields (dashboard route).

        Owns the 404 check and persistence commit so the route layer
        stays free of transaction control.
        """
        row = self._memories.get_memory_row(memory_id, namespaces=self._ns_filter)
        if row is None:
            raise ValueError(f"Memory {memory_id} not found")
        self._memories.update_memory_fields(memory_id, **fields)
        self._db.commit()
        return {"ok": True}

    def delete_memory(self, memory_id: str) -> dict[str, bool]:
        """Permanently delete a memory row (dashboard route).

        Owns the 404 check and persistence commit so the route layer
        stays free of transaction control.
        """
        row = self._memories.get_memory_row(memory_id, namespaces=self._ns_filter)
        if row is None:
            raise ValueError(f"Memory {memory_id} not found")
        self._memories.delete_memory_row(memory_id)
        self._db.commit()
        return {"ok": True}

    def forget(self, memory_ids: list[str], reason: str = "unspecified") -> dict[str, Any]:
        """Immediately soft-delete one or more memories by ID.

        Reuses the existing soft-delete field — no new schema. Reason is logged
        for auditability but not persisted to the DB (soft_deleted=1 is the signal).
        """
        if not memory_ids:
            raise ValueError("memory_ids must not be empty")
        _VALID_REASONS = {"duplicate", "hallucinated", "outdated", "expired", "unspecified"}
        if reason not in _VALID_REASONS:
            raise ValueError(f"Unknown reason {reason!r}. Must be one of: {sorted(_VALID_REASONS)}")
        forgotten: list[str] = []
        not_found: list[str] = []
        errors: list[dict[str, Any]] = []

        for mid in memory_ids:
            try:
                row = self._memories.get_memory_row(mid, namespaces=self._ns_filter)
                if row is None:
                    not_found.append(mid)
                    continue
                self._memories.update_memory_fields(mid, soft_deleted=1)
                forgotten.append(mid)
                log.info("lore_forget", memory_id=mid, reason=reason)
            except Exception as e:
                errors.append({"id": mid, "error": str(e)})

        if forgotten:
            self._db.commit()
            self._cache.rebuild_kw()

        return {
            "forgotten": forgotten,
            "not_found": not_found,
            "errors": errors,
        }
