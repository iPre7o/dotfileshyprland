#!/bin/sh
# Histórico da área de transferência (cliphist) num menu do rofi.
# Uso: clipboard-menu.sh        -> no meio da tela (SUPER+V)
#      clipboard-menu.sh bar    -> embaixo do ícone na waybar
# Enter copia o item de novo · Shift+Delete apaga o item · Alt+Delete limpa tudo

pkill -x rofi && exit 0  # clicar de novo fecha

if ! command -v cliphist >/dev/null; then
    notify-send -a "Área de transferência" "cliphist não instalado" "sudo pacman -S cliphist"
    exit 1
fi

place=""
[ "$1" = "bar" ] && place='window { location: north east; anchor: north east; x-offset: 0px; y-offset: 0px; width: 460px; border: 0px 0px 2px 2px; border-radius: 0px 0px 0px 10px; background-color: #000000; }'

while :; do
    # "[[ binary data 118 KiB png 690x390 ]]" -> "󰋩  imagem 690×390 · png · 118 KiB"
    # (o id na frente fica igual, é por ele que o cliphist acha o item)
    choice=$(cliphist list | sed -E 's/\[\[ binary data ([0-9.]+ [KMG]?i?B) ([a-z]+) ([0-9]+)x([0-9]+) \]\]/󰋩  imagem \3×\4 · \2 · \1/' | rofi -dmenu -i -p "󰅍" -display-columns 2 \
        -theme-str "$place entry { placeholder: \"Buscar no que foi copiado...\"; }" \
        -mesg "Enter copia · Shift+Del apaga · Alt+Del limpa tudo" \
        -kb-delete-entry "" -kb-custom-1 "shift+Delete" -kb-custom-2 "alt+Delete")
    code=$?
    case $code in
        0)  [ -n "$choice" ] && printf '%s' "$choice" | cliphist decode | wl-copy; exit 0 ;;
        10) printf '%s' "$choice" | cliphist delete ;;  # apaga e reabre o menu
        11) cliphist wipe; notify-send -a "Área de transferência" "Histórico limpo"; exit 0 ;;
        *)  exit 0 ;;
    esac
done
