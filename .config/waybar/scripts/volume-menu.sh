#!/bin/bash
SCRIPT="$HOME/.config/waybar/scripts/volume-mixer.py"

if pgrep -f "python3 $SCRIPT" >/dev/null; then
    pkill -f "python3 $SCRIPT"
    exit 0
fi

python3 "$SCRIPT" &
