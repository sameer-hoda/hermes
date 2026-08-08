import os
import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

_load_dotenv = load_dotenv(SCRIPT_DIR / ".env")

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# ── Databases (produced by the Go bridge) ────────────────────────────────────
MESSAGES_DB = os.getenv("MESSAGES_DB_PATH") or str(PROJECT_ROOT / "components" / "wa_bridge" / "store" / "messages.db")
WHATSAPP_DB = os.getenv("WHATSAPP_DB_PATH") or str(PROJECT_ROOT / "components" / "wa_bridge" / "store" / "whatsapp.db")

# ── Bridge HTTP API ──────────────────────────────────────────────────────────
BRIDGE_URL = os.getenv("WA_API_URL", "http://localhost:8080")

# ── Owner ────────────────────────────────────────────────────────────────────
OWNER_PHONE = os.getenv("OWNER_PHONE_NUMBER", "").strip().replace("+", "")

# ── MeChat (owner's self-chat / personal notes group) ───────────────────────
MECHAT_JID = os.getenv("MECHAT_JID", "").strip()

# ── LLM ──────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_FAST = os.getenv("GEMINI_MODEL_FAST", "gemini-3.1-flash-lite-preview")
GEMINI_MODEL_PRO = os.getenv("GEMINI_MODEL_PRO", "gemini-3.1-flash-lite-preview")

# ── Session ──────────────────────────────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
SESSION_FILE = os.getenv("SESSION_FILE") or str(SCRIPT_DIR / "store" / "session.json")

# ── Deep Dive Pipeline ──────────────────────────────────────────────────────
MAX_GROUPS_PER_SEARCH = int(os.getenv("MAX_GROUPS_PER_SEARCH", "10"))
SEARCH_LOOKBACK_DAYS = int(os.getenv("SEARCH_LOOKBACK_DAYS", "14"))
SEARCH_MESSAGES_PER_GROUP = int(os.getenv("SEARCH_MESSAGES_PER_GROUP", "200"))

# ── Cron ─────────────────────────────────────────────────────────────────────
CRON_ENABLED = os.getenv("CRON_ENABLED", "1") != "0"
HERMES_DB_PATH = os.getenv("HERMES_DB_PATH") or str(SCRIPT_DIR / "store" / "hermes.db")

# ── Store ────────────────────────────────────────────────────────────────────
STORE_DIR = SCRIPT_DIR / "store"
