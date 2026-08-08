# Hermes — WhatsApp Personal Assistant

A WhatsApp-native personal assistant with slash commands, conversation continuity, and
hot-word-driven deep-dive search across all your chats.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-username/hermes.git && cd hermes

# 2. Set up
cp hermes_bot/.env.example hermes_bot/.env
# Edit hermes_bot/.env → add your GEMINI_API_KEY and OWNER_PHONE_NUMBER

# 3. Install deps
pip install -r hermes_bot/requirements.txt
# Requires Go 1.24+ with toolchain support (go1.25 auto-downloads on first build)

# 4. Start
./scripts/hermes_start.sh
```

On first run, a QR code appears. Scan it with WhatsApp (Settings → Linked Devices).
Once paired, all interaction happens on WhatsApp — the terminal is no longer needed.

## What It Does

| Feature | How it works |
|---------|-------------|
| **Slash commands** | `/sotu`, `/pending`, `/stats`, `/recap`, `/eli5`, `/help` in any chat |
| **Personal assistant** | Talk naturally in your self-chat. "what's open", "catch me up", or any topic |
| **24-hr Sitrep** | "what's pending on me" — scans all groups for action items needing your attention |
| **Deep dive search** | `/ask <topic>` — scans all non-archived groups for relevant updates |
| **Daily cron** | Schedule recurring summaries: `/cron add "topic" daily 09:00` |

## Architecture

```
┌─────────────────┐        ┌──────────────────┐
│   Go Bridge      │        │  Hermes Python   │
│   (whatsmeow)    │        │                  │
│                  │◄───────│ • supervisor      │
│ • QR auth        │health  │ • cron scheduler  │
│ • :8080 REST API │check   │ • flush thread    │
│ • SQLite DBs     │        │                  │
└────────┬─────────┘        └──────────────────┘
         │
    ┌────┴──── spawns on incoming messages ────┐
    │                                          │
    ▼                                          ▼
wacmd.py (slash)              mechat_handler.py (assistant)
```

## Project Structure

```
hermes_bot/          — the unified bot (entry point, config, supervisor, sender, db)
  assistant/         — MeChat personal assistant (session, continuity, handler, responder)
  cron/              — deep dive & cron system (scheduler, searcher, feedback)
components/
  wa_bridge/         — Go whatsmeow bridge (QR auth, REST API, DB writes)
  wa_slash_commands/ — slash command engine (wacmd.py, engine.py, formatter.py)
  wa_pull/           — legacy reference implementation
docs/                — documentation (contact resolution, archive detection, DB guide, spec)
scripts/
  hermes_start.sh    — single start command
```

## Environment Variables

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
OWNER_PHONE_NUMBER=91XXXXXXXXXX

# MeChat — the chat Hermes talks to you in (your personal "notes" group)
MECHAT_JID=91XXXXXXXXXX-1633800754@g.us

# Optional (defaults work out of the box)
# BRIDGE_PORT=8877                 # change if another local server owns the port
# WA_API_URL=http://localhost:8877 # must match BRIDGE_PORT
# SESSION_TIMEOUT_MINUTES=60
# MAX_GROUPS_PER_SEARCH=10
# CRON_ENABLED=1
```

## Dependencies

- **Python:** `requests`, `google-genai`, `python-dotenv`
- **Go:** 1.21+ (bridge auto-compiles on first run)
- **WhatsApp:** A WhatsApp account to pair with

## Documentation

- `docs/superpowers/specs/` — full design spec
- `docs/contact_resolution.md` — JID/LID/phone → name resolution guide
- `docs/archive_detection.md` — archived chat detection guide
- `docs/whatsapp_database_master_guide.md` — DB schema reference
- `HERMES.md` — project overview & build log