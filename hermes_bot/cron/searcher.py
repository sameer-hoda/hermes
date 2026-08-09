import json
import time

from google import genai

from hermes_bot import config
from hermes_bot import db

RELEVANCE_PROMPT = """Given the search query: "{query}"

Which of these WhatsApp groups are relevant to this query?
Respond with JSON only: a list of objects with group_jid and relevance (0-10) and a brief why.
Only include groups with relevance >= 5.
Base your score on both the group name AND the sample of recent messages shown.

Groups:
{group_list}"""


SUMMARIZE_GROUP_PROMPT = """You are Hermes — a personal assistant helping the user stay on top of their WhatsApp messages.

Here are recent messages from the group "{group_name}", filtered for relevance to "{query}".

Your job: Summarize what matters. Structure the output naturally — use sections, bullets, or plain paragraphs based on what the content demands. Focus on:
- Decisions made, action items assigned, and status updates
- Blockers, risks, or escalations
- Key facts: names, dates, numbers, commitments

Be crisp and specific. Skip fluff, chatter, and resolved items. Use WhatsApp markdown: *bold* for key terms.

Messages:
{messages}"""


SYNTHESIS_PROMPT = """You are Hermes — a personal assistant helping the user stay on top of their WhatsApp messages.

You analyzed {group_count} groups for relevance to "{query}". Below are per-group summaries.

Your job: Synthesize everything into one crisp, comprehensive message for the user.

Principles:
- Decide the best structure based on what you found. Use sections only if they add clarity — never force a template.
- Cover all key points: decisions, action items, blockers, status updates, and anything needing attention.
- Be comprehensive but brief. Every line must earn its place.
- Use WhatsApp markdown: *bold* for key terms, `monospace` for numbers/dates.
- Speak directly to the user as their personal assistant. Warm but professional.
- If nothing is urgent or blocked, say so — don't invent a crisis.

{feedback_instruction}
Per-group summaries:
{all_summaries}"""


def _score_relevance(query: str, groups: list[dict]) -> list[dict]:
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    relevant = []
    batch_size = 10

    for i in range(0, len(groups), batch_size):
        batch = groups[i:i + batch_size]

        parts = []
        for g in batch:
            recent = db.get_chat_messages(g["jid"], days=14, limit=30)
            snippet = "N/A"
            if recent:
                lines = []
                for m in recent[-10:]:
                    lines.append(f"[{m['time'].strftime('%m/%d %H:%M')}] {m['sender']}: {m['content'][:120]}")
                snippet = "\n".join(lines)
            parts.append(f"  - {g['name']} (jid: {g['jid']})\n    Recent: {snippet[:600]}")

        group_list = "\n".join(parts)

        prompt = RELEVANCE_PROMPT.format(query=query, group_list=group_list)

        try:
            response = client.models.generate_content(
                model=config.GEMINI_MODEL_FAST,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            scores = json.loads(response.text)
            for item in scores:
                if item.get("relevance", 0) >= 5:
                    item["name"] = next(
                        (g["name"] for g in batch if g["jid"] == item.get("group_jid")),
                        item.get("group_jid", "").split("@")[0],
                    )
                    relevant.append(item)
        except Exception as e:
            print(f"[searcher] Relevance scoring error: {e}")
            continue

        if i + batch_size < len(groups):
            time.sleep(1)

    relevant.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    return relevant[:config.MAX_GROUPS_PER_SEARCH]


def _summarize_group(query: str, group: dict) -> str:
    messages = db.get_chat_messages(
        group["group_jid"],
        days=config.SEARCH_LOOKBACK_DAYS,
        limit=config.SEARCH_MESSAGES_PER_GROUP,
    )

    formatted = "\n".join(
        f"[{m['time'].strftime('%m/%d %H:%M')}] {m['sender']}: {m['content']}"
        for m in messages
    )

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    prompt = SUMMARIZE_GROUP_PROMPT.format(
        group_name=group.get("name", group.get("group_jid", "")),
        query=query,
        messages=formatted[:8000],
    )

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_FAST,
            contents=prompt,
        )
        return f"📍 *{group.get('name', 'Group')}*\n{response.text.strip()}"
    except Exception as e:
        print(f"[searcher] Summarize error for {group.get('name')}: {e}")
        return f"📍 *{group.get('name', 'Group')}*\n(Unable to summarize)"


def _synthesize(query: str, group_summaries: list[str], feedback: str = "") -> str:
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    feedback_instruction = ""
    if feedback:
        feedback_instruction = f'\nUser feedback from previous run: "{feedback}". Adjust accordingly.\n'

    prompt = SYNTHESIS_PROMPT.format(
        group_count=len(group_summaries),
        query=query,
        all_summaries="\n\n---\n\n".join(group_summaries),
        feedback_instruction=feedback_instruction,
    )

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_FAST,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[searcher] Synthesis error: {e}")
        return f"*{query}* — unable to complete synthesis. Please try again."


def _methodology_footer(
    total_groups: int,
    matched_groups: int,
    query: str,
) -> str:
    return (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔍 *Methodology*\n"
        f"Scanned: {total_groups} groups · Matched: {matched_groups} relevant\n"
        f"Lookback: {config.SEARCH_LOOKBACK_DAYS} days · "
        f"Messages: ~{config.SEARCH_MESSAGES_PER_GROUP}/group\n"
        f'Relevance filter: "{query}"\n'
        f"Deep-dived: top {min(matched_groups, config.MAX_GROUPS_PER_SEARCH)} groups"
    )


STATUS_CHECK_PROMPT = """You are Hermes — a personal assistant generating a situation report for the user.
Scan these messages from the last {hours} hours across all WhatsApp groups.

The sender "You" = the user themselves. Messages from the user start with "You:".

═══ CRITICAL: WHAT "PENDING ON ME" MEANS ═══

ONLY report items where the user ("You") specifically needs to DO something, DECIDE something, or RESPOND to something. These are commitments ON the user, not by others.

✅ INCLUDE — these are "on me":
- The user said "I'll do X", "let me check", "I'll get back to you", "will update by Friday"
- Someone asked the user a direct question that hasn't been answered
- Someone requested something from the user: "can you review", "need your approval", "please share"
- The user made a promise or commitment: "sending by EOD", "will fix this"
- The user is tagged/mentioned in a decision that needs their input

❌ EXCLUDE — these are NOT "on me":
- Things other people said they'll do ("Amit will handle it")
- General status updates from others that the user hasn't committed to
- Things the user already completed or responded to
- FYIs, announcements, or general chatter
- Someone ELSE's action items or blockers

═══ FORMAT ═══

Group by chat name. One bullet per item. Each bullet must mention:
- What the user committed to do
- Who asked (if someone did)
- Any deadline mentioned

Be strict: if you're not sure it's on the user, exclude it.
If nothing is pending on the user, say "Nothing pending on you right now." — do NOT pad with general activity.

Messages (newest first):
{messages}

Your response (speak directly to the user, WhatsApp markdown):"""


def run_status_check(progress=None) -> str:
    def _say(msg: str):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    _say("🔍 Scanning your last 24h across all chats …")

    messages = db.get_recent_all_messages(hours=24, limit=1000)

    if not messages:
        return "No recent messages across your groups in the last 24 hours."

    _say(f"📋 Found *{len(messages)}* messages — extracting what needs your attention …")

    formatted = "\n".join(
        f"[{m['chat_name']}] [{m['time'].strftime('%H:%M')}] {m['sender']}: {m['content']}"
        for m in messages
    )

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    prompt = STATUS_CHECK_PROMPT.format(hours=24, messages=formatted[:30000])

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_FAST,
            contents=prompt,
        )
        text = response.text.strip()
    except Exception as e:
        print(f"[searcher] Status check error: {e}")
        return "Couldn't generate the status report. Try again in a moment."

    return f"📊 *Your 24-hr Sitrep*\n\n{text}"


def run_one_shot_search(query: str, progress=None) -> str:
    def _say(msg: str):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    groups = db.get_active_groups(days=14)
    if not groups:
        return "No active groups found in the last 14 days."

    _say(f"🔍 Scanning *{len(groups)}* active groups for _{query[:60]}_ …")

    relevant = _score_relevance(query, groups)
    if not relevant:
        return f"No groups found relevant to *{query}*.\nTry a different query or broader terms."

    _say(f"🎯 *{len(relevant)}* relevant groups found — reading messages…")

    summaries = []
    for i, group in enumerate(relevant, 1):
        _say(f"📝 Reading {i}/{len(relevant)}: _{group.get('name', 'Group')}_")
        summary = _summarize_group(query, group)
        summaries.append(summary)

    _say("🧠 Stitching it all together…")
    synthesis = _synthesize(query, summaries)

    footer = _methodology_footer(len(groups), len(relevant), query)

    return f"🤖 *{query}*\n\n{synthesis}\n\n{footer}"


def run_cron_search(query: str, feedback: str = "") -> tuple[str, str, int, int]:
    groups = db.get_active_groups(days=14)
    total = len(groups)

    if not groups:
        return "No active groups found.", "", total, 0

    relevant = _score_relevance(query, groups)
    matched = len(relevant)

    if not relevant:
        return f"No groups found relevant to *{query}*.", "", total, 0

    summaries = []
    for group in relevant:
        summary = _summarize_group(query, group)
        summaries.append(summary)

    synthesis = _synthesize(query, summaries, feedback)

    footer = _methodology_footer(total, matched, query)

    return f"🤖 *{query}*\n\n{synthesis}\n\n{footer}", footer, total, matched


PERSON_SUMMARY_PROMPT = """You are Hermes — a personal assistant helping the user stay on top of their 1-on-1 WhatsApp conversations.

Here are recent messages between the user and {person_name} from the last {days} days.

Your job: Summarize the conversation for the user.

Principles:
- Decide the best structure based on what was discussed. Sections, bullets, or paragraphs — whatever fits.
- Cover all key points: decisions made, promises given, action items, follow-ups needed, important info shared.
- Be crisp and specific. Mention dates, commitments, and any open loops.
- If there's nothing substantive, say so honestly.
- Use WhatsApp markdown: *bold* for key terms.
- Speak directly to the user.

Messages (newest first):
{messages}"""


def run_person_search(person_name: str, person_jid: str, progress=None) -> str:
    def _say(msg: str):
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    _say(f"👤 Looking up chats with *{person_name}* …")

    messages = db.get_person_messages(person_jid, days=14, limit=200)

    if not messages:
        return f"No recent messages with *{person_name}* in the last 14 days."

    _say(f"📋 Found *{len(messages)}* messages — summarizing …")

    formatted = "\n".join(
        f"[{m['time'].strftime('%m/%d %H:%M')}] {m['sender']}: {m['content']}"
        for m in messages
    )

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    prompt = PERSON_SUMMARY_PROMPT.format(
        person_name=person_name,
        days=14,
        messages=formatted[:12000],
    )

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL_FAST,
            contents=prompt,
        )
        return f"👤 *{person_name}*\n\n{response.text.strip()}"
    except Exception as e:
        print(f"[searcher] Person summary error: {e}")
        return f"Couldn't summarize chats with *{person_name}*. Try again."
