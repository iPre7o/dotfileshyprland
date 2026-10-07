#!/bin/bash
THEME_POS="window {location: northeast; anchor: northeast; x-offset: 0px; y-offset: 0px;}"
ROFI_STR="$THEME_POS window {width: 320px;}"

ICON_BT="󰂯"
ICON_BT_OFF="󰂲"
ICON_CHECK="󰄬"
ICON_SCAN="󰑐"
ICON_DISCONNECT="󰅛"
ICON_TRASH="󰩹"

icon_for_device() {
    case "$1" in
        *audio-headset*|*audio-headphones*) printf '\U000f02cb' ;;
        *audio-card*|*audio-speakers*)      printf '\U000f04c3' ;;
        *input-keyboard*)                   printf '\U000f030c' ;;
        *input-mouse*|*input-tablet*)       printf '\U000f037d' ;;
        *input-gaming*)                     printf '\U000f0eb5' ;;
        *phone*)                            printf '\U000f03f2' ;;
        *computer*)                         printf '\U000f0322' ;;
        *printer*)                          printf '\U000f042a' ;;
        *camera*|*video*)                   printf '\U000f0567' ;;
        *watch*)                            printf '\U000f0bb6' ;;
        *)                                  printf '\U000f00af' ;;
    esac
}

if ! bluetoothctl show | grep -q "Powered: yes"; then
    chosen=$(printf "%s\n" "$ICON_BT  Ligar Bluetooth" | rofi -dmenu -i -p "Bluetooth" -theme-str "$ROFI_STR listview {lines: 1;}")
    [ -z "$chosen" ] && exit 0
    bluetoothctl power on
    exit 0
fi

# procura por novos dispositivos em segundo plano para a proxima abertura
setsid bluetoothctl --timeout 10 scan on >/dev/null 2>&1 &

mapfile -t connected < <(bluetoothctl devices Connected | awk '{print $2}')
mapfile -t paired < <(bluetoothctl devices Paired | awk '{print $2}')
mapfile -t all < <(bluetoothctl devices | awk '{print $2}')

is_in() {
    local needle="$1"; shift
    local item
    for item in "$@"; do
        [ "$item" = "$needle" ] && return 0
    done
    return 1
}

declare -a lines
declare -A mac_of
declare -A state_of

for mac in "${connected[@]}" "${paired[@]}" "${all[@]}"; do
    [ -z "$mac" ] && continue
    [ -n "${state_of[$mac]}" ] && continue

    info=$(bluetoothctl info "$mac")
    name=$(awk -F': ' '/^\tName:/{print $2; exit}' <<< "$info")
    [ -z "$name" ] && name="$mac"
    icon=$(icon_for_device "$(awk -F': ' '/^\tIcon:/{print $2; exit}' <<< "$info")")

    if is_in "$mac" "${connected[@]}"; then
        state_of["$mac"]="connected"
        label="$icon  $name (conectado) $ICON_CHECK"
    elif is_in "$mac" "${paired[@]}"; then
        state_of["$mac"]="paired"
        label="$icon  $name (pareado)"
    else
        state_of["$mac"]="new"
        label="$icon  $name"
    fi

    mac_of["$label"]="$mac"
    lines+=("$label")
done

menu_extra="$ICON_SCAN  Procurar dispositivos
$ICON_BT_OFF  Desligar Bluetooth"

if [ "${#connected[@]}" -gt 0 ]; then
    menu_extra="$ICON_DISCONNECT  Desconectar tudo
$menu_extra"
fi

chosen=$(printf "%s\n" "${lines[@]}" "$menu_extra" | rofi -dmenu -i -p "Bluetooth" -theme-str "$ROFI_STR")

[ -z "$chosen" ] && exit 0

case "$chosen" in
    *"Procurar dispositivos"*)
        notify-send -a Bluetooth "Bluetooth" "Procurando dispositivos..."
        bluetoothctl --timeout 8 scan on >/dev/null 2>&1
        exec "$0"
        ;;
    *"Desligar Bluetooth"*)
        bluetoothctl power off
        exit 0
        ;;
    *"Desconectar tudo"*)
        for mac in "${connected[@]}"; do
            bluetoothctl disconnect "$mac" >/dev/null
        done
        exit 0
        ;;
esac

mac="${mac_of[$chosen]}"
[ -z "$mac" ] && exit 0

name=$(sed -E 's/^\S+  //; s/ \((conectado|pareado)\).*$//' <<< "$chosen")

case "${state_of[$mac]}" in
    connected)
        action=$(printf "%s\n" "$ICON_DISCONNECT  Desconectar" "$ICON_TRASH  Remover dispositivo" |
            rofi -dmenu -i -p "$name" -theme-str "$ROFI_STR listview {lines: 2;}")
        case "$action" in
            *Desconectar*) bluetoothctl disconnect "$mac" >/dev/null ;;
            *Remover*)     bluetoothctl remove "$mac" >/dev/null ;;
        esac
        ;;
    paired)
        action=$(printf "%s\n" "$ICON_BT  Conectar" "$ICON_TRASH  Remover dispositivo" |
            rofi -dmenu -i -p "$name" -theme-str "$ROFI_STR listview {lines: 2;}")
        case "$action" in
            *Conectar*)
                if bluetoothctl connect "$mac" >/dev/null; then
                    notify-send -a Bluetooth "Bluetooth" "Conectado a $name"
                else
                    notify-send -a Bluetooth -u critical "Bluetooth" "Falha ao conectar a $name"
                fi
                ;;
            *Remover*) bluetoothctl remove "$mac" >/dev/null ;;
        esac
        ;;
    new)
        notify-send -a Bluetooth "Bluetooth" "Pareando com $name..."
        if bluetoothctl pair "$mac" >/dev/null; then
            bluetoothctl trust "$mac" >/dev/null
            if bluetoothctl connect "$mac" >/dev/null; then
                notify-send -a Bluetooth "Bluetooth" "Conectado a $name"
            else
                notify-send -a Bluetooth -u critical "Bluetooth" "Pareado, mas falha ao conectar a $name"
            fi
        else
            notify-send -a Bluetooth -u critical "Bluetooth" "Falha ao parear com $name"
        fi
        ;;
esac
