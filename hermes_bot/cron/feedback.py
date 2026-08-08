from hermes_bot.cron import cron_store
from hermes_bot.sender import enqueue_to_mechat


def handle_cron_setup(details: dict) -> str:
    query = details.get("query", "").strip()
    frequency = details.get("frequency", "daily")
    time_slot = details.get("time_slot", "09:00")

    if not query:
        return "What would you like me to summarize? Try: /cron add \"UPI growth\" daily 09:00"

    job_id = cron_store.create_job(query, frequency, time_slot)

    freq_label = {
        "daily": "Daily",
        "weekdays": "Weekdays",
        "weekly": "Weekly",
        "oneshot": "One-shot",
    }.get(frequency, frequency.capitalize())

    return f"✅ *Cron set* · \"{query}\" · {freq_label} {time_slot} IST\nID: `{job_id}`"


def handle_cron_list() -> str:
    jobs = cron_store.get_active_jobs()
    if not jobs:
        return "No active cron jobs. Create one with: /cron add \"topic\" daily 09:00"

    lines = ["📋 *Active Cron Jobs*\n"]
    for j in jobs:
        status_icon = {"active": "🟢", "retry_pending": "🔄", "paused": "⏸", "awaiting_feedback": "👀"}.get(
            j["status"], "•"
        )
        lines.append(
            f"{status_icon} `{j['id']}` · *{j['query']}* · {j['frequency']} {j['time_slot']}"
        )

    lines.append("\n/cron pause <id> · /cron resume <id> · /cron delete <id>")
    return "\n".join(lines)


def handle_cron_manage(action: str, message: str) -> str:
    parts = message.strip().split()
    if len(parts) < 3:
        return f"Usage: /cron {action} <id>"

    job_id = parts[2].strip("`").strip()
    job = cron_store.get_job(job_id)

    if not job:
        return f"No cron job found with ID `{job_id}`"

    if action == "pause":
        cron_store.update_job_status(job_id, "paused")
        return f"⏸ Paused cron `{job_id}` · *{job['query']}*"

    if action == "resume":
        cron_store.update_job_status(job_id, "active")
        return f"▶ Resumed cron `{job_id}` · *{job['query']}*"

    if action == "delete":
        cron_store.update_job_status(job_id, "archived")
        return f"🗑 Deleted cron `{job_id}` · *{job['query']}*"

    return f"Unknown action: {action}"


def handle_feedback(message: str) -> str:
    parts = message.strip().split(maxsplit=2)
    if len(parts) < 3:
        return "Usage: /cron feedback <id> \"your feedback\""

    job_id = parts[1].strip("`").strip()
    feedback_text = parts[2].strip('"').strip()

    job = cron_store.get_job(job_id)
    if not job:
        return f"No cron job found with ID `{job_id}`"

    cron_store.update_job_status(job_id, "retry_pending", feedback_text)

    import datetime
    from hermes_bot.config import IST
    next_run = (datetime.datetime.now(IST) + datetime.timedelta(minutes=2)).isoformat()

    conn = cron_store._connect()
    conn.execute(
        "UPDATE cron_jobs SET next_run_at = ? WHERE id = ?",
        (next_run, job_id),
    )
    conn.commit()
    conn.close()

    return (
        f"✅ *Feedback saved* · Next \"{job['query']}\" summary will adjust.\n"
        f"Retrying in 2 minutes..."
    )


def handle_keep() -> str:
    jobs = cron_store.get_active_jobs()
    awaiting = [j for j in jobs if j["status"] == "awaiting_feedback"]
    if not awaiting:
        return "No pending feedback to confirm. Use /cron list to see your jobs."

    job = awaiting[0]
    cron_store.update_job_status(job["id"], "active")

    import datetime
    from hermes_bot.config import IST

    time_slot = job.get("time_slot", "09:00")
    frequency = job.get("frequency", "daily")
    next_run = cron_store._compute_next_run(frequency, time_slot)

    conn = cron_store._connect()
    conn.execute(
        "UPDATE cron_jobs SET next_run_at = ? WHERE id = ?",
        (next_run, job["id"]),
    )
    conn.commit()
    conn.close()

    return f"👍 *Saved* · \"{job['query']}\" will continue {job['frequency']} at {job['time_slot']} IST"


def mark_awaiting_feedback(job_id: str):
    cron_store.update_job_status(job_id, "awaiting_feedback")
