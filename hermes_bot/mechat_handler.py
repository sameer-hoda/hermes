#!/usr/bin/env python3
"""
Invoked by the Go bridge when a MeChat message arrives from the owner.

Usage: python3 mechat_handler.py <chat_jid> <sender_jid> <message_text>
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_bot.assistant.session import SessionManager
from hermes_bot.assistant.continuity import check_continuity
from hermes_bot.assistant.responder import route_intent
from hermes_bot.sender import enqueue_to_mechat
from hermes_bot.db import is_message_from_owner


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[hermes {ts}] {msg}", flush=True)


def main():
    if len(sys.argv) < 4:
        _log("ERROR: missing args")
        sys.exit(1)

    chat_jid = sys.argv[1]
    sender_jid = sys.argv[2]
    message_text = " ".join(sys.argv[3:])

    _log(f"INVOKED chat={chat_jid} sender={sender_jid} msg=\"{message_text[:60]}\"")

    if not message_text.strip():
        _log("SKIP: empty message")
        return

    if message_text.strip().startswith("/"):
        _log("SKIP: slash command (bridge handles these)")
        return

    _log("Checking owner...")
    if not is_message_from_owner(chat_jid, sender_jid):
        _log("SKIP: not owner")
        return
    _log("Owner check passed")

    # Immediate ack so the user is never left wondering — deep-dive replies
    # can take minutes; progress updates follow as the pipeline advances.
    enqueue_to_mechat("⚡ *On it* — figuring out what you need…")

    _log("Loading session...")
    session_mgr = SessionManager()
    session = session_mgr.get_active_session()
    if session:
        _log(f"Active session: id={session.session_id} topic=\"{session.topic[:40]}\" state={session.state}")
    else:
        _log("No active session")

    if session and session.state == "awaiting_continuity_confirm":
        msg_lower = message_text.strip().lower()
        _log(f"Awaiting confirm, user said: \"{message_text[:40]}\"")
        if msg_lower in ("yes", "yeah", "y", "continue", "sure", "ok", "okay"):
            _log("User confirmed, continuing session")
            session_mgr.clear_pending_confirmation(session)
            session.touch()
            session.add_message(message_text)
            session_mgr.update_session(session)
            reply = route_intent(session, message_text, progress=_progress)
            _log(f"Reply generated: \"{reply[:80]}...\"")
            _send_reply(reply)
            return
        elif msg_lower in ("no", "n", "nope", "new", "fresh", "start over", "restart"):
            _log("User wants new session")
            session_mgr.close_session(session)
            session = session_mgr.create_session(message_text)
            reply = route_intent(session, message_text, progress=_progress)
            _log(f"Reply generated: \"{reply[:80]}...\"")
            _send_reply(reply)
            return
        else:
            _log("Ambiguous response to confirm, proceeding")
            session_mgr.clear_pending_confirmation(session)
            session.touch()
            session.add_message(message_text)
            session_mgr.update_session(session)

    if session:
        _log("Running continuity check...")
        result = check_continuity(session, message_text)
        _log(f"Continuity: continues={result.continues} confidence={result.confidence:.2f}")

        if not result.continues:
            _log(f"New topic: \"{result.new_topic}\"")
            session_mgr.close_session(session)
            session = session_mgr.create_session(message_text)
            reply = route_intent(session, message_text, progress=_progress)
            _log(f"Reply generated: \"{reply[:80]}...\"")
            _send_reply(reply)
            return

        if result.confidence < 0.7:
            _log("Low confidence, asking user to confirm")
            session_mgr.set_awaiting_confirmation(session)
            enqueue_to_mechat(
                f"We were chatting about *{session.topic[:60]}*.\n"
                f"Continue that or start fresh? (yes/no)"
            )
            session.add_message(message_text)
            session_mgr.update_session(session)
            return

        _log("Continuing existing session")
        session.touch()
        session.add_message(message_text)
        session_mgr.update_session(session)
    else:
        _log("Creating new session")
        session = session_mgr.create_session(message_text)

    _log("Routing intent...")
    reply = route_intent(session, message_text, progress=_progress)
    _log(f"Reply generated: \"{reply[:100]}...\"")

    _log("Sending reply via bridge API...")
    _send_reply(reply)
    _log("DONE — reply sent, handler exiting")


def _send_reply(text: str):
    _log(f"Enqueueing {len(text)} chars to pending_messages.json")
    enqueue_to_mechat(text)
    _log("Enqueued")


def _progress(msg: str):
    _log(f"Progress: {msg}")
    enqueue_to_mechat(msg)


if __name__ == "__main__":
    main()