#!/usr/bin/env bash
# Renderiza uma "bolinha" de workspace para a waybar (custom/ws-N).
# Uso: ws-button.sh <numero-do-workspace>
set -euo pipefail

WS_ID="$1"
STATE_FILE="$HOME/.local/state/waybar/ws-state.json"

# Workspaces ate esse numero sempre aparecem. Acima disso, so aparecem
# enquanto tiverem alguma janela aberta, estiverem piscando ou voce estiver nelas.
FIXED_COUNT=3

python3 - "$WS_ID" "$STATE_FILE" "$FIXED_COUNT" <<'PY'
import json
import sys

ws_id, state_file, fixed_count = sys.argv[1], sys.argv[2], int(sys.argv[3])

try:
    with open(state_file) as f:
        state = json.load(f)
except Exception:
    state = {}

entry = state.get(ws_id, {"active": False, "occupied": False, "flashing": False})
relevant = entry["occupied"] or entry["flashing"] or entry["active"]

if int(ws_id) > fixed_count and not relevant:
    print(json.dumps({"text": ""}))
    raise SystemExit

classes = []
if entry["active"]:
    classes.append("active")
if entry["occupied"]:
    classes.append("occupied")
if entry["flashing"]:
    classes.append("flashing")
if not classes:
    classes.append("empty")

icon = ws_id
tooltip = f"Workspace {ws_id}"
if entry["flashing"]:
    tooltip = f"Workspace {ws_id} - app ja aberto aqui"

print(json.dumps({"text": icon, "class": classes, "tooltip": tooltip, "alt": ws_id}))
PY
