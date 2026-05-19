# Plan: Export / Import (Backup) via Dashboard

## Context

Lorekeeper has no way to back up memories or share them across instances. The user wants a **Backup tab** in the dashboard where they can:
1. **Export** — download all memories + links as a portable JSON file
2. **Import** — upload a JSON file, see a preview of what will be inserted vs skipped (by ID), then confirm

No MCP tools needed. This is a pure dashboard REST API + UI feature.

---

## JSON Format

```json
{
  "version": "2",
  "exported_at": "2026-05-19T...",
  "memories": [
    {
      "id": "uuid", "title": "...", "description": "...", "content": "...",
      "created_at": "...", "updated_at": "...",
      "usage_count": 5, "score": 7.2, "soft_deleted": false,
      "confidence": 8.0, "confidence_count": 12
    }
  ],
  "links": [
    {
      "id": "uuid", "source_memory_id": "...", "target_memory_id": "...",
      "relation_type": "related_to", "reason": "...",
      "score": 1.0, "created_at": "...", "updated_at": "...",
      "usage_count": 2, "confidence": null, "confidence_count": 0
    }
  ]
}
```

Export includes soft-deleted memories only when the user checks "Include soft-deleted" (**default = unchecked / false**). The `soft_deleted` flag is preserved on import.

> **Note on vectors**: Chroma embeddings are NOT exported. On import, each memory is re-embedded via `engine.add()`. Large imports (thousands of memories) will be slow.

---

## Files to Change

| File | Change |
|------|--------|
| `src/lorekeeper/services/link_store.py` | Extend `insert_link()` with optional `id` + metadata params |
| `src/lorekeeper/services/orchestrator.py` | Add `import_dump(dry_run=)` method |
| `src/lorekeeper/dashboard/app.py` | Add 3 routes: GET `/api/export`, POST `/api/import/preview`, POST `/api/import/confirm` |
| `src/lorekeeper/dashboard/static/index.html` | Add Backup tab button + pane |
| `src/lorekeeper/dashboard/static/js/backup.js` | New file — backup tab logic |
| `src/lorekeeper/dashboard/static/js/app.js` | Import + wire backup.js |

---

## Step-by-Step Implementation

### 1. `link_store.py` — extend `insert_link()` with optional `id`

The existing `insert_link()` always generates a new UUID. Extend it to accept an optional `id` parameter — if provided, use it; otherwise generate one as before. No new method needed.

```python
def insert_link(
    self,
    source_memory_id: str,
    target_memory_id: str,
    relation_type: str,
    reason: str,
    score: float = 1.0,
    id: str | None = None,           # new optional param
    created_at: str | None = None,   # new optional param
    updated_at: str | None = None,   # new optional param
    usage_count: int = 0,            # new optional param
    confidence: float | None = None, # new optional param
    confidence_count: int = 0,       # new optional param
) -> MemoryLink:
    now = _now()
    link = MemoryLink(
        id=id or str(uuid.uuid4()),   # preserve original ID if given
        ...
    )
```

All existing callers continue to work unchanged (all new params have defaults).

---

### 2. `orchestrator.py` — add `import_dump()`

```python
def import_dump(
    self,
    memories: list[dict],
    links: list[dict],
    dry_run: bool = False,
) -> dict:
    # Returns:
    # {
    #   memories_inserted, memories_skipped,
    #   links_inserted, links_skipped, links_error,
    #   errors: list[str]
    # }
```

**Memory logic** (per entry):
- Check `store.get_memory_row(id)` — if row exists → `memories_skipped += 1`, continue
- If `dry_run=False`: call `engine.add(f"{title} {description} {content}", lore_id)` then `store.upsert_memory_row(...)` with ALL fields from the JSON (preserving original timestamps, score, soft_deleted, confidence, etc.)
- After all memories: `_rebuild_kw()` (skip if dry_run)

**Link logic** (per entry):
- Check `store.get_link(id)` — if exists → `links_skipped += 1`, continue
- Check both FK memories exist in SQLite (using the set of existing + newly imported IDs) — if broken → `links_error += 1`, continue
- If `dry_run=False`: `store.insert_link(id=id, ...)` preserving original fields (using extended signature)

---

### 3. `app.py` — 3 new routes

Add `from fastapi import File, UploadFile` and `from fastapi.responses import Response`.

**`GET /api/export`** — file download
```python
@app.get("/api/export")
def export_dump(include_deleted: bool = False) -> Response:
    store = get_service()._store
    memories = [dict(r) for r in store.all_memory_rows(include_deleted=include_deleted)]
    # Convert soft_deleted int → bool for portability
    for m in memories:
        m["soft_deleted"] = bool(m["soft_deleted"])
    links = [lnk.model_dump() for lnk in store.all_links()]
    payload = {
        "version": "2",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "memories": memories,
        "links": links,
    }
    filename = f"lorekeeper-{datetime.now().strftime('%Y-%m-%d')}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

**`POST /api/import/preview`** — dry run
```python
@app.post("/api/import/preview")
async def import_preview(file: UploadFile = File(...)) -> dict:
    data = json.loads(await file.read())
    return get_service().import_dump(data["memories"], data["links"], dry_run=True)
```

**`POST /api/import/confirm`** — actual import
```python
@app.post("/api/import/confirm")
async def import_confirm(file: UploadFile = File(...)) -> dict:
    data = json.loads(await file.read())
    return get_service().import_dump(data["memories"], data["links"], dry_run=False)
```

---

### 4. `index.html` — Backup tab

Add tab button after Config:
```html
<button class="tab" onclick="switchTab('backup')">Backup</button>
```

Add tab pane `#tab-backup` with two sections:

**Export section:**
```
[Export All Memories ↓]   ☐ Include soft-deleted  (default: unchecked)
```

**Import section:**
```
Browse file…  [Choose file button]
→ (after file chosen, preview auto-loads)

Preview:
  Memories:  42 to insert  |  5 to skip (already exist)
  Links:     18 to insert  |  2 to skip (already exist)  |  1 skip (broken FK)

[Import N memories, M links]   (disabled until preview loaded)
```

Preview and confirm button are in the same pane — no page navigation.

---

### 5. `backup.js` — new module

```javascript
export function initBackup() { /* set up file input change listener */ }
export function triggerExport() {
  // GET /api/export?include_deleted=X
  // Use <a download> approach to trigger browser download
}
async function loadPreview(file) {
  // POST FormData to /api/import/preview
  // Render preview stats into #backup-preview
  // Enable confirm button, stash file ref
}
export async function confirmImport() {
  // POST same file FormData to /api/import/confirm
  // Show toast with result counts
  // Reset UI
}
```

File upload uses `FormData` (not the `api()` JSON helper — needs special handling for multipart).

---

### 6. `app.js` — wire backup tab

```javascript
import { initBackup } from './backup.js';
// in registerTabCallbacks: onTabBackup: () => {} (init is called once at startup)
// in init(): initBackup();
```

---

## Dedup / Skip Logic Summary

| Case | Behaviour |
|------|-----------|
| Memory ID already in SQLite | Skip (count as `memories_skipped`) |
| Memory ID new | Insert into SQLite + Mem0 |
| Link ID already in `memory_links` | Skip (count as `links_skipped`) |
| Link FK references missing memory | Skip (count as `links_error`) |
| Link ID new, FKs valid | Insert |

Soft-deleted flag is preserved as-is from the JSON on import. No forced restore.

---

## Verification

1. `uv run pytest` — existing tests still pass
2. Open dashboard → Backup tab → click Export → JSON file downloads
3. Upload the same file → preview: all memories/links shown as "skip (already exist)"
4. Delete a few memories, upload same file → preview shows those IDs as "to insert"
5. Confirm import → memories restored, toast shows counts
6. `GET /api/memories` returns restored memories
