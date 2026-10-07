#!/usr/bin/env bash
# Fecha a janela ativa (ALT+F4 / SUPER+Return).
# Exceção: o Spotify não fecha — vai pra área escondida "special:music" e
# continua tocando; o player no fundo da área de trabalho traz ele de volta.
class=$(hyprctl activewindow -j | python3 -c 'import json,sys; print(json.load(sys.stdin).get("class", ""))')

case "$class" in
    Spotify|spotify)
        ws=$(hyprctl activeworkspace -j | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
        hyprctl dispatch 'hl.dsp.window.move({ workspace = "special:music", follow = false })' >/dev/null
        # devolve o foco pra última janela usada nesse workspace (se tiver)
        prev=$(hyprctl clients -j | python3 -c '
import json, sys
ws = int(sys.argv[1])
wins = [c for c in json.load(sys.stdin) if c["workspace"]["id"] == ws and c["mapped"]]
wins.sort(key=lambda c: c["focusHistoryID"])
print(wins[0]["address"] if wins else "")' "$ws")
        if [ -n "$prev" ]; then
            hyprctl dispatch "hl.dsp.focus({ window = 'address:$prev' })" >/dev/null
        else
            hyprctl dispatch "hl.dsp.focus({ workspace = $ws })" >/dev/null
        fi
        ;;
    *)
        hyprctl dispatch 'hl.dsp.window.close()' >/dev/null
        ;;
esac
