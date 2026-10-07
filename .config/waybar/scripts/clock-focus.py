#!/usr/bin/env python3
"""custom/clock da waybar: horas e, com o timer de foco do painel em andamento,
o tempo que falta. Lê o estado que o welcome.py salva em focus.json.
Clique esquerdo = play/pause do foco (SIGUSR1 pro painel); direito = calendário."""
import datetime
import json
import locale
import os
import sys
import time

FOCUS_FILE = os.path.expanduser("~/.local/share/welcome/focus.json")
MINUTES = {"focus": 25, "short": 5, "long": 15}  # igual ao FOCUS_MINUTES do welcome.py
NAMES = {"focus": "foco", "short": "pausa", "long": "pausa longa"}
ICONS = {"focus": "\U000f13ab", "short": "\U000f0176", "long": "\U000f0176"}  # alvo / xícara

try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    pass


def focus_state():
    try:
        with open(FOCUS_FILE) as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None
    phase = state.get("phase", "focus")
    total = MINUTES.get(phase, 25) * 60
    if state.get("running"):
        left = max(0, int(round(state.get("ends", 0) - time.time())))
    else:
        left = int(state.get("left", total))
        if left >= total:
            return None  # parado no começo: não mostra nada
    return phase, left, bool(state.get("running"))


def line():
    now = datetime.datetime.now()
    text = now.strftime("%H:%M")
    date = now.strftime("%A, %d de %B de %Y").capitalize()
    cls = "idle"
    tooltip = f"{date}\nclique: começar foco · direito: calendário"
    st = focus_state()
    if st:
        phase, left, running = st
        timer = f"{left // 60:02d}:{left % 60:02d}"
        icon = ICONS.get(phase, "") if running else "\U000f03e4"  # pausado
        text += f"   {icon} {timer}"
        cls = phase if running else "paused"
        tooltip = (f"{date}\n{NAMES.get(phase, phase)} {'em andamento' if running else 'pausado'}"
                   f" · faltam {timer}\nclique: {'pausar' if running else 'continuar'} · direito: calendário")
    return json.dumps({"text": text, "tooltip": tooltip, "class": cls})


while True:
    try:
        print(line(), flush=True)
    except BrokenPipeError:
        sys.exit(0)
    time.sleep(1 - (time.time() % 1) + 0.02)  # vira junto com o segundo
