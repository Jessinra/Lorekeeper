from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from lorekeeper.domains.link.models import RELATION_TYPES, TYPE_MIGRATION_MAP, MemoryLink
from lorekeeper.domains.link.repository import LinkStore
from lorekeeper.domains.memory.models import Memory
from lorekeeper.domains.memory.repository import MemoryStore
from lorekeeper.domains.reflection.repository import ReflectionStore
from lorekeeper.infra.keyword_index import KeywordIndex
from lorekeeper.infra.search_engine import LanceDBEngine
from lorekeeper.infra.settings import Settings
from lorekeeper.platform.config.repository import ConfigStore
from lorekeeper.platform.metrics.repository import MetricsStore
from lorekeeper.services.dedup import is_duplicate
from lorekeeper.services.feedback import (
    apply_score_delta,
    compute_running_confidence,
    should_soft_delete,
)
from lorekeeper.services.search import SearchResult, parse_iso_utc, rank_results

if TYPE_CHECKING:
    from lorekeeper.services.link_candidate import LinkCandidate, LinkCandidateGenerator

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
        engine: LanceDBEngine,
        memories: MemoryStore,
        links: LinkStore,
        reflections: ReflectionStore,
        metrics: MetricsStore,
        config: ConfigStore,
        keyword_index: KeywordIndex,
        settings: Settings,
        link_candidate_generator: LinkCandidateGenerator | None = None,
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
        # Orchestrator owns commit control — all stores share this connection
        self._conn = memories._conn
        # Namespace filter for all read/write operations: None = no filter (shared sees all).
        self._ns_filter: list[str] | None = (
            None if self._namespace == "shared" else [self._namespace, "shared"]
        )
        # LKPR-60: in-process cache for all_memories(include_deleted=True).
        # None means dirty — must reload from SQLite. Cache always holds the full
        # (include_deleted=True) dataset; include_deleted=False is filtered in Python.
        self._memory_cache: dict[str, Memory] | None = None
        # LKPR-58: instantiate LinkCandidateGenerator once so spaCy model is only loaded once.
        if link_candidate_generator is not None:
            self._link_candidate_generator = link_candidate_generator
        else:
            from lorekeeper.services.link_candidate import LinkCandidateGenerator

            self._link_candidate_generator = LinkCandidateGenerator(
                engine=self._engine,
                memory_store=self.memories,
                link_store=self.links,
                keyword_index=self._kw,
                settings=self.settings,
                ns_filter=self._ns_filter,
            )

    def _invalidate_cache(self) -> None:
        """Mark the memory cache dirty. Call at every write that adds/removes memories."""
        self._memory_cache = None

    def commit(self) -> None:
        """Flush all pending writes to disk.

        Dashboard routes use this instead of accessing _conn directly.
        """
        self._conn.commit()

    def _all_memories(self, include_deleted: bool = False) -> dict[str, Memory]:
        # None → no filter → reads all rows (backward-compat for the default "shared" agent).
        # Non-shared agents scope reads to their own namespace + the shared pool.
        namespaces = self._ns_filter
        if self._memory_cache is None:
            rows = self.memories.all_memory_rows(include_deleted=True, namespaces=namespaces)
            self._memory_cache = {r["id"]: _row_to_memory(r) for r in rows}
        if include_deleted:
            return dict(self._memory_cache)
        return {mid: m for mid, m in self._memory_cache.items() if not m.soft_deleted}

    def _rebuild_kw(self) -> None:
        self._invalidate_cache()
        mems = list(self._all_memories(include_deleted=True).values())
        self._kw.rebuild(mems)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _increment_metric(self, tool_name: str) -> None:
        try:
            self.metrics.increment_metric(tool_name)
            self._conn.commit()
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
        search_format: str = "full",
        created_after: datetime | None = None,
        updated_after: datetime | None = None,
        sort_by: str = "relevance",
        source_type: str | None = None,
    ) -> list[SearchResult]:
        self._increment_metric("lore_search")
        sem_hits = self._engine.search(query, limit=200)
        kw_hits = self._kw.search_normalized(query)
        memories = self._all_memories(include_deleted=include_deleted)

        if limit is None:
            limit = self.settings.search_limit

        links_by_id: dict[str, list[MemoryLink]] = {}
        if include_links and search_format != "title":
            max_links = self.settings.max_links_per_memory
            for mid in memories:
                all_links = self.links.links_for_memory(mid)
                links_by_id[mid] = all_links[:max_links]

        results = rank_results(
            sem_hits, kw_hits, memories, links_by_id,
            self.settings, limit, min_score, include_deleted,
            refine_from=refine_from,
            created_after=created_after,
            updated_after=updated_after,
            sort_by=sort_by,
            source_type=source_type,
        )

        # Increment usage on returned memories
        for r in results:
            self.memories.update_memory_fields(r.memory.id, usage_count=r.memory.usage_count + 1)
        self._conn.commit()

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

        rows = self.memories.get_memory_rows(ids, namespaces=self._ns_filter)
        results: list[SearchResult] = []
        for row in rows:
            mem = _row_to_memory(row)
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
            links: list[MemoryLink] = []
            if include_links:
                links = self.links.links_for_memory(mem.id)[:self.settings.max_links_per_memory]
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
        self.memories.bulk_increment_usage_count([r.memory.id for r in results])
        self._conn.commit()

        return results

    # ── Insert ────────────────────────────────────────────────────────────────

    def insert(
        self,
        memories: list[dict[str, Any]],
        links: list[dict[str, Any]],
        force: bool = False,
    ) -> dict[str, Any]:
        self._increment_metric("lore_insert")
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

        if inserted_memories or inserted_links:
            self._conn.commit()

        return {
            "inserted_memories": inserted_memories,
            "inserted_links": inserted_links,
            "duplicates": duplicates,
            "errors": errors,
        }

    # ── Remember (fast one-shot insert) ────────────────────────────────────────

    def remember(self, thought: str, source_type: str = "observed") -> dict[str, Any]:
        """Fast one-shot insert with auto-extracted fields and auto-linking."""
        self._increment_metric("lore_remember")
        result = self._remember_with_score(
            thought, score=self.settings.new_memory_default_score, source_type=source_type
        )
        return {
            "id": result["id"],
            "title": result["title"],
            "linked_to": result["linked_to"],
        }

    def _remember_with_score(
        self, thought: str, score: float, source_type: str = "observed"
    ) -> dict[str, Any]:
        """Internal helper for remember-like insert with explicit score override.

        Returns a stable payload with created flag so callers (e.g. lore_reflect)
        can distinguish new inserts from dedup hits.
        """
        title = self._extract_title(thought)
        description = title

        result = self._insert_one_memory({
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
        self._rebuild_kw()

        linked_to = self._auto_link(thought, lore_id)
        self._conn.commit()
        return {"id": lore_id, "title": title, "linked_to": linked_to, "created": True}

    def _auto_link(
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
                    relation_type="references",
                    reason=f"auto-linked from lore_{source}: {raw_score:.2f}",
                )
            except Exception:
                log.warning("auto_link: insert_link failed", exc_info=True)
                continue

            self._increment_metric("auto_linked")
            return {"id": hit["lore_id"], "score": raw_score}
        return None

    def _insert_one_memory(self, m: dict[str, Any], force: bool) -> dict[str, Any]:
        if "title" not in m:
            raise ValueError("memory dict missing required field: 'title'")
        title = m["title"]
        description = m.get("description", "")
        content = m.get("content", "")
        score = float(m.get("score", self.settings.new_memory_default_score))
        source_type = m.get("source_type", "observed")
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
            source_type=source_type,
        )
        log.info("memory_inserted", lore_id=lore_id, title=title)
        return {"inserted": {"id": lore_id, "title": title}}

    def _insert_one_link(self, lnk: dict[str, Any]) -> dict[str, Any]:
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
        memories: list[dict[str, Any]],
        links: list[dict[str, Any]],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        memories_inserted = 0
        memories_skipped = 0
        links_inserted = 0
        links_skipped = 0
        links_error = 0
        errors: list[str] = []
        preview_memories: list[dict[str, Any]] = []
        preview_links: list[dict[str, Any]] = []

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
            self._conn.commit()

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
            # Normalise legacy relation types so old dumps restore correctly.
            raw_rel = lnk.get("relation_type", "references")
            normalized_rel = TYPE_MIGRATION_MAP.get(raw_rel, raw_rel)
            if dry_run:
                preview_links.append({
                    "id": lid,
                    "source_memory_id": src,
                    "target_memory_id": tgt,
                    "relation_type": normalized_rel,
                    "reason": lnk.get("reason", ""),
                })
            else:
                try:
                    self.links.insert_link(
                        id=lid,
                        source_memory_id=src,
                        target_memory_id=tgt,
                        relation_type=normalized_rel,
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

        if not dry_run and links_inserted:
            self._conn.commit()

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
        memory_feedback: list[dict[str, Any]],
        link_feedback: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self._increment_metric("lore_update")
        updated_memories = 0
        updated_links = 0
        soft_deleted = 0
        errors: list[dict[str, Any]] = []

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
                fields: dict[str, Any] = {"score": new_score, "usage_count": row["usage_count"] + 1}

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

        if updated_memories or updated_links:
            self._conn.commit()
        if updated_memories:
            self._invalidate_cache()

        return {
            "updated_memories": updated_memories,
            "updated_links": updated_links,
            "soft_deleted_memories": soft_deleted,
            "errors": errors,
        }


    # ── Forget ────────────────────────────────────────────────────────────────

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
        self._increment_metric("lore_forget")
        forgotten: list[str] = []
        not_found: list[str] = []
        errors: list[dict[str, Any]] = []

        for mid in memory_ids:
            try:
                row = self.memories.get_memory_row(mid, namespaces=self._ns_filter)
                if row is None:
                    not_found.append(mid)
                    continue
                self.memories.update_memory_fields(mid, soft_deleted=1)
                forgotten.append(mid)
                log.info("lore_forget", memory_id=mid, reason=reason)
            except Exception as e:
                errors.append({"id": mid, "error": str(e)})

        if forgotten:
            self._conn.commit()
            self._rebuild_kw()

        return {
            "forgotten": forgotten,
            "not_found": not_found,
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
        auto_insert: bool = True,
    ) -> dict[str, Any]:
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
                "memories_created": [],
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
        self._conn.commit()  # commit reflection + session rows before auto-insert

        # Auto-insert factual_discoveries and lessons_learnt as memories (best-effort)
        memories_created: list[dict[str, Any]] = []
        if auto_insert:
            _auto_items: list[tuple[list[str], str, float]] = [
                (factual_discoveries, "discovered_in", 7.0),
                (lessons_learnt, "learned_in", 8.0),
            ]
            new_inserts = 0
            skipped = 0
            for items_list, relation, score in _auto_items:
                for text in items_list:
                    try:
                        title = self._extract_title(text)
                        result = self._insert_one_memory(
                            {"title": title, "description": title, "content": text, "score": score},
                            force=False,
                        )
                        if "duplicate" in result:
                            mem_id = result["duplicate"]["existing_memory"]["id"]
                            status = "duplicate"
                        elif "inserted" in result:
                            mem_id = result["inserted"]["id"]
                            status = "inserted"
                            new_inserts += 1
                        else:
                            raise ValueError(
                                f"unexpected _insert_one_memory result shape: {result!r}"
                            )
                        memories_created.append(
                            {"id": mem_id, "title": title, "relation": relation, "status": status}
                        )
                    except Exception:
                        skipped += 1
                        log.warning(
                            "reflect_auto_insert_failed",
                            text=str(text)[:80],
                            relation=relation,
                            exc_info=True,
                        )

            if skipped:
                log.info(
                    "reflect_auto_insert_partial",
                    skipped=skipped,
                    inserted=new_inserts,
                    session_id=session_id,
                )
            if new_inserts:
                self._rebuild_kw()
                self._conn.commit()

        return {
            "reflection_id": reflection_id,
            "session_id": session_id,
            "created_at": now,
            "memories_created": memories_created,
        }

    def recommend_links(
        self,
        lore_id: str,
        top_k: int | None = None,
    ) -> list[LinkCandidate]:
        """Return link candidates for a source memory. Never writes.

        Args:
            lore_id: Source memory to find candidates for.
            top_k: Override max candidates (default: settings.link_top_m).
        """
        self._increment_metric("lore_recommend_links")
        from lorekeeper.services.link_candidate import LinkCandidateGenerator

        effective = self.settings
        if top_k is not None:
            effective = effective.model_copy(update={"link_top_m": top_k})
            generator = LinkCandidateGenerator(
                engine=self._engine,
                memory_store=self.memories,
                link_store=self.links,
                keyword_index=self._kw,
                settings=effective,
                ns_filter=self._ns_filter,
            )
        else:
            generator = self._link_candidate_generator
        candidates = generator.generate(lore_id)

        return candidates

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
        source_type=row["source_type"] if "source_type" in row.keys() else "unknown",
    )
