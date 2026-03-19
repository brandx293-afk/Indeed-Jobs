"""
core/state.py — Persistent job state manager.

Stores all job data in a local SQLite database that persists via Railway Volume.
Every command reads and writes through this module.

Job statuses:
  pending    — scraped, not yet reviewed
  approved   — user said YES → generate packet + send link
  rejected   — user said NO → never show again
  waiting    — user said WAIT → hold for next review round
  applied    — packet generated, link sent, awaiting submission
  done       — fully submitted

Search criteria (customizable via /run args):
  title_tier  — "manager" | "director" | "executive"
  salary_floor — integer (e.g. 80000)
  base_location — string (e.g. "Sayreville, NJ")
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "data/jobs.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Create tables if they don't exist."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                company     TEXT,
                location    TEXT,
                salary      TEXT,
                level       TEXT,
                industry    TEXT,
                apply_url   TEXT,
                date_posted TEXT,
                status      TEXT DEFAULT 'pending',
                notes       TEXT,
                added_at    TEXT,
                actioned_at TEXT,
                review_round INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS rejected_ids (
                job_id TEXT PRIMARY KEY,
                rejected_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS search_criteria (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Default criteria
        defaults = [
            ("title_tier",     "director"),
            ("salary_floor",   "80000"),
            ("base_location",  "Sayreville, NJ"),
        ]
        for key, val in defaults:
            c.execute(
                "INSERT OR IGNORE INTO search_criteria (key, value) VALUES (?, ?)",
                (key, val)
            )
        c.commit()


def get_criteria() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT key, value FROM search_criteria").fetchall()
    return {k: v for k, v in rows}


def set_criteria(key: str, value: str):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO search_criteria (key, value) VALUES (?, ?)",
            (key, value)
        )
        c.commit()


def is_rejected(job_id: str) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM rejected_ids WHERE job_id = ?", (job_id,)
        ).fetchone()
    return row is not None


def upsert_job(job: dict):
    """Insert a new job or ignore if already exists."""
    with _conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO jobs
            (id, title, company, location, salary, level, industry,
             apply_url, date_posted, status, notes, added_at, review_round)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, 1)
        """, (
            job["id"], job["title"], job["company"], job["location"],
            job.get("salary", "Not Listed"), job.get("level", ""),
            job.get("industry", ""), job.get("apply_url", ""),
            job.get("date_posted", ""), job.get("notes", ""),
            datetime.now().isoformat()
        ))
        c.commit()


def get_pending_jobs() -> list[dict]:
    """Return all jobs with status = 'pending', ordered by level then added_at."""
    with _conn() as c:
        rows = c.execute("""
            SELECT id, title, company, location, salary, level,
                   apply_url, date_posted, notes, review_round
            FROM jobs
            WHERE status = 'pending'
            ORDER BY review_round ASC, added_at DESC
        """).fetchall()
    cols = ["id","title","company","location","salary","level",
            "apply_url","date_posted","notes","review_round"]
    return [dict(zip(cols, r)) for r in rows]


def get_job(job_id: str) -> Optional[dict]:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
    if not row:
        return None
    cols = ["id","title","company","location","salary","level","industry",
            "apply_url","date_posted","status","notes","added_at","actioned_at","review_round"]
    return dict(zip(cols, row))


def get_job_by_number(number: int) -> Optional[dict]:
    """Get a pending job by its display number (1-indexed from pending list)."""
    pending = get_pending_jobs()
    if 1 <= number <= len(pending):
        return pending[number - 1]
    return None


def set_status(job_id: str, status: str):
    with _conn() as c:
        c.execute(
            "UPDATE jobs SET status = ?, actioned_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), job_id)
        )
        c.commit()
    if status == "rejected":
        with _conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO rejected_ids (job_id, rejected_at) VALUES (?, ?)",
                (job_id, datetime.now().isoformat())
            )
            c.commit()


def set_wait(job_id: str):
    """Keep job pending but increment review_round so it shows last next time."""
    with _conn() as c:
        c.execute(
            "UPDATE jobs SET review_round = review_round + 1, actioned_at = ? WHERE id = ?",
            (datetime.now().isoformat(), job_id)
        )
        c.commit()


def get_all_stats() -> dict:
    """Return counts by status for the /status command."""
    with _conn() as c:
        rows = c.execute(
            "SELECT status, COUNT(*) FROM jobs GROUP BY status"
        ).fetchall()
        total_rejected = c.execute(
            "SELECT COUNT(*) FROM rejected_ids"
        ).fetchone()[0]
    stats = {r[0]: r[1] for r in rows}
    stats["never_show_again"] = total_rejected
    return stats


def get_jobs_by_status(status: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("""
            SELECT id, title, company, location, salary, level, apply_url, date_posted
            FROM jobs WHERE status = ?
            ORDER BY actioned_at DESC
        """, (status,)).fetchall()
    cols = ["id","title","company","location","salary","level","apply_url","date_posted"]
    return [dict(zip(cols, r)) for r in rows]
