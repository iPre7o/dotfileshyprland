#!/usr/bin/env python3
# Velocidade da rede (down/up) pra waybar: soma todas as interfaces menos lo/virtuais.
import json, subprocess, sys, time

SKIP = ("lo", "docker", "veth", "br-", "virbr", "tun", "wg")


def read():
    rx = tx = 0
    with open("/proc/net/dev") as f:
        for line in f.readlines()[2:]:
            name, data = line.split(":", 1)
            if name.strip().startswith(SKIP):
                continue
            v = data.split()
            rx += int(v[0])
            tx += int(v[8])
    return rx, tx


def human(bps):
    for unit in ("B", "K", "M", "G"):
        if bps < 1000 or unit == "G":
            return f"{bps:.0f}{unit}" if unit == "B" or bps >= 10 else f"{bps:.1f}{unit}"
        bps /= 1024


def connection():
    """Conexão ativa pro tooltip: tipo, nome, interface (e sinal no Wi-Fi)."""
    def nm(*args):
        try:
            return subprocess.run(["nmcli", "-t", *args], capture_output=True, text=True, timeout=3,
                                  env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}).stdout
        except (OSError, subprocess.TimeoutExpired):
            return ""
    kinds = {"802-11-wireless": "Wi-Fi", "802-3-ethernet": "Cabo", "vpn": "VPN", "wireguard": "VPN",
             "gsm": "Dados móveis", "bluetooth": "Bluetooth"}
    lines = []
    for line in nm("-f", "NAME,TYPE,DEVICE", "con", "show", "--active").splitlines():
        name, kind, dev = (line.rsplit(":", 2) + ["", ""])[:3]
        if kind not in kinds:
            continue
        name = name.replace("\\:", ":")
        extra = ""
        if kind == "802-11-wireless":
            sig = next((l.split(":")[-1] for l in nm("-f", "active,signal", "dev", "wifi").splitlines()
                        if l.startswith("yes:")), "")
            extra = f" · sinal {sig}%" if sig else ""
        lines.append(f"{kinds[kind]}: {name} ({dev}){extra}")
    return "\n".join(lines) or "sem conexão"


DOWN, UP = "\U000f01da", "\U000f0552"
prev, last = read(), time.monotonic()
conn, conn_at = connection(), time.monotonic()
while True:
    time.sleep(1)
    cur, now = read(), time.monotonic()
    dt = now - last or 1
    down, up = (cur[0] - prev[0]) / dt, (cur[1] - prev[1]) / dt
    prev, last = cur, now
    text = f"{DOWN}{human(down):<5} {UP}{human(up):<5}"
    if now - conn_at > 10:  # nmcli é lento pra rodar todo segundo
        conn, conn_at = connection(), now
    tip = f"{conn}\n\ndownload: {human(down)}/s\nupload: {human(up)}/s"
    print(json.dumps({"text": text, "tooltip": tip,
                      "class": "active" if down + up > 50 * 1024 else "idle"}, ensure_ascii=False), flush=True)
