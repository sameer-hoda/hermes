import sqlite3
import uuid
import datetime
from typing import Optional

from hermes_bot import config

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _now() -> str:
    return datetime.datetime.now(IST).isoformat()


def _connect():
    conn = sqlite3.connect(config.HERMES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cron_jobs (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            frequency TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            scope TEXT DEFAULT 'all',
            status TEXT DEFAULT 'active',
            feedback TEXT,
            feedback_iteration INTEGER DEFAULT 0,
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cron_run_log (
            id TEXT PRIMARY KEY,
            cron_job_id TEXT NOT NULL,
            run_at TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            methodology TEXT,
            groups_scanned INTEGER,
            groups_matched INTEGER,
            user_rating TEXT,
            user_feedback TEXT,
            FOREIGN KEY (cron_job_id) REFERENCES cron_jobs(id)
        );
    """)
    conn.commit()
    conn.close()


def create_job(
    query: str,
    frequency: str,
    time_slot: str,
    scope: str = "all",
) -> str:
    job_id = str(uuid.uuid4())[:8]
    now = _now()

    next_run = _compute_next_run(frequency, time_slot)

    conn = _connect()
    conn.execute(
        """
        INSERT INTO cron_jobs (id, query, frequency, time_slot, scope, status,
                               next_run_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
        """,
        (job_id, query, frequency, time_slot, scope, next_run, now, now),
    )
    conn.commit()
    conn.close()
    return job_id


def get_due_jobs() -> list[dict]:
    now = _now()
    conn = _connect()
    rows = conn.execute(
        """
        SELECT * FROM cron_jobs
        WHERE status IN ('active', 'retry_pending')
          AND next_run_at <= ?
        ORDER BY next_run_at ASC
        """,
        (now,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_jobs() -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        """
        SELECT * FROM cron_jobs
        WHERE status != 'archived'
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job(job_id: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM cron_jobs WHERE id = ?", (job_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_job_status(job_id: str, status: str, feedback: str = ""):
    now = _now()
    conn = _connect()
    if feedback:
        conn.execute(
            """
            UPDATE cron_jobs
            SET status = ?, feedback = ?, feedback_iteration = feedback_iteration + 1,
                updated_at = ?
            WHERE id = ?
            """,
            (status, feedback, now, job_id),
        )
    else:
        conn.execute(
            "UPDATE cron_jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, job_id),
        )
    conn.commit()
    conn.close()


def update_job_next_run(job_id: str, next_run_at: str):
    now = _now()
    conn = _connect()
    conn.execute(
        "UPDATE cron_jobs SET last_run_at = ?, next_run_at = ?, updated_at = ? WHERE id = ?",
        (_now(), next_run_at, now, job_id),
    )
    conn.commit()
    conn.close()


def log_run(
    cron_job_id: str,
    summary_text: str,
    methodology: str,
    groups_scanned: int,
    groups_matched: int,
) -> str:
    run_id = str(uuid.uuid4())[:8]
    conn = _connect()
    conn.execute(
        """
        INSERT INTO cron_run_log (id, cron_job_id, run_at, summary_text, methodology,
                                  groups_scanned, groups_matched)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, cron_job_id, _now(), summary_text, methodology, groups_scanned, groups_matched),
    )
    conn.commit()
    conn.close()
    return run_id


def update_run_feedback(run_id: str, rating: str, feedback: str = ""):
    conn = _connect()
    conn.execute(
        "UPDATE cron_run_log SET user_rating = ?, user_feedback = ? WHERE id = ?",
        (rating, feedback, run_id),
    )
    conn.commit()
    conn.close()


def get_last_run_for_job(cron_job_id: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute(
        """
        SELECT * FROM cron_run_log
        WHERE cron_job_id = ?
        ORDER BY run_at DESC LIMIT 1
        """,
        (cron_job_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _compute_next_run(frequency: str, time_slot: str) -> str:
    now = datetime.datetime.now(IST)
    try:
        hour, minute = map(int, time_slot.split(":"))
    except (ValueError, AttributeError):
        hour, minute = 9, 0

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if target <= now:
        target += datetime.timedelta(days=1)

    if frequency == "weekdays":
        while target.weekday() >= 5:
            target += datetime.timedelta(days=1)
    elif frequency.startswith("weekly:"):
        day_name = frequency.split(":")[1].lower()
        day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                     "friday": 4, "saturday": 5, "sunday": 6}
        target_day = day_map.get(day_name, 0)
        while target.weekday() != target_day:
            target += datetime.timedelta(days=1)

    return target.isoformat()
