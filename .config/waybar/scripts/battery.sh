#!/bin/bash
BAT=/sys/class/power_supply/BAT1

capacity=$(cat "$BAT/capacity" 2>/dev/null || echo 0)
status=$(cat "$BAT/status" 2>/dev/null || echo "Unknown")
profile=$(powerprofilesctl get 2>/dev/null)

case "$profile" in
    performance)
        profile_icon=""
        profile_label="Desempenho"
        ;;
    power-saver)
        profile_icon=""
        profile_label="Economia de energia"
        ;;
    *)
        profile_icon=""
        profile_label="Equilibrado"
        ;;
esac

if [ "$status" = "Charging" ]; then
    battery_icon="󰂄"
elif [ "$capacity" -lt 20 ]; then
    battery_icon="󰂎"
elif [ "$capacity" -lt 40 ]; then
    battery_icon="󰁻"
elif [ "$capacity" -lt 60 ]; then
    battery_icon="󰁽"
elif [ "$capacity" -lt 80 ]; then
    battery_icon="󰁿"
else
    battery_icon="󰂁"
fi

class="$profile"
if [ "$capacity" -le 10 ] && [ "$status" != "Charging" ]; then
    class="critical"
elif [ "$capacity" -le 25 ] && [ "$status" != "Charging" ]; then
    class="warning"
fi

text="${profile_icon} ${battery_icon} ${capacity}%"
tooltip="Bateria: ${capacity}% (${status})\nModo de energia: ${profile_label}\nClique para trocar o modo"

printf '{"text": "%b", "tooltip": "%s", "class": "%s"}\n' "$text" "$tooltip" "$class"
