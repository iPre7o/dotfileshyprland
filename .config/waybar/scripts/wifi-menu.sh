#!/bin/bash
IFACE="wlo1"
THEME_POS="window {location: northeast; anchor: northeast; x-offset: 0px; y-offset: 0px;}"

current_ssid=$(LC_ALL=C nmcli -t -f active,ssid dev wifi | awk -F: '$1=="yes"{print $2}')

mapfile -t networks < <(
    LC_ALL=C nmcli -t -f ssid,signal,security dev wifi list |
    awk -F: '$1!=""' |
    sort -t: -k2 -n -r |
    awk -F: '!seen[$1]++'
)

declare -a lines
declare -A security_of

ICON_LOCK="󰌾"
ICON_UNLOCK="󰍀"
ICON_CHECK="󰄬"
ICON_COG="󰒓"
ICON_DISCONNECT="󰅛"

for entry in "${networks[@]}"; do
    ssid="${entry%%:*}"
    rest="${entry#*:}"
    signal="${rest%%:*}"
    security="${rest#*:}"
    security_of["$ssid"]="$security"

    icon="$ICON_LOCK"
    [ -z "$security" ] && icon="$ICON_UNLOCK"

    mark=""
    [ "$ssid" = "$current_ssid" ] && mark=" $ICON_CHECK"

    lines+=("$icon  $ssid (${signal}%)$mark")
done

menu_extra="$ICON_COG  Configuracoes avancadas"
if [ -n "$current_ssid" ]; then
    menu_extra="$ICON_DISCONNECT  Desconectar
$menu_extra"
fi

chosen=$(printf "%s\n" "${lines[@]}" "$menu_extra" | rofi -dmenu -i -p "Wi-Fi" -theme-str "$THEME_POS window {width: 320px;}")

[ -z "$chosen" ] && exit 0

case "$chosen" in
    *"Configuracoes avancadas"*)
        nm-connection-editor
        exit 0
        ;;
    *"Desconectar"*)
        nmcli device disconnect "$IFACE"
        exit 0
        ;;
esac

ssid=$(echo "$chosen" | sed -E 's/^\S+  //; s/ \([0-9]+%\).*$//')

if nmcli -t -f NAME connection show | grep -qx "$ssid"; then
    nmcli connection up "$ssid"
    exit 0
fi

security="${security_of[$ssid]}"
if [ -z "$security" ]; then
    nmcli device wifi connect "$ssid"
else
    password=$(rofi -dmenu -password -p "Senha de $ssid" -theme-str "$THEME_POS window {width: 320px;}")
    [ -z "$password" ] && exit 0
    nmcli device wifi connect "$ssid" password "$password"
fi
