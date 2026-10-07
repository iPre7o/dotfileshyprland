#!/bin/bash
options="󰐥  Desligar
󰜉  Reiniciar
󰒲  Suspender
󰍃  Sair"

chosen=$(echo -e "$options" | rofi -dmenu -i -p "Energia" -theme-str "window {width: 240px;} listview {lines: 4;}")

case "$chosen" in
    *Desligar*) systemctl poweroff ;;
    *Reiniciar*) systemctl reboot ;;
    *Suspender*) systemctl suspend ;;
    *Sair*) hyprctl dispatch exit ;;
esac
