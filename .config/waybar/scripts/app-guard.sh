#!/usr/bin/env bash
# Impede reabrir um app "single instance": se ja existe uma janela cuja
# classe bate com o regex, faz o workspace dela piscar vermelho na waybar
# e foca esse workspace, em vez de lancar um novo processo.
#
# Uso: app-guard.sh '<regex-da-classe>' -- comando args...
#   ex: app-guard.sh '^(discord|vesktop)$' -- vesktop

set -euo pipefail

if [[ "${1:-}" == "" || "${2:-}" != "--" ]]; then
  echo "uso: app-guard.sh '<regex-da-classe>' -- comando args..." >&2
  exit 64
fi

CLASS_REGEX="$1"
shift 2

STATE_DIR="$HOME/.local/state/waybar"
FLASH_FILE="$STATE_DIR/flash.json"
mkdir -p "$STATE_DIR"

MATCH_WS="$(python3 - "$CLASS_REGEX" <<'PY'
import json
import re
import subprocess
import sys

pattern = re.compile(sys.argv[1])
clients = json.loads(subprocess.run(
    ["hyprctl", "-j", "clients"], capture_output=True, text=True
).stdout or "[]")

for c in clients:
    if c.get("mapped") and pattern.search(c.get("class", "")):
        print(c["workspace"]["id"])
        break
PY
)"

if [[ -z "$MATCH_WS" ]]; then
  exec "$@"
fi

python3 - "$MATCH_WS" "$FLASH_FILE" <<'PY'
import json
import os
import sys
import time

ws_id, path = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = json.load(f)
except Exception:
    data = {}
data[ws_id] = time.time() + 3.5
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f)
os.replace(tmp, path)
PY

hyprctl dispatch "hl.dsp.event('flash', '')" >/dev/null
hyprctl dispatch "hl.dsp.focus({ workspace = $MATCH_WS })" >/dev/null
