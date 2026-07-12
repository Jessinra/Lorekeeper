"""Memory row CRUD — extracted from LinkStore as part of LKPR-51."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import cast

from lorekeeper.infra.database import Database


def _now() -> str:
    return datetime.now(UTC).isoformat()


class MemoryStore:
    """CRUD for the `memories` table.

    All callers receive `sqlite3.Row` (or list thereof); the orchestrator
    converts these to Pydantic `Memory` models. Typed-model returns are
    a follow-up (see LKPR-51 ticket).
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._conn = db.conn

    def upsert_memory_row(
        self,
        id: str,
        title: str,
        description: str,
        content: str,
        created_at: str,
        updated_at: str,
        usage_count: int = 0,
        score: float = 1.0,
        soft_deleted: bool = False,
        confidence: float | None = None,
        confidence_count: int = 0,
        last_used: str | None = None,
        namespace: str = "shared",
        source_type: str = "observed",
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO memories
              (id, title, description, content, created_at, updated_at,
               usage_count, score, soft_deleted, confidence, confidence_count,
               last_used, namespace, source_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title, description=excluded.description,
              content=excluded.content, updated_at=excluded.updated_at,
              usage_count=excluded.usage_count, score=excluded.score,
              soft_deleted=excluded.soft_deleted, confidence=excluded.confidence,
              confidence_count=excluded.confidence_count,
              last_used=COALESCE(excluded.last_used, last_used),
              source_type=excluded.source_type
            """,
            (id, title, description, content, created_at, updated_at,
             usage_count, score, int(soft_deleted), confidence,
             confidence_count, last_used, namespace, source_type),
        )

    def get_memory_row(
        self, id: str, namespaces: list[str] | None = None,
    ) -> sqlite3.Row | None:
        sql = "SELECT * FROM memories WHERE id = ?"
        params: list[object] = [id]
        if namespaces is not None:
            if not namespaces:
                return None
            placeholders = ",".join("?" * len(namespaces))
            sql += f" AND namespace IN ({placeholders})"
            params.extend(namespaces)
        return cast(sqlite3.Row | None, self._conn.execute(sql, params).fetchone())

    def get_memory_rows(
        self, ids: list[str], namespaces: list[str] | None = None
    ) -> list[sqlite3.Row]:
        """Bulk lookup by IDs — SELECT WHERE id IN (...).

        Batches into chunks of 500 to stay under SQLite's variable limit (999).
        Returns only rows that exist (silently skips missing IDs).
        Preserves no particular order — caller should re-order if needed.
        """
        if not ids:
            return []
        # De-duplicate while preserving order
        ids = list(dict.fromkeys(ids))
        _CHUNK_SIZE = 500
        results: list[sqlite3.Row] = []
        for i in range(0, len(ids), _CHUNK_SIZE):
            chunk = ids[i : i + _CHUNK_SIZE]
            placeholders = ",".join("?" * len(chunk))
            sql = f"SELECT * FROM memories WHERE id IN ({placeholders}) AND soft_deleted = 0"
            params: list[object] = list(chunk)
            if namespaces is not None:
                if not namespaces:
                    continue
                ns_placeholders = ",".join("?" * len(namespaces))
                sql += f" AND namespace IN ({ns_placeholders})"
                params.extend(namespaces)
            results.extend(self._conn.execute(sql, params).fetchall())
        return results

    def get_memory_row_by_title(
        self, title: str, namespaces: list[str] | None = None
    ) -> sqlite3.Row | None:
        sql = "SELECT * FROM memories WHERE title = ? AND soft_deleted = 0"
        params: list[object] = [title]
        if namespaces is not None:
            if not namespaces:
                return None
            placeholders = ",".join("?" * len(namespaces))
            sql += f" AND namespace IN ({placeholders})"
            params.extend(namespaces)
        sql += " ORDER BY score DESC LIMIT 1"
        return cast(sqlite3.Row | None, self._conn.execute(sql, params).fetchone())

    def all_memory_rows(
        self,
        include_deleted: bool = False,
        namespaces: list[str] | None = None,
    ) -> list[sqlite3.Row]:
        conditions = []
        params: list[object] = []

        if not include_deleted:
            conditions.append("soft_deleted = 0")

        if namespaces is not None:
            if not namespaces:
                # Empty list → no rows can match; short-circuit
                return []
            placeholders = ",".join("?" * len(namespaces))
            conditions.append(f"namespace IN ({placeholders})")
            params.extend(namespaces)

        sql = "SELECT * FROM memories"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        return self._conn.execute(sql, params).fetchall()

    def search_memory_rows(
        self,
        page: int = 1,
        per_page: int = 50,
        query: str = "",
        namespace: str | None = None,
        include_deleted: bool = False,
        filter_preset: str | None = None,
        sort: str = "updated_at",
        sort_dir: str = "desc",
    ) -> tuple[list[sqlite3.Row], int]:
        """Paginated, filtered, sorted memory listing. Returns (rows, total_count)."""
        conditions: list[str] = []
        params: list[object] = []

        if not include_deleted:
            conditions.append("soft_deleted = 0")

        if query:
            conditions.append("(title LIKE ? OR content LIKE ? OR description LIKE ?)")
            like_query = f"%{query}%"
            params.extend([like_query, like_query, like_query])

        if namespace:
            conditions.append("namespace = ?")
            params.append(namespace)

        if filter_preset == "needs_review":
            conditions.append("confidence < 5 AND score < 6")
        elif filter_preset == "high_confidence":
            conditions.append("confidence >= 8 AND score >= 7")
        elif filter_preset == "stale_30d":
            conditions.append("updated_at < datetime('now', '-30 days') AND soft_deleted = 0")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sort_dir_sql = "ASC" if sort_dir.upper() != "DESC" else "DESC"
        allowed_sort_columns = {
            "title", "namespace", "score", "confidence",
            "usage_count", "updated_at", "created_at",
        }
        sort_col = sort if sort in allowed_sort_columns else "updated_at"

        count_sql = f"SELECT COUNT(*) FROM memories{where_clause}"
        total: int = self._conn.execute(count_sql, params).fetchone()[0]

        offset = (page - 1) * per_page
        data_sql = (
            f"SELECT * FROM memories{where_clause}"
            f" ORDER BY {sort_col} {sort_dir_sql} LIMIT ? OFFSET ?"
        )
        return self._conn.execute(data_sql, [*params, per_page, offset]).fetchall(), total

    def get_counts_by_filter(self) -> dict[str, int]:
        """Returns counts for each filter preset."""
        def _count(where: str, params: list[object] | None = None) -> int:
            return self._conn.execute(
                f"SELECT COUNT(*) FROM memories WHERE {where}", params or []
            ).fetchone()[0]

        return {
            "all": _count("1=1"),
            "needs_review": _count("confidence < 5 AND score < 6"),
            "high_confidence": _count("confidence >= 8 AND score >= 7"),
            "stale_30d": _count("updated_at < datetime('now', '-30 days') AND soft_deleted = 0"),
        }

    def get_distinct_namespaces(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT namespace FROM memories WHERE soft_deleted = 0 ORDER BY namespace"
        ).fetchall()
        return [r[0] for r in rows]

    def update_memory_fields(self, id: str, **fields: object) -> None:
        """Update memory fields. `updated_at` is always set to now — passing
        it in the kwargs is ignored (the store owns this timestamp).
        """
        allowed = {
            "score", "usage_count", "soft_deleted",
            "confidence", "confidence_count",
            "title", "description", "content", "last_used",
        }
        cols = {k: v for k, v in fields.items() if k in allowed}
        if not cols:
            return
        cols["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in cols)
        self._conn.execute(
            f"UPDATE memories SET {set_clause} WHERE id = ?",
            (*cols.values(), id),
        )

    def bulk_increment_usage_count(self, ids: list[str]) -> None:
        """Increment usage_count by 1 for all given IDs in a single transaction."""
        if not ids:
            return
        updated_at = _now()
        placeholders = ",".join("?" * len(ids))
        self._conn.execute(
            f"UPDATE memories SET usage_count = usage_count + 1, updated_at = ?"
            f" WHERE id IN ({placeholders})",
            (updated_at, *ids),
        )

    def delete_memory_row(self, id: str) -> None:
        self._conn.execute("DELETE FROM memories WHERE id = ?", (id,))
