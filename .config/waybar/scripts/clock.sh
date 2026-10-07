#!/bin/bash
state_file="$HOME/.cache/waybar-clock-mode"
mode=$(cat "$state_file" 2>/dev/null || echo "date")

if [ "$mode" = "time" ]; then
    text=$(date '+%H:%M:%S')
else
    text=$(LC_TIME=pt_BR.UTF-8 date '+%A, %d de %B')
    text="$(echo "${text:0:1}" | tr '[:lower:]' '[:upper:]')${text:1}"
fi

tooltip=$(LC_TIME=pt_BR.UTF-8 date '+%A, %d de %B de %Y - %H:%M:%S')
tooltip="$(echo "${tooltip:0:1}" | tr '[:lower:]' '[:upper:]')${tooltip:1}"
tooltip="${tooltip}\nClique para abrir o calendário"

echo "{\"text\": \"$text\", \"tooltip\": \"$tooltip\"}"
