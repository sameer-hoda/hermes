#!/usr/bin/env python3
"""
Hermes — WhatsApp Personal Assistant
Main entry point. Manages the Go bridge lifecycle and cron scheduler.
"""
import os
import sys
import signal
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hermes_bot import supervisor, config
from hermes_bot.cron import scheduler
from hermes_bot.sender import enqueue_to_mechat, start_flush_thread
from hermes_bot.db import get_mechat_chat_jid, get_own_phone

_running = True


def _shutdown(signum, frame):
    global _running
    print("\n[hermes] Shutting down...")
    _running = False
    scheduler.stop()
    try:
        enqueue_to_mechat("⚠️ *Hermes* · Offline")
    except Exception:
        pass
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if not config.GEMINI_API_KEY:
        print("[hermes] GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print("[hermes] Starting Hermes...")
    print(f"[hermes] Bridge: {config.BRIDGE_URL}")
    print(f"[hermes] Messages DB: {config.MESSAGES_DB}")

    proc = supervisor.start_bridge()

    if not supervisor.launch(proc):
        proc.terminate()
        print("[hermes] Failed to pair bridge. Exiting.")
        sys.exit(1)

    try:
        mechat = get_mechat_chat_jid()
        phone = get_own_phone()
        enqueue_to_mechat(f"🤖 *Hermes* · Ready\nID: `{phone}`\n/help for commands")
    except Exception as e:
        print(f"[hermes] Welcome message failed: {e}")

    scheduler.start()
    start_flush_thread()

    print("[hermes] All systems go. Waiting for messages...\n")

    while _running:
        if proc.poll() is not None:
            print("[hermes] Bridge exited unexpectedly. Restarting...")
            enqueue_to_mechat("⚠️ *Bridge restarted* · Brief interruption")
            proc = supervisor.start_bridge()
            supervisor.launch(proc)
        time.sleep(2)

    proc.terminate()
    proc.wait(timeout=5)


if __name__ == "__main__":
    main()
