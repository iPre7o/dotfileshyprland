#!/bin/bash
state_file="$HOME/.cache/waybar-clock-mode"
mode=$(cat "$state_file" 2>/dev/null || echo "date")

if [ "$mode" = "time" ]; then
    echo "date" > "$state_file"
else
    echo "time" > "$state_file"
fi

pkill -RTMIN+8 waybar
