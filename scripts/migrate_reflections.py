"""
One-time migration: backfill Reflection records from loop/run_log.jsonl
and enrich Session records from loop/sessions/*.md frontmatter.

Strategy:
  - 1 Reflection per run_log.jsonl entry
  - Reflection ID = uuid5(NAMESPACE_URL, completed_at) → idempotent re-runs
  - Substantive sessions (non-stub topics) matched to reflections by topic slug
  - Stub sessions (short-session / housekeeping) matched to the last reflection
    whose completed_at is on or before the stub's date
"""
import json
import os
import re
import sqlite3
import sys
import uuid
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_DIR  = Path(__file__).resolve().parent.parent
SESSIONS_DIR = PROJECT_DIR / "loop" / "sessions"
RUN_LOG      = PROJECT_DIR / "loop" / "run_log.jsonl"

DATA_DIR = Path(os.environ.get("LORE_DATA_DIR", str(Path.home() / ".lorekeeper")))
DB_PATH  = DATA_DIR / "lorekeeper.db"

REFLECTION_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace


# ── Helpers ───────────────────────────────────────────────────────────────────

def deterministic_id(completed_at: str) -> str:
    return str(uuid.uuid5(REFLECTION_NAMESPACE, f"reflect:{completed_at}"))


def is_valid_uuid(s: str) -> bool:
    return len(s) == 36 and s.count("-") == 4


def parse_session_log(path: Path) -> dict | None:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not m:
        return None
    fm_raw, body = m.group(1), m.group(2)

    fm: dict = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()

    def extract_bullets(section_name: str) -> list[str]:
        pat = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        sm  = re.search(pat, body, re.DOTALL | re.IGNORECASE)
        if not sm:
            return []
        result = []
        for line in sm.group(1).strip().splitlines():
            s = line.strip()
            if not s or s.startswith("(stub"):
                continue
            if s.startswith("-"):
                content = s.lstrip("-").strip()
                if content and content not in ("none noted", "none"):
                    result.append(content)
        return result

    def extract_text(section_name: str) -> str | None:
        """Return the raw section text (not split into bullets)."""
        pat = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        sm  = re.search(pat, body, re.DOTALL | re.IGNORECASE)
        if not sm:
            return None
        text = sm.group(1).strip()
        if not text or text.startswith("(stub"):
            return None
        return text

    return {
        "session_id":    fm.get("session_id", ""),
        "date":          fm.get("date", ""),
        "topic":         fm.get("topic", ""),
        "task_type":     fm.get("task_type", ""),
        "transcript":    fm.get("transcript", ""),
        "is_stub":       fm.get("topic", "") in ("short-session", "housekeeping"),
        "lessons":       extract_bullets("Lessons learnt"),
        "good_patterns": extract_bullets("Good patterns observed"),
        "user_profile":  extract_bullets("What I learned about the user"),
        "discoveries":   (
            extract_bullets("Corrections / discoveries")
            + extract_bullets("Decisions made")
        ),
        # Raw text fields for the sessions content columns
        "what_was_done": extract_text("What was done"),
        "decisions_text":extract_text("Decisions made"),
        "lessons_text":  extract_text("Lessons learnt"),
        "patterns_text": extract_text("Good patterns observed"),
        "profile_text":  extract_text("What I learned about the user"),
        "discover_text": extract_text("Corrections / discoveries"),
    }


def bullets(items: list[str]) -> str | None:
    clean = [i for i in items if i]
    return "\n".join(f"- {i}" for i in clean) if clean else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    if not RUN_LOG.exists():
        print(f"ERROR: run_log.jsonl not found at {RUN_LOG}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # ── Parse all session logs ─────────────────────────────────────────────────
    topic_map: dict[str, dict]  = {}  # topic slug → info  (non-stubs)
    stub_sessions: list[dict]   = []  # stubs with valid UUIDs, sorted by date+filename
    all_by_uuid: dict[str, dict] = {}  # session_id → info (all)

    for f in sorted(SESSIONS_DIR.glob("*.md")):
        info = parse_session_log(f)
        if not info:
            continue
        sid = info["session_id"]
        if is_valid_uuid(sid):
            all_by_uuid[sid] = info
            if info["is_stub"]:
                stub_sessions.append(info)
            else:
                topic_map[info["topic"]] = info

    print(f"Parsed {len(topic_map)} substantive session logs")
    print(f"Parsed {len(stub_sessions)} stub session logs with valid UUIDs")

    # ── Parse run_log.jsonl ────────────────────────────────────────────────────
    runs: list[dict] = []
    for line in RUN_LOG.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    print(f"Found {len(runs)} runs in run_log.jsonl")

    # ── Build reflections, match sessions → reflections ───────────────────────
    # For stub assignment: last reflection whose date (YYYY-MM-DD) <= stub date
    # Sort runs by completed_at so we can do a last-match scan
    runs_sorted = sorted(runs, key=lambda r: r.get("completed_at", ""))
    run_date_map: list[tuple[str, str]] = [
        (r["completed_at"][:10], deterministic_id(r["completed_at"]))
        for r in runs_sorted
    ]  # (YYYY-MM-DD, reflection_id) sorted ascending

    def find_reflection_for_date(date_str: str) -> str | None:
        """Last reflection whose run date <= date_str."""
        result = None
        for run_date, ref_id in run_date_map:
            if run_date <= date_str:
                result = ref_id
        return result

    reflections_inserted = 0
    sessions_enriched    = 0

    for run in runs_sorted:
        completed_at  = run.get("completed_at", "")
        new_logs      = run.get("new_logs", [])
        stubs_count   = run.get("stubs", 0)
        skipped       = run.get("skipped", 0)
        lore_inserted = run.get("lore_inserted", [])
        lore_updated  = run.get("lore_updated", [])

        reflection_id = deterministic_id(completed_at)
        session_count = len(new_logs) + stubs_count

        # Aggregate content from matched substantive session logs
        all_lessons      : list[str] = []
        all_patterns     : list[str] = []
        all_user_profile : list[str] = []
        all_discoveries  : list[str] = []
        matched_sessions : list[dict] = []

        for topic in new_logs:
            if topic in topic_map:
                info = topic_map[topic]
                all_lessons      += info["lessons"]
                all_patterns     += info["good_patterns"]
                all_user_profile += info["user_profile"]
                all_discoveries  += info["discoveries"]
                matched_sessions.append(info)

        # Build summary
        topic_list  = ", ".join(new_logs) if new_logs else "unknown topics"
        mem_titles  = [m["title"] for m in lore_inserted[:3]]
        mem_snippet = "; ".join(mem_titles)
        summary = (
            f"Processed {session_count} session(s): {topic_list}."
            + (f" Inserted: {mem_snippet}." if mem_snippet else "")
            + (f" {skipped} skipped." if skipped else "")
        )[:400]

        memory_ids = [m["id"] for m in lore_inserted] + [m["id"] for m in lore_updated]

        # Insert reflection (idempotent)
        existing = conn.execute(
            "SELECT id FROM reflections WHERE id = ?", (reflection_id,)
        ).fetchone()

        if existing:
            print(f"  SKIP  {reflection_id[:8]}… (already exists)")
        else:
            conn.execute(
                """
                INSERT INTO reflections
                  (id, created_at, session_count, lessons_learnt, good_patterns,
                   user_profile_updates, factual_discoveries, summary, memory_ids)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    reflection_id, completed_at, session_count,
                    bullets(all_lessons) or "",
                    bullets(all_patterns),
                    bullets(all_user_profile),
                    bullets(all_discoveries),
                    summary,
                    json.dumps(memory_ids) if memory_ids else None,
                ),
            )
            reflections_inserted += 1
            f"{completed_at}, {session_count} sessions, {len(matched_sessions)} substantive logs)"

        # Link substantive session records
        for info in matched_sessions:
            sid = info["session_id"]
            if not is_valid_uuid(sid):
                continue
            row = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (sid,),
            ).fetchone()
            if row:
                conn.execute(
                    """UPDATE sessions SET
                         session_date   = COALESCE(session_date, ?),
                         topic          = COALESCE(topic, ?),
                         task_type      = COALESCE(task_type, ?),
                         reflection_id  = COALESCE(reflection_id, ?),
                         transcript     = COALESCE(transcript, ?),
                         what_was_done  = COALESCE(what_was_done, ?),
                         decisions      = COALESCE(decisions, ?),
                         lessons_learnt = COALESCE(lessons_learnt, ?),
                         good_patterns  = COALESCE(good_patterns, ?),
                         user_profile   = COALESCE(user_profile, ?),
                         discoveries    = COALESCE(discoveries, ?)
                       WHERE session_id = ?""",
                    (info["date"], info["topic"], info["task_type"], reflection_id,
                     info["transcript"], info["what_was_done"], info["decisions_text"],
                     info["lessons_text"], info["patterns_text"], info["profile_text"],
                     info["discover_text"], sid),
                )
            else:
                conn.execute(
                    """INSERT OR IGNORE INTO sessions
                         (session_id, session_date, topic, task_type, reviewed_at, reflection_id,
                          transcript, what_was_done, decisions, lessons_learnt,
                          good_patterns, user_profile, discoveries)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (sid, info["date"], info["topic"], info["task_type"],
                     completed_at, reflection_id,
                     info["transcript"], info["what_was_done"], info["decisions_text"],
                     info["lessons_text"], info["patterns_text"], info["profile_text"],
                     info["discover_text"]),
                )
                print(f"    INSERTED missing session {sid[:8]}… ({info['topic']})")
            sessions_enriched += 1

    conn.commit()

    # ── Assign stub sessions to reflections by date ────────────────────────────
    print()
    print("Assigning stub sessions…")
    for info in stub_sessions:
        sid = info["session_id"]
        row = conn.execute(
            "SELECT session_id, reflection_id FROM sessions WHERE session_id = ?",
            (sid,),
        ).fetchone()
        if row and row["reflection_id"]:
            continue  # already linked

        ref_id = find_reflection_for_date(info["date"])
        if not ref_id:
            continue

        if row:
            conn.execute(
                """UPDATE sessions SET
                     session_date  = COALESCE(session_date, ?),
                     topic         = COALESCE(topic, ?),
                     task_type     = COALESCE(task_type, ?),
                     reflection_id = COALESCE(reflection_id, ?)
                   WHERE session_id = ?""",
                (info["date"], info["topic"] or "short-session",
                 info["task_type"] or "build", ref_id, sid),
            )
        else:
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                     (session_id, session_date, topic, task_type, reviewed_at, reflection_id)
                   VALUES (?,?,?,?,?,?)""",
                (sid, info["date"], info["topic"] or "short-session", info["task_type"] or "build",
                 info["date"] + "T00:00:00Z", ref_id),
            )
        sessions_enriched += 1
        print(f"  stub {sid[:8]}… ({info['date']}) → reflection {ref_id[:8]}…")

    conn.commit()

    # ── Insert or enrich any remaining sessions from markdown files ──────────
    # Covers sessions whose topics never appeared in run_log.jsonl new_logs.
    for sid, info in all_by_uuid.items():
        if info["is_stub"]:
            continue
        row = conn.execute(
            "SELECT session_id, topic FROM sessions WHERE session_id = ?",
            (sid,),
        ).fetchone()
        content_args = (
            info["transcript"], info["what_was_done"], info["decisions_text"],
            info["lessons_text"], info["patterns_text"], info["profile_text"],
            info["discover_text"],
        )
        if row:
            if not row["topic"]:
                conn.execute(
                    """UPDATE sessions SET
                         session_date   = COALESCE(session_date, ?),
                         topic          = COALESCE(topic, ?),
                         task_type      = COALESCE(task_type, ?),
                         transcript     = COALESCE(transcript, ?),
                         what_was_done  = COALESCE(what_was_done, ?),
                         decisions      = COALESCE(decisions, ?),
                         lessons_learnt = COALESCE(lessons_learnt, ?),
                         good_patterns  = COALESCE(good_patterns, ?),
                         user_profile   = COALESCE(user_profile, ?),
                         discoveries    = COALESCE(discoveries, ?)
                       WHERE session_id = ?""",
                    (info["date"], info["topic"], info["task_type"], *content_args, sid),
                )
                sessions_enriched += 1
        else:
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                     (session_id, session_date, topic, task_type, reviewed_at,
                      transcript, what_was_done, decisions, lessons_learnt,
                      good_patterns, user_profile, discoveries)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (sid, info["date"], info["topic"], info["task_type"], info["date"] + "T00:00:00Z",
                 *content_args),
            )
            print(f"  INSERT orphan session {sid[:8]}… ({info['topic']})")
            sessions_enriched += 1

    conn.commit()
    conn.close()

    print()
    print(
        f"Done: {reflections_inserted} reflections inserted,"
        f" {sessions_enriched} sessions enriched"
    )


if __name__ == "__main__":
    main()
