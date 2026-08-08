#!/usr/bin/env python3
import os
import sys
import signal
import threading
import time
import json
from pathlib import Path

from hermes_bot import supervisor, config
from hermes_bot.cron import scheduler
from hermes_bot.sender import enqueue_to_mechat, start_flush_thread
from hermes_bot.db import get_mechat_chat_jid, get_own_phone

_running = True


def _drain_bridge_output(proc):
    def _run():
        try:
            for line in iter(proc.stdout.readline, ""):
                stripped = line.rstrip()
                if stripped:
                    print(f"[bridge] {stripped}", flush=True)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


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


def _read_setup_state() -> str:
    path = Path(config.SETUP_FILE)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get("state", "")
        except Exception:
            pass
    return ""


def main():
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[hermes] Starting Hermes...")
    print(f"[hermes] Bridge URL: {config.BRIDGE_URL}")
    print(f"[hermes] Messages DB: {config.MESSAGES_DB}")
    print(f"[hermes] Store Dir: {config.STORE_DIR}")

    proc = supervisor.start_bridge()
    _drain_bridge_output(proc)

    if not supervisor.wait_for_readiness(timeout=180):
        proc.terminate()
        print("[hermes] Bridge failed to start. Exiting.")
        sys.exit(1)

    print("[hermes] Bridge ready. Starting services...")
    start_flush_thread()
    scheduler.start()

    was_ready = False
    print("[hermes] All systems go. Waiting for setup to complete...\n")

    while _running:
        if proc.poll() is not None:
            print("[hermes] Bridge exited. Restarting...")
            time.sleep(2)
            proc = supervisor.start_bridge()
            _drain_bridge_output(proc)
            supervisor.wait_for_readiness(timeout=60)
            continue

        state = _read_setup_state()
        
        if state == "READY" and not was_ready:
            was_ready = True
            print("[hermes] Setup complete! Hermes is READY.")
            try:
                mechat = get_mechat_chat_jid()
                phone = get_own_phone()
                enqueue_to_mechat(f"🤖 *Hermes* · Ready\nID: `{phone}`\n/help for commands")
            except Exception as e:
                print(f"[hermes] Welcome message failed: {e}")
        
        elif state == "RESETTING":
            print("[hermes] Reset in progress, waiting for restart...")
        
        time.sleep(2)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()