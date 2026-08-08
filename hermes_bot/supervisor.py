import os
import sys
import time
import signal
import subprocess
import sqlite3
from pathlib import Path

from hermes_bot import config

BRIDGE_DIR = config.PROJECT_ROOT / "components" / "wa_bridge"


def _bridge_port() -> int:
    port = os.getenv("BRIDGE_PORT", "").strip()
    if port:
        return int(port)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(config.BRIDGE_URL)
        if parsed.port:
            return parsed.port
    except Exception:
        pass
    return 8080


def _pids_listening_on_port(port: int) -> list[int]:
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True, text=True, timeout=5,
        )
        return [int(x) for x in result.stdout.split()]
    except Exception:
        return []


def _is_bridge_process(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True, text=True, timeout=5,
        )
        return "wa-bridge" in result.stdout
    except Exception:
        return False


def _free_bridge_port(port: int):
    """Kill stale wa-bridge processes holding the port; abort if a foreign process owns it.

    A stale bridge from a previous run silently cripples the whole system: the new
    bridge can't bind the REST port, so sends fail while receives keep working.
    """
    pids = _pids_listening_on_port(port)
    if not pids:
        return
    for pid in pids:
        if _is_bridge_process(pid):
            print(f"[supervisor] Killing stale wa-bridge (PID {pid}) holding port {port}...")
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            print(f"[supervisor] ERROR: port {port} is in use by PID {pid} (not wa-bridge).")
            print("[supervisor] Free the port, or change BRIDGE_PORT + WA_API_URL in hermes_bot/.env.")
            sys.exit(1)
    for _ in range(20):
        if not _pids_listening_on_port(port):
            return
        time.sleep(0.5)
    print(f"[supervisor] ERROR: port {port} still in use after killing stale bridge. Exiting.")
    sys.exit(1)


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
        resp = requests.post(
            f"{config.BRIDGE_URL}/api/send",
            json={"recipient": "test@s.whatsapp.net", "message": ""},
            timeout=3,
        )
        # 404 means something else is listening on the port (not our bridge)
        return resp.status_code != 404
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
    if config.MECHAT_JID:
        env["MECHAT_JID"] = config.MECHAT_JID
    bridge_port = os.getenv("BRIDGE_PORT", "").strip()
    if bridge_port:
        env["BRIDGE_PORT"] = bridge_port

    _free_bridge_port(_bridge_port())

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
