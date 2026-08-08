#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
HERMES_DIR="$PROJECT_DIR/hermes_bot"
BRIDGE_DIR="$PROJECT_DIR/components/wa_bridge"

echo "=== Hermes — WhatsApp Personal Assistant ==="
echo ""

# Build Go bridge if needed
if [ ! -f "$BRIDGE_DIR/wa-bridge" ]; then
    echo "[setup] Building Go bridge..."
    cd "$BRIDGE_DIR"
    GOTOOLCHAIN=go1.25.0 go build -o wa-bridge .
    cd "$PROJECT_DIR"
    echo "[setup] Bridge built."
fi

# Check for .env
if [ ! -f "$HERMES_DIR/.env" ]; then
    if [ -f "$HERMES_DIR/.env.example" ]; then
        echo "[setup] No .env found. Copying from .env.example..."
        cp "$HERMES_DIR/.env.example" "$HERMES_DIR/.env"
        echo "[setup] Edit hermes_bot/.env and add your GEMINI_API_KEY"
        echo "[setup] Then run this script again."
        exit 1
    fi
fi

# Ensure store directory exists
mkdir -p "$HERMES_DIR/store"

# Launch Hermes
cd "$PROJECT_DIR"
exec python3 -m hermes_bot.main
