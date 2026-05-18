import uuid
from datetime import datetime, timezone

import structlog

from lorekeeper.config import Settings
from lorekeeper.models import Memory, MemoryLink
from lorekeeper.services.dedup import is_duplicate
from lorekeeper.services.feedback import (
    apply_score_delta,
    compute_running_confidence,
    should_soft_delete,
)
from lorekeeper.services.keyword_index import KeywordIndex
from lorekeeper.services.link_store import LinkStore
from lorekeeper.services.memory_engine import MemoryEngine
from lorekeeper.services.search import SearchResult, rank_results

log = structlog.get_logger()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryService:
    def __init__(
        self,
        engine: MemoryEngine,
        store: LinkStore,
        keyword_index: KeywordIndex,
        settings: Settings,
    ) -> None:
        self._engine = engine
        self._store = store
        self._kw = keyword_index
        self._settings = settings

    def _all_memories(self, include_deleted: bool = False) -> dict[str, Memory]:
        rows = self._store.all_memory_rows(include_deleted=include_deleted)
        return {r["id"]: _row_to_memory(r) for r in rows}

    def _rebuild_kw(self) -> None:
        mems = list(self._all_memories(include_deleted=True).values())
        self._kw.rebuild(mems)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.1,
        include_links: bool = True,
        include_deleted: bool = False,
    ) -> list[SearchResult]:
        sem_hits = self._engine.search(query, limit=200)
        kw_hits = self._kw.search_normalized(query)
        memories = self._all_memories(include_deleted=include_deleted)

        links_by_id: dict[str, list[MemoryLink]] = {}
        if include_links:
            for mid in memories:
                links_by_id[mid] = self._store.links_for_memory(mid)

        results = rank_results(
            sem_hits, kw_hits, memories, links_by_id,
            self._settings, limit, min_score, include_deleted,
        )

        # Increment usage on returned memories
        for r in results:
            self._store.update_memory_fields(r.memory.id, usage_count=r.memory.usage_count + 1)

        return results

    # ── Insert ────────────────────────────────────────────────────────────────

    def insert(
        self,
        memories: list[dict],
        links: list[dict],
        force: bool = False,
    ) -> dict:
        inserted_memories: list[dict] = []
        inserted_links: list[dict] = []
        duplicates: list[dict] = []
        errors: list[dict] = []

        for m in memories:
            try:
                result = self._insert_one_memory(m, force)
                if result.get("duplicate"):
                    duplicates.append(result["duplicate"])
                else:
                    inserted_memories.append(result["inserted"])
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

    def _insert_one_memory(self, m: dict, force: bool) -> dict:
        title = m["title"]
        description = m.get("description", "")
        content = m.get("content", "")
        score = float(m.get("score", 1.0))

        if not force:
            # Check for duplicates via hybrid score
            text = f"{title} {description} {content}"
            sem_hits = self._engine.search(text, limit=5)
            kw_hits = self._kw.search_normalized(text)
            for hit in sem_hits:
                lid = hit["lore_id"]
                sem = hit["score"]
                kw = kw_hits.get(lid, 0.0)
                if is_duplicate(sem, kw, self._settings):
                    existing_row = self._store.get_memory_row(lid)
                    if existing_row:
                        return {"duplicate": {
                            "input_title": title,
                            "existing_memory": dict(existing_row),
                            "similarity": round(0.6 * sem + 0.4 * kw, 4),
                        }}

        lore_id = str(uuid.uuid4())
        now = _now()
        text = f"{title} {description} {content}"
        self._engine.add(text, lore_id)
        self._store.upsert_memory_row(
            id=lore_id, title=title, description=description, content=content,
            created_at=now, updated_at=now, score=score,
        )
        log.info("memory_inserted", lore_id=lore_id, title=title)
        return {"inserted": {"id": lore_id, "title": title}}

    def _insert_one_link(self, lnk: dict) -> dict:
        link = self._store.insert_link(
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

    # ── Update (feedback) ────────────────────────────────────────────────────

    def update(
        self,
        memory_feedback: list[dict],
        link_feedback: list[dict],
    ) -> dict:
        updated_memories = 0
        updated_links = 0
        soft_deleted = 0
        errors: list[dict] = []

        for fb in memory_feedback:
            try:
                mid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                row = self._store.get_memory_row(mid)
                if row is None:
                    errors.append({"id": mid, "error": "not found"})
                    continue

                new_score = apply_score_delta(
                    row["score"], useful, confidence, self._settings
                )
                fields: dict = {"score": new_score, "usage_count": row["usage_count"] + 1}

                if confidence is not None:
                    new_conf = compute_running_confidence(
                        row["confidence"], row["confidence_count"],
                        confidence, self._settings.confidence_window_size,
                    )
                    fields["confidence"] = new_conf
                    fields["confidence_count"] = row["confidence_count"] + 1

                if should_soft_delete(useful, confidence, self._settings.soft_delete_confidence_threshold):
                    fields["soft_deleted"] = 1
                    soft_deleted += 1

                self._store.update_memory_fields(mid, **fields)
                updated_memories += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        for fb in link_feedback:
            try:
                lid = fb["id"]
                useful = bool(fb["useful"])
                confidence = fb.get("confidence")
                link = self._store.get_link(lid)
                if link is None:
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

                self._store.update_link_fields(lid, **fields)
                updated_links += 1
            except Exception as e:
                errors.append({"id": fb.get("id", "?"), "error": str(e)})

        return {
            "updated_memories": updated_memories,
            "updated_links": updated_links,
            "soft_deleted_memories": soft_deleted,
            "errors": errors,
        }


def _row_to_memory(row: object) -> Memory:
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
    )
