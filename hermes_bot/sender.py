import time
import json
import threading
from pathlib import Path

from hermes_bot import config

_pending_file = Path(config.STORE_DIR) / "pending_messages.json"


def _read_pending() -> list[dict]:
    if not _pending_file.exists():
        return []
    try:
        return json.loads(_pending_file.read_text())
    except (json.JSONDecodeError, Exception):
        return []


def _write_pending(messages: list[dict]):
    _pending_file.parent.mkdir(parents=True, exist_ok=True)
    _pending_file.write_text(json.dumps(messages))


def enqueue_message(jid: str, text: str):
    messages = _read_pending()
    messages.append({"jid": jid, "text": text, "queued_at": time.time()})
    _write_pending(messages)


def enqueue_to_mechat(text: str):
    from hermes_bot.db import get_mechat_chat_jid
    enqueue_message(get_mechat_chat_jid(), text)


def flush_pending():
    import requests
    messages = _read_pending()
    if not messages:
        return

    url = f"{config.BRIDGE_URL}/api/send"
    sent = []

    for msg in messages:
        try:
            resp = requests.post(
                url,
                json={"recipient": msg["jid"], "message": msg["text"]},
                timeout=15,
            )
            if resp.status_code == 200 and resp.json().get("success"):
                sent.append(msg)
        except Exception:
            pass

    remaining = [m for m in messages if m not in sent]
    _write_pending(remaining)

    if sent:
        print(f"[sender] Flushed {len(sent)} pending message(s)")


def _flush_loop():
    while True:
        time.sleep(2)
        try:
            flush_pending()
        except Exception:
            pass


_flush_thread = None


def start_flush_thread():
    global _flush_thread
    if _flush_thread and _flush_thread.is_alive():
        return
    _flush_thread = threading.Thread(target=_flush_loop, daemon=True)
    _flush_thread.start()
    print("[sender] Flush thread started.")