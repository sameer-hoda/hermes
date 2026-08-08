import time
import threading
import datetime

from hermes_bot import config
from hermes_bot.cron import cron_store
from hermes_bot.cron.searcher import run_cron_search
from hermes_bot.cron.feedback import mark_awaiting_feedback
from hermes_bot.sender import enqueue_to_mechat

IST = config.IST


class CronScheduler:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[cron] Scheduler started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[cron] Scheduler stopped.")

    def _loop(self):
        cron_store.init_db()
        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"[cron] Error in tick: {e}")
            time.sleep(30)

    def _tick(self):
        jobs = cron_store.get_due_jobs()
        if not jobs:
            return

        active_recently = self._user_active_recently()
        if active_recently:
            return

        for job in jobs:
            try:
                self._execute_job(job)
            except Exception as e:
                print(f"[cron] Failed job {job['id']}: {e}")

    def _execute_job(self, job: dict):
        print(f"[cron] Running: {job['query']} ({job['id']})")

        enqueue_to_mechat(f"🔍 Searching for *{job['query']}*...")

        feedback_text = job.get("feedback", "")
        summary, methodology, groups_scanned, groups_matched = run_cron_search(
            job["query"], feedback_text
        )

        if not summary.strip():
            enqueue_to_mechat(f"No relevant updates found for *{job['query']}*.")
            self._reschedule(job)
            return

        run_id = cron_store.log_run(
            job["id"], summary, methodology, groups_scanned, groups_matched
        )

        cron_store.update_run_feedback(run_id, "")

        enqueue_to_mechat(summary)

        feedback_prompt = self._feedback_prompt(job["id"])
        enqueue_to_mechat(feedback_prompt)

        mark_awaiting_feedback(job["id"])

        self._reschedule(job)

    def _reschedule(self, job: dict):
        frequency = job.get("frequency", "daily")
        time_slot = job.get("time_slot", "09:00")
        next_run = cron_store._compute_next_run(frequency, time_slot)
        cron_store.update_job_next_run(job["id"], next_run)

    def _feedback_prompt(self, job_id: str) -> str:
        return (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👍 *Like this?* Send \"keep\" or /cron keep\n"
            f"👎 *Improve it?* /cron feedback {job_id} \"your feedback\"\n"
            f"⏹ *Stop* /cron pause {job_id}"
        )

    def _user_active_recently(self) -> bool:
        return False


_scheduler = CronScheduler()


def start():
    if config.CRON_ENABLED:
        _scheduler.start()


def stop():
    _scheduler.stop()
