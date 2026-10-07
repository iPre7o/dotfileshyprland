#!/bin/bash
eth_state=$(LC_ALL=C nmcli -t -f TYPE,STATE dev status | grep '^ethernet' | cut -d: -f2)

icon_1=$(printf '\U000f091f')
icon_2=$(printf '\U000f0922')
icon_3=$(printf '\U000f0925')
icon_4=$(printf '\U000f0928')
icon_eth=$(printf '\U000f0200')
icon_off=$(printf '\U000f05aa')

if [ "$eth_state" = "connected" ]; then
    echo "{\"text\": \"$icon_eth\", \"tooltip\": \"Conectado via cabo\", \"class\": \"ethernet\"}"
    exit 0
fi

read -r ssid signal <<< "$(LC_ALL=C nmcli -t -f active,ssid,signal dev wifi | awk -F: '$1=="yes"{print $2, $3}')"

if [ -z "$ssid" ]; then
    echo "{\"text\": \"$icon_off\", \"tooltip\": \"Desconectado\", \"class\": \"disconnected\"}"
    exit 0
fi

if [ "$signal" -ge 76 ]; then
    icon="$icon_4"
elif [ "$signal" -ge 51 ]; then
    icon="$icon_3"
elif [ "$signal" -ge 26 ]; then
    icon="$icon_2"
else
    icon="$icon_1"
fi

echo "{\"text\": \"$icon\", \"tooltip\": \"$ssid ($signal%)\", \"class\": \"wifi\"}"
