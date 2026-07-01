"""Memory import (backup restore) — rare admin path.

Extracted from ``services/orchestrator.py`` (LKPR-104 Phase 5) into its own
module — it's a one-shot migration/restore utility, not part of the
per-request hot path, so it doesn't belong on ``MemorySearchService`` or
``MemoryWriteService``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lorekeeper.domains.link.models import TYPE_MIGRATION_MAP

if TYPE_CHECKING:
    from lorekeeper.services.orchestrator import MemoryService


class ImportService:
    """Backup/dump restore for memories and links."""

    def __init__(self, svc: MemoryService) -> None:
        self._svc = svc

    def import_dump(
        self,
        memories: list[dict[str, Any]],
        links: list[dict[str, Any]],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        svc = self._svc
        memories_inserted = 0
        memories_skipped = 0
        links_inserted = 0
        links_skipped = 0
        links_error = 0
        errors: list[str] = []
        preview_memories: list[dict[str, Any]] = []
        preview_links: list[dict[str, Any]] = []

        # Track IDs that exist or were just inserted (for FK validation)
        valid_ids: set[str] = {r["id"] for r in svc.memories.all_memory_rows(include_deleted=True)}

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
                    svc._engine.add(text, mid)
                    svc.memories.upsert_memory_row(
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
                        namespace=m.get("namespace", svc._namespace),
                    )
                except Exception as e:
                    errors.append(f"memory {mid}: {e}")
                    continue
            valid_ids.add(mid)
            memories_inserted += 1

        if not dry_run and memories_inserted:
            svc._rebuild_kw()
            svc._conn.commit()

        existing_link_ids: set[str] = {lnk.id for lnk in svc.links.all_links()}

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
                    svc.links.insert_link(
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
            svc._conn.commit()

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
