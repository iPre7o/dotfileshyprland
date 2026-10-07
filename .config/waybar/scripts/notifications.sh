#!/bin/bash
count=$(dunstctl count waiting)
paused=$(dunstctl is-paused)

if [ "$paused" = "true" ]; then
    if [ "$count" -gt 0 ]; then
        echo "{\"text\": \"󰂛\", \"tooltip\": \"$count notificações (Não Perturbe)\", \"class\": \"dnd-notification\"}"
    else
        echo "{\"text\": \"󰂛\", \"tooltip\": \"Não Perturbe ativado\", \"class\": \"dnd-none\"}"
    fi
else
    if [ "$count" -gt 0 ]; then
        echo "{\"text\": \"󱅫\", \"tooltip\": \"$count notificações\", \"class\": \"notification\"}"
    else
        echo "{\"text\": \"󰂜\", \"tooltip\": \"Sem notificações\", \"class\": \"none\"}"
    fi
fi
