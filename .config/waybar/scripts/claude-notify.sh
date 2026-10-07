#!/bin/sh
# módulo custom/claude: mostra o último aviso do Claude Code por até 10 min
f="${XDG_RUNTIME_DIR:-/tmp}/claude-notify"
if [ "$1" = "click" ]; then
    rm -f "$f"
    # tira os avisos do Claude do histórico do dunst (somem do painel também)
    dunstctl history | python3 -c 'import json,sys; [print(n["id"]["data"]) for n in json.load(sys.stdin)["data"][0] if n["summary"]["data"] == "Claude Code"]' 2>/dev/null |
        while read -r id; do dunstctl history-rm "$id"; done
    addr=$(hyprctl clients -j | python3 -c 'import json,sys; c=[w for w in json.load(sys.stdin) if w["class"]=="kitty"]; print(c[0]["address"] if c else "")')
    [ -n "$addr" ] && hyprctl dispatch "hl.dsp.focus({ window = 'address:$addr' })" >/dev/null
    pkill -RTMIN+12 -x waybar
    exit 0
fi
[ -f "$f" ] || { echo '{"text": ""}'; exit 0; }
ts=$(sed -n 1p "$f"); body=$(sed -n 2p "$f" | sed 's/["\\]//g')
if [ $(( $(date +%s) - ts )) -gt 600 ]; then rm -f "$f"; echo '{"text": ""}'; exit 0; fi
echo "{\"text\": \"󰚩 Claude aguardando\", \"tooltip\": \"$body\", \"class\": \"waiting\"}"
