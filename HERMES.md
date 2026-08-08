# Hermes — Project Overview & Build Log

> **Date:** 2026-08-07
> **Status:** First working prototype built. All Python code written, Go bridge modified. Ready to pair and test.

---

## What Was Built

Hermes is a unified WhatsApp bot that consolidates the existing wa_pull + wa_slash_commands
components into a single project with a personal assistant in MeChat, conversation continuity
awareness, and a hot-word-driven deep-dive search system across all non-archived chats.

### Project Structure

```
master_project/
├── README.md                          # this project overview
├── scripts/
│   └── hermes_start.sh                # single start command
├── hermes_bot/                        # the unified bot (NEW — 16 files)
│   ├── main.py                        # entry point: supervisor + cron
│   ├── config.py                      # env vars & constants
│   ├── supervisor.py                  # bridge lifecycle, QR relay, crash recovery
│   ├── sender.py                      # WhatsApp message sender
│   ├── db.py                          # SQLite queries (groups, messages, contacts)
│   ├── mechat_handler.py              # CLI invoked by Go bridge on MeChat messages
│   ├── .env / .env.example            # config (GEMINI_API_KEY, OWNER_PHONE_NUMBER)
│   ├── requirements.txt               # requests, google-genai, python-dotenv
│   ├── assistant/                     # MeChat personal assistant logic
│   │   ├── session.py                 # JSON-persisted conversation sessions
│   │   ├── continuity.py              # LLM-based continuity detection
│   │   ├── handler.py                 # intent detection & routing
│   │   └── responder.py               # free-form responses, routing dispatch
│   └── cron/                          # hot-word deep dive system
│       ├── scheduler.py               # background thread, checks every 30s
│       ├── cron_store.py              # SQLite CRUD for cron jobs
│       ├── searcher.py                # 5-step deep dive pipeline
│       └── feedback.py                # feedback state machine
├── components/                        # infrastructure
│   ├── wa_bridge/                     # Go bridge (MODIFIED — MeChat trigger added)
│   ├── wa_slash_commands/             # slash command engine (used as-is)
│   └── wa_pull/                       # legacy reference (kept for compatibility)
└── docs/                              # documentation
    ├── contact_resolution.md          # JID/LID/phone → name resolution
    ├── archive_detection.md           # archived chat detection guide
    ├── whatsapp_database_master_guide.md  # DB schema reference
    └── superpowers/specs/
        └── 2026-08-07-hermes-design.md   # full design spec
```

---

## How to Start

```bash
cd /path/to/your/project/wa_main_v2/master_project
./scripts/hermes_start.sh
```

That's the only command. It:

1. Checks if the Go bridge binary (`wa-bridge`) exists; builds it if not (`cd components/wa_bridge && go build`)
2. Loads `.env` from `hermes_bot/.env` (GEMINI_API_KEY, OWNER_PHONE_NUMBER)
3. Starts the Go bridge as a subprocess (QR code on first pairing, auto-connect if paired)
4. Waits for pairing / connection
5. Once API is up on `:8080`, launches the cron scheduler thread
6. Sends a welcome message to MeChat
7. Blocks, monitoring bridge health (auto-restart on crash)

---

## Architecture

### How Messages Flow

```
WhatsApp message arrives
         │
         ▼
Go Bridge (whatsmeow) writes to messages.db + whatsapp.db
         │
         ├── Message starts with "/"
         │   └── spawns wacmd.py <chat_jid> <sender_jid> <command>
         │       (slash commands: /sotu, /pending, /stats, /recap, /eli5, /help)
         │
         └── Message is from MeChat + owner + NOT a "/" command
             └── spawns mechat_handler.py <chat_jid> <sender_jid> <text>
                 │
                 ├── Loads session from hermes_bot/store/session.json
                 ├── Checks conversation continuity (LLM)
                 ├── Routes intent (LLM)
                 │   ├── /ask query → deep dive across groups
                 │   ├── /cron add/list/pause/feedback → cron management
                 │   ├── question → free-form LLM response
                 │   ├── statement → acknowledge + offer options
                 │   └── greeting/help → static responses
                 ├── Sends reply via POST :8080/api/send
                 └── Saves session to session.json, exits
```

### Key Design Decisions

**Bridge-triggered, not polling.**
The Go bridge's `handleMessage()` function directly spawns `mechat_handler.py` when a
MeChat message arrives from the owner. This is the same subprocess-spawning pattern the
bridge already uses for slash commands (`wacmd.py`). Zero latency, no polling loop.

**Fresh process per message.**
`mechat_handler.py` is a CLI script that runs, processes one message, and exits. Session
state (conversation topic, recent messages, timeout) is persisted to
`hermes_bot/store/session.json` — read on startup, written on completion.

**Only the cron scheduler is long-running.**
The `hermes_bot/main.py` process only runs the bridge supervisor and the cron scheduler
thread. Everything else is stateless or file-persisted.

---

## What Was Changed in the Go Bridge

**File:** `components/wa_bridge/main.go` — 3 changes:

1. **Line 32:** Added `var ownerPhone string` global variable
2. **Lines 830-833:** In `main()`, reads `OWNER_PHONE_NUMBER` env var on startup
3. **Lines 505-557:** In `handleMessage()`, after the existing slash-command handler block,
   added a MeChat trigger:
   - Checks if `chatUser == ownerPhone` (standard MeChat JID)
   - Falls back to checking `@lid` suffix for LID-based MeChat
   - If sender is owner AND it's MeChat AND message doesn't start with `/`
   - Spawns `../hermes_bot/mechat_handler.py <chat_jid> <sender_jid> <text>`
   - Runs in a goroutine (non-blocking)

---

## What Was Removed

These components were deleted because they're not part of the Hermes project:

- `components/channel_manager/` — multi-channel routing manager
- `components/master_tracker/` — initiative/OKR tracker
- `components/wa_brain/` — brain writer helper
- `components/wa_productivity/` — legacy analysis scripts
- `scripts/` (old) — legacy deploy/EC2/sync scripts (replaced with `scripts/hermes_start.sh`)
- 13 stale docs from `docs/` — EC2 guide, backend docs, frontend docs, troubleshooting, etc.

---

## Feature Details

### 1. Slash Commands (unchanged from existing)

Works in any chat. Owner-only (enforced by `wacmd.py:390-407`).

| Command | What it does |
|---------|-------------|
| `/sotu` | State of the Union — group summary |
| `/pending` | Pending action items |
| `/stats` | Team activity stats |
| `/recap` | Last 24 hours recap |
| `/eli5 <topic>` | Explain topic in detail |
| `/help` | Show available commands |

### 2. MeChat Personal Assistant

**Conversation continuity:**
- Each conversation is a "session" with a topic label
- On each message, an LLM call checks: is this continuing the current topic?
  - High confidence (≥0.7) yes → continue session, respond with context
  - Low confidence (0.4–0.7) → ask user "continue or start fresh?"
  - No → close old session, start new
- Sessions auto-timeout after 60 minutes of inactivity
- Session state persisted to `hermes_bot/store/session.json`

**Intent routing:**

| User sends | Hermes does |
|-----------|------------|
| `hi`, `hello`, `hey` | Greeting |
| `help`, `/help` | Help text with available commands |
| `/ask <query>` | One-shot deep dive across groups |
| `/cron add "<query>" daily 09:00` | Create recurring cron job |
| `/cron list` | List active cron jobs |
| `/cron pause <id>` | Pause a cron job |
| `/cron resume <id>` | Resume a cron job |
| `/cron delete <id>` | Delete a cron job |
| `/cron feedback <id> "feedback"` | Give feedback on last run |
| Natural language question | LLM free-form response |
| Natural language (query-like) | May trigger deep dive if LLM detects it |

### 3. Hot-Word Deep Dive (`/ask`)

5-step pipeline:

1. **List groups** — query all non-archived groups active in last 30 days
2. **Score relevance** — batch groups into 10s, LLM scores each 0-10 for relevance to query
3. **Deep fetch** — get last 200 messages from top-N relevant groups
4. **Per-group summarize** — LLM summarizes each group's relevant content in 3-5 bullets
5. **Cross-group synthesize** — LLM produces overall picture, key items, blockers, contradictions

Every response includes a methodology footer:
```
🔍 Methodology
Scanned: 47 groups · Matched: 12 relevant
Lookback: 14 days · Messages: ~200/group
Relevance filter: "UPI growth"
Deep-dived: top 8 groups
```

### 4. Cron Jobs

**State machine:**
```
active → runs → awaiting_feedback
  ├── user likes → saved (continues on schedule)
  └── user dislikes → feedback_collected → retry_pending → retries with feedback
```

**Storage:** `hermes_bot/store/hermes.db` (SQLite) — `cron_jobs` and `cron_run_log` tables

**Scheduling:** Background thread checks every 30 seconds for due jobs. Supports
`daily`, `weekdays`, `weekly:<day>`, and `oneshot` frequencies.

**Feedback loop:** When user gives feedback on a run, it's injected into the LLM
synthesis prompt on the next run. Example: "User said last summary was too broad —
focus only on specific decisions."

---

## Environment Variables

**`hermes_bot/.env`** (already configured):

```env
GEMINI_API_KEY=...           # from wa-slash-commands/.env
OWNER_PHONE_NUMBER=91XXXXXXXXXX

# Defaults below work out of the box:
# MESSAGES_DB_PATH=components/wa_bridge/store/messages.db
# WHATSAPP_DB_PATH=components/wa_bridge/store/whatsapp.db
# WA_API_URL=http://localhost:8080
# HERMES_DB_PATH=hermes_bot/store/hermes.db
# SESSION_TIMEOUT_MINUTES=60
# MAX_GROUPS_PER_SEARCH=10
# SEARCH_LOOKBACK_DAYS=14
# CRON_ENABLED=1
```

---

## Dependencies

**Python** (`hermes_bot/requirements.txt`):
- `requests>=2.31.0` — bridge API calls
- `google-genai>=0.3.0` — Gemini LLM
- `python-dotenv>=1.0.0` — .env loading

**Go** (`components/wa_bridge/go.mod`):
- `go.mau.fi/whatsmeow` — WhatsApp Web client
- `github.com/mattn/go-sqlite3` — SQLite driver
- `github.com/mdp/qrterminal` — QR code rendering

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `hermes_bot/main.py` | 65 | Entry point, bridge lifecycle, signal handling |
| `hermes_bot/supervisor.py` | 105 | Bridge subprocess, QR relay, pairing wait, API health check |
| `hermes_bot/mechat_handler.py` | 90 | CLI script: loads session → continuity → intent → reply → save |
| `hermes_bot/assistant/session.py` | 155 | SessionManager class, JSON persistence, timeout logic |
| `hermes_bot/assistant/continuity.py` | 55 | LLM call: "is this continuing the same conversation?" |
| `hermes_bot/assistant/handler.py` | 90 | LLM call: detect intent (ask/cron/question/statement/etc.) |
| `hermes_bot/assistant/responder.py` | 95 | Route intents to handlers, free-form LLM responses, help text |
| `hermes_bot/cron/searcher.py` | 180 | 5-step pipeline: groups → relevance → fetch → summarize → synthesize |
| `hermes_bot/cron/cron_store.py` | 190 | SQLite CRUD for cron_jobs + cron_run_log tables |
| `hermes_bot/cron/scheduler.py` | 95 | Background thread, 30s tick, cron execution + feedback delivery |
| `hermes_bot/cron/feedback.py` | 115 | Handle /cron add/list/pause/feedback/keep commands |
| `hermes_bot/db.py` | 180 | All SQLite queries (non-archived groups, messages, contacts, MeChat JID) |
| `hermes_bot/sender.py` | 55 | POST to bridge API, long message splitting, retry logic |
| `hermes_bot/config.py` | 40 | Env var loading, path defaults, model config |
| `components/wa_bridge/main.go` | 1432 | Go bridge — modified with MeChat trigger (lines 505-557) |