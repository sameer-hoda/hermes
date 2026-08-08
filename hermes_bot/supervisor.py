import os
import sys
import time
import subprocess
import sqlite3
from pathlib import Path

from hermes_bot import config

BRIDGE_DIR = config.PROJECT_ROOT / "components" / "wa_bridge"


def _bridge_binary() -> Path:
    return BRIDGE_DIR / "wa-bridge"


def _bridge_device_exists() -> bool:
    whatsapp_db = Path(config.WHATSAPP_DB)
    if not whatsapp_db.exists():
        return False
    try:
        conn = sqlite3.connect(str(whatsapp_db))
        row = conn.execute("SELECT COUNT(*) FROM whatsmeow_device").fetchone()
        conn.close()
        return bool(row and row[0] > 0)
    except Exception:
        return False


def _bridge_send_works() -> bool:
    import requests
    try:
        resp = requests.post(
            f"{config.BRIDGE_URL}/api/send",
            json={"recipient": "test@s.whatsapp.net", "message": ""},
            timeout=5,
        )
        data = resp.json()
        return data.get("success", False)
    except Exception:
        return False


def _bridge_api_up() -> bool:
    import requests
    try:
        requests.post(
            f"{config.BRIDGE_URL}/api/send",
            json={"recipient": "test@s.whatsapp.net", "message": ""},
            timeout=3,
        )
        return True
    except Exception:
        return False


def _is_connected_line(line: str) -> bool:
    markers = [
        "Successfully connected and authenticated",
        "Connected to WhatsApp",
    ]
    return any(m in line for m in markers)


def start_bridge() -> subprocess.Popen:
    binary = _bridge_binary()
    if not binary.exists():
        print("[supervisor] Building Go bridge...")
        result = subprocess.run(
            ["go", "build", "-o", str(binary), "."],
            cwd=str(BRIDGE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[supervisor] Build failed:\n{result.stderr}")
            sys.exit(1)
        print("[supervisor] Bridge built.")

    env = os.environ.copy()
    if config.OWNER_PHONE:
        env["OWNER_PHONE_NUMBER"] = config.OWNER_PHONE

    print("[supervisor] Starting Go bridge...")
    proc = subprocess.Popen(
        [str(binary)],
        cwd=str(BRIDGE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    return proc


def wait_for_pairing(proc: subprocess.Popen, timeout: int = 180) -> bool:
    if _bridge_device_exists() and _bridge_api_up():
        print("[supervisor] Bridge already paired and connected.")
        return True

    print("\n📱 *Scan this QR code with WhatsApp*")
    print("   Settings → Linked Devices → Link a Device\n")

    qr_shown = False
    connected = False
    start = time.time()

    for line in iter(proc.stdout.readline, ""):
        stripped = line.rstrip()

        if any(c in stripped for c in ["▀", "▄", "█", "▌", "▐"]):
            if not qr_shown:
                qr_shown = True
            sys.stdout.write(line)
            sys.stdout.flush()
            continue

        if stripped:
            if "level=" not in stripped and "REST server" not in stripped:
                pass
            if _is_connected_line(stripped):
                print(f"\n[supervisor] {stripped}")
                connected = True
            elif qr_shown:
                pass
            else:
                print(f"[bridge] {stripped}")

        if connected:
            break

        if time.time() - start > timeout:
            print("\n[supervisor] QR pairing timed out (3 min).")
            proc.terminate()
            return False

    if not connected:
        print("[supervisor] Bridge did not report connection. Exiting.")
        proc.terminate()
        return False

    print("[supervisor] Waiting for bridge to be ready...")
    for i in range(90):
        if proc.poll() is not None:
            print(f"[supervisor] Bridge exited unexpectedly (code {proc.returncode}).")
            return False
        if _bridge_device_exists() and _bridge_api_up():
            print("\n✅ Paired. Hermes is live. All interaction now on WhatsApp.\n")
            return True
        time.sleep(1)

    print("[supervisor] Bridge not ready after 90s. Exiting.")
    proc.terminate()
    return False


def launch(proc: subprocess.Popen) -> bool:
    return wait_for_pairing(proc)
