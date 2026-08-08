import json

from google import genai

from hermes_bot import config
from hermes_bot.assistant.session import Session

RESPONDER_PROMPT = """You are Hermes, a concise personal assistant on WhatsApp.
Respond to the user's message directly and helpfully.

User message: "{message}"

Rules:
- Be brief. 2-4 short paragraphs max. No fluff.
- Use WhatsApp markdown: *bold* for key terms, _italic_ for emphasis.
- If the user asks a factual question, answer it directly.
- If the user shares info, acknowledge and offer relevant next steps.
- If you don't know something, say so honestly.
- Never make up facts.

Your response (plain text, no JSON):"""


def respond_freeform(session: Session, message: str) -> str:
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = RESPONDER_PROMPT.format(message=message)

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_FAST,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[responder] Error: {e}")
        return "Got it. What would you like me to help with?"


HELP_TEXT = """🤖 *Hermes* · Your WhatsApp Assistant

*What I can do:*
• Chat with you naturally in this chat
• /ask <topic> — search all groups for updates
• /cron add "<query>" daily 09:00 — schedule summaries
• /cron list — see your scheduled summaries
• /sotu — State of the Union (in any group)
• /pending — pending items (in any group)

*I understand context* — I remember what we're chatting about within a session. Just talk normally.

Need something specific? Just ask."""


GREETINGS = [
    "Hey! What can I help with?",
    "Hi there. What's on your mind?",
    "Hello! Ready to help. What do you need?",
]


def route_intent(session: Session, message: str) -> str:
    msg_lower = message.strip().lower()

    if msg_lower in ("/help", "help", "what can you do"):
        return HELP_TEXT

    if msg_lower in ("hi", "hello", "hey", "yo", "sup"):
        import random
        return random.choice(GREETINGS)

    from hermes_bot.assistant.handler import detect_intent

    intent = detect_intent(session, message)

    if intent.intent == "ask":
        from hermes_bot.cron.searcher import run_one_shot_search
        return run_one_shot_search(intent.query or message)

    if intent.intent == "cron_setup":
        from hermes_bot.cron.feedback import handle_cron_setup
        return handle_cron_setup(intent.cron_details)

    if intent.intent == "cron_list":
        from hermes_bot.cron.feedback import handle_cron_list
        return handle_cron_list()

    if intent.intent in ("cron_pause", "cron_resume", "cron_delete"):
        from hermes_bot.cron.feedback import handle_cron_manage
        return handle_cron_manage(intent.intent.replace("cron_", ""), message)

    if intent.intent == "cron_feedback":
        from hermes_bot.cron.feedback import handle_feedback
        return handle_feedback(message)

    if intent.intent == "cron_keep":
        from hermes_bot.cron.feedback import handle_keep
        return handle_keep()

    if intent.intent in ("question", "unknown"):
        if intent.needs_context and intent.context_scope == "all_groups":
            from hermes_bot.cron.searcher import run_one_shot_search
            return run_one_shot_search(intent.query or message)
        return respond_freeform(session, message)

    if intent.intent == "statement":
        session.topic = message[:80]
        return respond_freeform(session, message)

    return respond_freeform(session, message)
