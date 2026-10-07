#!/usr/bin/env python3
"""Daemon que mantem o estado dos workspaces (ativo/ocupado/piscando)
para os modulos custom/ws-N da waybar, e sinaliza a waybar quando muda.

Estado escrito em ~/.local/state/waybar/ws-state.json.
Pisca ("flash") sao pedidas por app-guard.sh escrevendo em
~/.local/state/waybar/flash.json e disparando o evento IPC 'flash'.
"""
import json
import os
import socket
import subprocess
import threading
import time

STATE_DIR = os.path.expanduser("~/.local/state/waybar")
STATE_FILE = os.path.join(STATE_DIR, "ws-state.json")
FLASH_FILE = os.path.join(STATE_DIR, "flash.json")
WS_COUNT = 10
SIGNAL_NUM = 11  # SIGRTMIN+11, ver config.jsonc dos custom/ws-N
FLASH_SECONDS = 3.5
DEBOUNCE_SECONDS = 0.12

os.makedirs(STATE_DIR, exist_ok=True)
_lock = threading.Lock()
_pending_timer = None


def hyprctl_json(*args):
    out = subprocess.run(["hyprctl", "-j", *args], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except Exception:
        return None


def load_flash():
    try:
        with open(FLASH_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_flash(data):
    tmp = FLASH_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, FLASH_FILE)


def refresh(signal_waybar=True):
    with _lock:
        active = hyprctl_json("activeworkspace") or {}
        active_id = active.get("id")

        workspaces = hyprctl_json("workspaces") or []
        occupied = {w["id"] for w in workspaces if w.get("windows", 0) > 0}

        flash = load_flash()
        now = time.time()
        changed = False
        for ws_id in list(flash.keys()):
            if flash[ws_id] <= now:
                del flash[ws_id]
                changed = True
        if changed:
            save_flash(flash)

        state = {}
        for i in range(1, WS_COUNT + 1):
            state[str(i)] = {
                "active": i == active_id,
                "occupied": i in occupied,
                "flashing": str(i) in flash,
            }

        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, STATE_FILE)

        # reagenda um refresh para quando o proximo flash expirar
        if flash:
            next_expiry = min(flash.values())
            schedule_refresh_at(next_expiry)

    if signal_waybar:
        subprocess.run(["pkill", f"-SIGRTMIN+{SIGNAL_NUM}", "waybar"])


def schedule_refresh_at(epoch_time):
    global _pending_timer
    delay = max(0.05, epoch_time - time.time() + 0.05)
    if _pending_timer is not None:
        _pending_timer.cancel()
    _pending_timer = threading.Timer(delay, refresh)
    _pending_timer.daemon = True
    _pending_timer.start()


def debounced_refresh():
    global _pending_timer
    if _pending_timer is not None:
        _pending_timer.cancel()
    _pending_timer = threading.Timer(DEBOUNCE_SECONDS, refresh)
    _pending_timer.daemon = True
    _pending_timer.start()


def socket2_path():
    runtime = os.environ["XDG_RUNTIME_DIR"]
    sig = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
    return f"{runtime}/hypr/{sig}/.socket2.sock"


def listen_loop():
    path = socket2_path()
    while True:
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(path)
            buf = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    debounced_refresh()
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            pass
        time.sleep(1)


if __name__ == "__main__":
    refresh(signal_waybar=False)
    listen_loop()
