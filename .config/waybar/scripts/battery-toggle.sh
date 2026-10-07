#!/bin/bash
current=$(powerprofilesctl get 2>/dev/null)

case "$current" in
    power-saver) next="performance" ;;
    performance) next="balanced" ;;
    *)           next="power-saver" ;;
esac

powerprofilesctl set "$next"
pkill -RTMIN+9 waybar

case "$next" in
    performance)  label="Desempenho" ;;
    power-saver)  label="Economia de energia" ;;
    *)            label="Equilibrado" ;;
esac

(timeout 2 notify-send -a "Energia" "Modo de energia" "$label" &)
