# Hermes — WhatsApp Personal Assistant

A WhatsApp-native personal assistant with slash commands, conversation continuity, and
deep-dive search across all your chats. Deploy in one click — no terminal needed after deploy.

## Quick Start (Cloud)

### Option 1: Railway (one-click)

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new?template=https://github.com/sameer-hoda/hermes)

1. Click the button above. Railway auto-detects the `Dockerfile` and `railway.json`.
2. **Attach a volume** at mount path `/data` (required — stores your WhatsApp session so it survives redeploys)
3. Open the deployed app URL
4. Check deploy logs for the one-time console access code, then follow the setup wizard in your browser

### Option 2: Hostinger VPS / Any Docker Host

```bash
git clone https://github.com/sameer-hoda/hermes.git && cd hermes
docker compose up -d
# Open http://<your-server-ip>:8080 → follow setup wizard
```

### Option 3: Local Dev

```bash
git clone https://github.com/sameer-hoda/hermes.git && cd hermes
cd components/wa_bridge && GOTOOLCHAIN=go1.25.0 go build -o wa-bridge . && cd ../..
pip install -r hermes_bot/requirements.txt -r components/wa_slash_commands/requirements.txt
./scripts/hermes_start.sh
# Open http://localhost:8080 → follow setup wizard
```

## Setup Wizard (Browser)

Once deployed, the setup wizard walks you through 3 steps entirely in your browser:

| Step | What you do |
|------|-------------|
| **1. Gemini Key** | Paste your Gemini API key ([get one free](https://aistudio.google.com)) |
| **2. QR Code** | Scan the QR with WhatsApp (Settings → Linked Devices → Link a Device) |
| **3. Pair MeChat** | Send the `HERMES-XXXX` code in the WhatsApp chat you want as your assistant chat |

After pairing, the dashboard shows your chat name, connection status, and uptime. Hermes sends a welcome message into your paired chat.

### Kill & Reset

Dashboard → **Kill & Reset** → type `RESET` to confirm. This unlinks the device from your phone and wipes all data. You can optionally keep your Gemini API key.

Or send `/reset` in your MeChat → reply `RESET CONFIRM` within 2 minutes.

## What It Does

| Feature | How it works |
|---------|-------------|
| **Slash commands** | `/sotu`, `/pending`, `/stats`, `/recap`, `/eli5`, `/help` in any chat |
| **Personal assistant** | Talk naturally in your paired chat. "what's open", "catch me up", or any topic |
| **24-hr Sitrep** | "what needs my attention" — scans all groups for action items |
| **Deep dive search** | `/ask <topic>` — scans all non-archived groups for relevant updates |
| **Daily cron** | Schedule recurring summaries: `/cron add "topic" daily 09:00` |

## Architecture

```
┌─────────────────┐        ┌──────────────────┐
│   Go Bridge      │◄───────│  Python Hermes   │
│   (whatsmeow)    │        │                  │
│                  │        │ • supervisor      │
│ • Web wizard     │        │ • cron scheduler  │
│ • Setup state    │        │ • flush thread    │
│ • :8080 public   │        │                  │
│ • 127.0.0.1:8081 │        │                  │
│   internal API   │        │                  │
└────────┬─────────┘        └──────────────────┘
         │
    ┌────┴──── spawned on incoming messages ────┐
    │                                          │
    ▼                                          ▼
wacmd.py (slash commands)    mechat_handler.py (assistant)
```

## Environment Variables

All variables are optional — the setup wizard handles configuration in-browser:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Gemini API key (skip wizard step 1 if set) |
| `OWNER_PHONE_NUMBER` | Your phone number (auto-detected after pairing) |
| `MECHAT_JID` | Assistant chat JID (set during wizard step 3) |
| `SETUP_PASSWORD` | Console access password (auto-generated if unset) |
| `STORE_DIR` | Persistent state directory (default `/data` in Docker, `store/` locally) |
| `PORT` | Public HTTP port (default 8080) |
| `HERMES_TIMEZONE` | Timezone for cron/sessions (default Asia/Kolkata) |

## Project Structure

```
hermes_bot/          — Python bot (main, config, supervisor, sender, db)
  assistant/         — MeChat assistant (session, continuity, handler, responder)
  cron/              — deep dive & cron (scheduler, searcher, feedback)
components/
  wa_bridge/         — Go bridge (whatsmeow, web wizard, REST API)
  wa_slash_commands/ — slash command engine
scripts/             — startup scripts
```

## Documentation

- `HERMES.md` — project overview & build log
- `docs/contact_resolution.md` — JID/LID/phone resolution guide
- `docs/whatsapp_database_master_guide.md` — DB schema reference

## Privacy Note

Your WhatsApp message history is stored unencrypted in SQLite databases on the host. When deploying on a VPS, use a single-tenant box and consider disk encryption. Your Gemini API key is stored with restricted permissions (`chmod 600`). The setup console is password-protected with HMAC-signed session cookies.