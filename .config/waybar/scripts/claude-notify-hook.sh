#!/bin/sh
# chamado pelo dunst (regra [claude-code]): guarda o aviso e acorda o módulo da waybar
printf '%s\n%s\n' "$(date +%s)" "$3" > "${XDG_RUNTIME_DIR:-/tmp}/claude-notify"
pkill -RTMIN+12 -x waybar
