#!/usr/bin/env python3
# Tela de boas-vindas no lugar do wallpaper (estilo console do Claude).
# Fica na camada "background" do Wayland: aparece sempre que o workspace está vazio.
# Digitar filtra os apps instalados; ↑/↓ escolhe, Enter abre, Esc limpa.
# Com --menu vira o launcher do SUPER+Q: abre por cima das janelas e fecha
# ao abrir um app, apertar Esc ou clicar fora (rodar de novo também fecha).

import datetime
import glob
import hashlib
import json
import os
import random
import re
import shutil
import socket
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, GtkLayerShell, Pango  # noqa: E402

try:
    gi.require_version("GioUnix", "2.0")
    from gi.repository.GioUnix import DesktopAppInfo  # noqa: E402
except (ValueError, ImportError):
    DesktopAppInfo = Gio.DesktopAppInfo

try:  # player de música (pacote playerctl)
    gi.require_version("Playerctl", "2.0")
    from gi.repository import Playerctl  # noqa: E402
except (ValueError, ImportError):
    Playerctl = None

NAME = "Gabryel"
WALLPAPER = os.path.expanduser("~/.config/hypr/assets/wallpaper.png")
GHOST = os.path.expanduser("~/.config/hypr/assets/arch.svg")
GHOST_SIZE = 120
MAX_RESULTS = 7
WEB_SEARCH = "https://www.google.com/search?q="
ICON_SIZE = 32      # px, igual pra todo app (ícones SVG/grandes não estouram)
ROW_HEIGHT = 50     # altura fixa de cada resultado
MENU_WIDTH = 760    # largura fixa do conteúdo (menu do SUPER+Q)
DESK_WIDTH = 640    # no fundo, menor pra sobrar o mesmo respiro dos dois lados das colunas
WAYBAR_HEIGHT = 32  # o painel lateral começa logo abaixo da waybar
PANEL_WIDTH = 280   # largura da coluna da direita
PANEL_BOTTOM = 16   # folga entre as colunas laterais e a borda de baixo
ART_SIZE = 76       # capa do álbum no player
ART_CACHE = os.path.expanduser("~/.cache/welcome-art")
WAYBAR_SCRIPTS = os.path.expanduser("~/.config/waybar/scripts")
TERMINAL = "kitty"
FILE_MANAGER = "thunar"
TODO_FILE = os.path.expanduser("~/.local/share/welcome/todo.json")  # antigo; migra pro Obsidian
TODO_NOTE = "✅ Tarefas.md"  # nota no cofre do Obsidian (OBSIDIAN_VAULT) com as tarefas
TODO_MIN_HEIGHT = 80   # a lista rola quando não cabe no espaço até o status
WEATHER_PLACE = None  # ex.: {"city": "Goiânia", "region": "Goiás", "lat": -16.68, "lon": -49.26}; None = pelo IP
WEATHER_CACHE = os.path.expanduser("~/.cache/welcome-weather.json")
FAVORITES_FILE = os.path.expanduser("~/.local/share/welcome/favorites.json")
FAV_DEFAULTS = ["firefox.desktop", "kitty.desktop", "thunar.desktop", "com.microsoft.VSCode.desktop",
                "spotify-launcher.desktop", "obsidian.desktop", "vesktop.desktop", "steam.desktop"]
FAV_COLUMNS = 9  # embaixo da barra de input cabe uma fileira inteira
FAV_ICON_SIZE = 32
FAV_TILE_WIDTH = 64  # largura fixa de cada atalho (a fileira fica centralizada)
FAV_RESULTS = 6
OBSIDIAN_VAULT = os.path.expanduser("~/Obsidian Vault")
OBSIDIAN_CAPTURE = "00 INBOX/⚡ Capturas rápidas.md"  # relativo ao cofre
OBSIDIAN_INBOX = "00 INBOX/📥 Inbox.md"  # ganha um link pras capturas na primeira vez
OBSIDIAN_RECENT = 4  # notas editadas recentemente mostradas embaixo
FOCUS_FILE = os.path.expanduser("~/.local/share/welcome/focus.json")
FOCUS_MINUTES = {"focus": 25, "short": 5, "long": 15}  # foco, pausa curta, pausa longa
FOCUS_LONG_EVERY = 4  # a cada 4 focos a pausa é longa
FOCUS_SOUND = "/usr/share/sounds/freedesktop/stereo/complete.oga"
DESKTOP_VISIBLE = [True]  # falso quando tem janela na frente (pausa as leituras)
MENU_MODE = "--menu" in sys.argv
DESK_PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "welcome-desk.pid")  # waybar manda SIGUSR1 = play/pause do foco
MENU_PIDFILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "welcome-menu.pid")

# Mesmas cores do rofi/waybar/kitty (preto e branco)
BG, BG_ALT, FG, FG_MUTED, ACCENT = "#000000", "#141414", "#ffffff", "#888888", "#eeeeee"

CSS = f"""
window {{
    background-color: {BG};
    background-image: linear-gradient(rgba(0,0,0,0.82), rgba(0,0,0,0.82)), url("file://{WALLPAPER}");
    background-size: cover;
    background-position: center;
}}
window.menu {{
    background-color: rgba(0,0,0,0.78);
    background-image: none;
}}
* {{ font-family: "JetBrainsMono Nerd Font", monospace; }}
#welcome {{ color: {FG}; font-size: 15px; font-weight: bold; }}
#greeting {{ color: {FG}; font-size: 26px; }}
#prompt-box {{
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 4px 12px;
    background-color: rgba(20,20,20,0.8);
}}
#prompt {{ color: {ACCENT}; font-size: 20px; font-weight: bold; }}
entry {{
    background: transparent;
    border: none;
    box-shadow: none;
    color: {FG};
    caret-color: {FG};
    font-size: 18px;
    padding: 6px 4px;
}}
list, row {{ background: transparent; }}
row {{ padding: 8px 10px; border-radius: 8px; }}
row:selected {{ background-color: {ACCENT}; }}
.app-name {{ color: {FG}; font-size: 15px; }}
.app-desc {{ color: {FG_MUTED}; font-size: 12px; }}
.arrow {{ color: {FG}; font-size: 15px; font-weight: bold; }}
.action-icon {{ color: {FG}; font-size: 24px; }}
row:selected .action-icon {{ color: #000000; }}
row:selected .app-name, row:selected .arrow {{ color: #000000; }}
row:selected .app-desc {{ color: #444444; }}
#empty {{ color: {FG_MUTED}; font-size: 13px; padding: 8px 10px; }}
#hints-bar {{ margin-bottom: 10px; }}
.hint-chip {{
    color: {FG_MUTED};
    font-size: 11px;
    padding: 2px 7px;
}}
.hint-key {{
    color: {ACCENT};
    font-weight: bold;
}}

/* painel lateral colado na waybar: relógio, calendário e player */
#side-panel {{
    background: none;
    border: none;
    padding: 14px 16px 12px 16px;
}}
#side-panel separator {{ background: none; min-height: 0; margin: 9px 0; }}
#cal-time {{ color: {FG}; font-size: 34px; font-weight: bold; }}
#cal-secs {{ color: {FG_MUTED}; font-size: 18px; }}
#cal-date {{ color: {FG_MUTED}; font-size: 13px; }}
#side-panel button {{
    background: none;
    border: none;
    box-shadow: none;
    outline: none;
    padding: 0;
    min-width: 30px;
    min-height: 24px;
    border-radius: 6px;
    color: {FG};
    font-size: 13px;
}}
#side-panel button:hover {{ background-color: rgba(255,255,255,0.12); }}
#side-panel button.nav {{ color: {FG_MUTED}; font-size: 16px; }}
#side-panel button.nav:hover {{ color: {FG}; }}
#side-panel button#cal-title {{ font-size: 14px; font-weight: bold; padding: 0 8px; }}
#side-panel grid button {{ color: #aaaaaa; }}
#side-panel button.other {{ color: #444444; }}
#side-panel button.selected {{ background-color: rgba(255,255,255,0.08); }}
#side-panel button.today {{ color: {FG}; font-weight: bold; text-decoration: underline; }}
.cal-wday {{ color: {FG_MUTED}; font-size: 11px; }}

#todo entry {{ font-size: 13px; padding: 4px 0; color: {FG}; }}
.sysinfo-key {{ color: {FG}; font-size: 12px; font-weight: bold; }}
.sysinfo-val {{ color: {FG_MUTED}; font-size: 12px; }}
.todo-head {{ color: #666666; font-size: 9px; font-weight: bold; }}
.todo-plus {{ color: {FG_MUTED}; font-size: 14px; }}
.todo-row {{ padding: 5px 0; }}
.todo-check {{ color: {FG}; font-size: 16px; }}
.todo-check.done {{ color: {FG_MUTED}; }}
.todo-text {{ color: {FG}; font-size: 13px; }}
.todo-text.done {{ color: #555555; }}
#side-panel button.todo-del {{ color: {FG_MUTED}; font-size: 12px; min-width: 20px; min-height: 18px; }}
#side-panel button.todo-del:hover {{ color: {FG}; background: none; }}
#player-art {{ border: none; }}
#weather-place {{ color: {FG_MUTED}; font-size: 12px; }}
#weather-icon {{ color: {FG}; font-size: 40px; }}
#weather-temp {{ color: {FG}; font-size: 40px; font-weight: bold; }}
#weather-desc {{ color: {FG}; font-size: 13px; }}
.weather-muted {{ color: {FG_MUTED}; font-size: 11px; }}
.weather-day {{ color: #666666; font-size: 10px; font-weight: bold; }}
.weather-day-icon {{ color: {FG}; font-size: 18px; }}
#side-panel button.notif-clear {{ color: #666666; font-size: 10px; min-height: 0; min-width: 0; padding: 0 2px; }}
#side-panel button.notif-clear:hover {{ color: {FG}; background: none; }}
#capture entry {{ font-size: 13px; padding: 4px 0; color: {FG}; }}
#side-panel button.note {{ padding: 3px 0; min-height: 0; }}
.note-name {{ color: #aaaaaa; font-size: 12px; }}
#side-panel button.note:hover .note-name {{ color: {FG}; }}
.note-age {{ color: #555555; font-size: 10px; }}
#focus-time {{ color: {FG}; font-size: 30px; font-weight: bold; }}
#focus-time.paused {{ color: {FG_MUTED}; }}
.focus-phase {{ color: {FG_MUTED}; font-size: 12px; }}
.focus-dots {{ color: {FG_MUTED}; font-size: 10px; }}
.notif-row {{ padding: 6px 0; }}
.notif-summary {{ color: {FG}; font-size: 12px; font-weight: bold; }}
.notif-body {{ color: {FG_MUTED}; font-size: 11px; }}
.notif-time {{ color: #555555; font-size: 10px; }}
.notif-empty {{ color: #555555; font-size: 12px; padding: 4px 0; }}
#favorites flowboxchild {{ padding: 0; }}
#favorites button {{
    background: none;
    border: none;
    box-shadow: none;
    outline: none;
    padding: 0;
    min-width: 30px;
    min-height: 24px;
    border-radius: 6px;
    color: {FG};
    font-size: 13px;
}}
#favorites button:hover, #favorites button.kbd {{ background-color: rgba(255,255,255,0.12); }}
#favorites button.fav.kbd .fav-name {{ color: {FG}; }}
#side-panel button.kbd, #side-panel box.kbd {{ background-color: rgba(255,255,255,0.10); border-radius: 6px; }}
#side-panel entry.kbd, #side-panel scale.kbd {{ background-color: rgba(255,255,255,0.10); border-radius: 6px; }}
#favorites button.nav {{ color: {FG_MUTED}; font-size: 16px; }}
#favorites button.nav:hover {{ color: {FG}; }}
#favorites button.fav {{ padding: 6px 0; min-width: 0; }}
.fav-name {{ color: {FG_MUTED}; font-size: 10px; }}
#favorites button.fav:hover .fav-name {{ color: {FG}; }}
.fav-plus {{ color: #555555; font-size: 24px; }}
#favorites button.fav-result {{ padding: 6px 4px; min-height: 0; }}
#favorites entry {{ font-size: 13px; padding: 4px 0; color: {FG}; }}
#player-placeholder {{ color: #555555; font-size: 44px; }}
#player-title {{ color: {FG}; font-size: 13px; font-weight: bold; }}
#player-artist {{ color: {FG_MUTED}; font-size: 12px; }}
.player-time {{ color: {FG_MUTED}; font-size: 10px; }}
#side-panel button.ctrl {{ font-size: 15px; min-width: 32px; min-height: 26px; }}
#side-panel button.ctrl.main {{ font-size: 18px; }}
#side-panel button.ctrl.on {{ color: {FG}; }}
#side-panel button.ctrl.off {{ color: #555555; }}
#side-panel button.source {{ color: #555555; font-size: 11px; padding: 0 6px; min-height: 20px; }}
#side-panel button.source.current {{ color: {FG}; font-weight: bold; }}
#side-panel button.tile {{ min-height: 40px; padding: 2px 0; }}
.tile-icon {{ font-size: 18px; }}
.tile-text {{ font-size: 10px; color: {FG_MUTED}; }}
#side-panel button.tile.on .tile-icon {{ color: {FG}; }}
#side-panel button.tile.off .tile-icon, #side-panel button.tile.off .tile-text {{ color: #555555; }}
#side-panel button.slider-icon {{ font-size: 16px; min-width: 24px; min-height: 22px; color: {FG}; }}
#side-panel button.slider-icon.off {{ color: #555555; }}
.slider-pct {{ color: {FG_MUTED}; font-size: 11px; }}
#side-panel button.stat {{ padding: 4px; min-height: 0; }}
.stat-title {{ color: #666666; font-size: 9px; font-weight: bold; }}
.stat-value {{ color: {FG}; font-size: 12px; font-weight: bold; }}
#side-panel button.stat.alert .stat-value {{ color: #f7768e; }}
#stats scale, #stats scale trough, #player scale, #player scale trough {{ min-width: 0; }}
#stats scale, #player scale {{ padding: 0; margin: 0; }}
#stats scale trough {{ background-color: rgba(255,255,255,0.15); min-height: 3px; border: none; border-radius: 2px; }}
#stats scale highlight {{ background-color: {FG}; border: none; border-radius: 2px; }}
#stats scale slider {{ background: {FG}; border: none; box-shadow: none; min-width: 9px; min-height: 9px; margin: -4px; border-radius: 50%; }}
#player scale trough {{ background-color: rgba(255,255,255,0.15); min-height: 3px; border: none; border-radius: 2px; }}
#player scale highlight {{ background-color: {FG}; border: none; border-radius: 2px; }}
#player scale slider {{ background: {FG}; border: none; box-shadow: none; min-width: 9px; min-height: 9px; margin: -4px; border-radius: 50%; }}
"""

MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]
WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
            "sexta-feira", "sábado", "domingo"]  # ordem do date.weekday()
WEEK_HEADER = ["D", "S", "T", "Q", "Q", "S", "S"]  # semana começa no domingo


# Frases sorteadas a cada vez que a tela aparece ({n} = seu nome)
GREETINGS = [
    "O que vamos fazer hoje, {n}?",
    "Bora, {n}. O que vai ser?",
    "No que posso te ajudar, {n}?",
    "Qual é o plano agora, {n}?",
    "Manda, {n}. O que vamos abrir?",
    "Pronto quando você estiver, {n}.",
    "E aí, {n}, o que vem agora?",
    "Por onde começamos, {n}?",
    "O que você tem em mente, {n}?",
    "Vamos nessa, {n}. Qual app?",
    "Mais uma missão, {n}?",
    "Diz aí, {n}: o que a gente faz?",
    "Hora de produzir, {n}?",
    "Qual vai ser a boa, {n}?",
    "Tô ouvindo, {n}. Digita aí.",
]
GREETINGS_BY_TIME = {
    "manha": ["Café já tomou, {n}? O que vamos fazer?", "Começando o dia, {n}?"],
    "tarde": ["Como tá a tarde, {n}? O que agora?", "Seguindo firme, {n}?"],
    "noite": ["Ainda por aqui, {n}? O que vamos fazer?", "Sessão noturna, {n}?",
              "Só mais uma coisinha, {n}?"],
}
LAST_GREETING_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "welcome-last-greeting")


def period():
    hour = GLib.DateTime.new_now_local().get_hour()
    if 5 <= hour < 12:
        return "manha"
    if 12 <= hour < 18:
        return "tarde"
    return "noite"


def header_text():
    salut = {"manha": "Bom dia", "tarde": "Boa tarde", "noite": "Boa noite"}[period()]
    return f"{salut}, {NAME}!"


def greeting_text():
    # sorteia uma frase diferente da última (vale entre o menu e o fundo)
    pool = GREETINGS + GREETINGS_BY_TIME[period()]
    try:
        with open(LAST_GREETING_FILE) as f:
            last = f.read()
    except OSError:
        last = ""
    choice = random.choice([g for g in pool if g != last] or pool)
    try:
        with open(LAST_GREETING_FILE, "w") as f:
            f.write(choice)
    except OSError:
        pass
    return choice.format(n=NAME)


def load_apps():
    apps = []
    for info in Gio.AppInfo.get_all():
        if not info.should_show() or not isinstance(info, DesktopAppInfo):
            continue
        keywords = " ".join(info.get_keywords() or [])
        apps.append({
            "info": info,
            "name": info.get_display_name() or info.get_name(),
            "desc": info.get_description() or info.get_generic_name() or "",
            "search": " ".join(filter(None, [
                info.get_executable() or "", keywords, info.get_generic_name() or "",
            ])).lower(),
        })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def score(app, query):
    name = app["name"].lower()
    if name.startswith(query):
        return 0
    if any(w.startswith(query) for w in name.split()):
        return 1
    if query in name:
        return 2
    if query in app["search"]:
        return 3
    # subsequência ("vsc" -> "Visual Studio Code")
    it = iter(name)
    if all(c in it for c in query):
        return 4
    return None


class DeskCalendar(Gtk.Box):
    """Relógio + calendário fixo no canto superior direito do fundo.
    ‹ › ou rolar o mouse troca o mês, clicar no título volta pra hoje,
    clicar num dia mostra quanto falta (ou quanto passou)."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        self.today = datetime.date.today()
        self.view = self.today.replace(day=1)
        self.selected = self.today

        clock = Gtk.Box()
        self.time = Gtk.Label(xalign=0)
        self.time.set_name("cal-time")
        self.secs = Gtk.Label(xalign=0)
        self.secs.set_name("cal-secs")
        self.secs.set_valign(Gtk.Align.END)
        self.secs.set_margin_bottom(8)
        clock.pack_start(self.time, False, False, 0)
        clock.pack_start(self.secs, False, False, 2)
        self.date = Gtk.Label(xalign=0)
        self.date.set_name("cal-date")
        # relógio + data ficam fora do calendário (o painel deixa eles sempre à mostra)
        self.header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.header.set_margin_bottom(14)
        self.header.pack_start(clock, False, False, 0)
        self.header.pack_start(self.date, False, False, 0)

        nav = Gtk.Box()
        prev = self._button("‹", lambda *_: self.shift(-1), "nav")
        nxt = self._button("›", lambda *_: self.shift(1), "nav")
        self.title = self._button("", lambda *_: self.go_today())
        self.title.set_name("cal-title")
        self.title.set_tooltip_text("voltar pra hoje")
        nav.pack_start(prev, False, False, 0)
        nav.set_center_widget(self.title)
        nav.pack_end(nxt, False, False, 0)
        self.pack_start(nav, False, False, 4)

        self.grid = Gtk.Grid(column_spacing=2, row_spacing=2)
        for col, letter in enumerate(WEEK_HEADER):
            lbl = Gtk.Label(label=letter)
            lbl.get_style_context().add_class("cal-wday")
            lbl.set_margin_bottom(4)
            self.grid.attach(lbl, col, 0, 1, 1)
        self.days = []
        for i in range(42):  # sempre 6 semanas, pro quadro não mudar de tamanho
            btn = self._button("", self.on_day)
            self.grid.attach(btn, i % 7, 1 + i // 7, 1, 1)
            self.days.append(btn)
        self.pack_start(self.grid, False, False, 0)


        # rolar o mouse em cima do calendário troca o mês
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("scroll-event", self.on_scroll)

        self.render()
        self.tick()
        GLib.timeout_add(1000 - datetime.datetime.now().microsecond // 1000, self._start_clock)

    def _button(self, label, callback, css_class=None):
        btn = Gtk.Button(label=label)
        btn.set_can_focus(False)  # o teclado continua indo pra barra de input
        btn.set_relief(Gtk.ReliefStyle.NONE)
        if css_class:
            btn.get_style_context().add_class(css_class)
        btn.connect("clicked", callback)
        return btn

    # --- relógio ---------------------------------------------------------------
    def _start_clock(self):
        self.tick()
        GLib.timeout_add_seconds(1, self.tick)
        return False

    def tick(self):
        now = datetime.datetime.now()
        self.time.set_text(now.strftime("%H:%M"))
        self.secs.set_text(now.strftime(":%S"))
        if now.date() != self.today:  # virou o dia
            if self.selected == self.today:
                self.selected = now.date()
            self.today = now.date()
            self.render()
        self.update_info()
        return True

    # --- calendário ------------------------------------------------------------
    def render(self):
        year, month = self.view.year, self.view.month
        self.title.set_label(f"{MONTHS[month - 1]} {year}")
        offset = (self.view.weekday() + 1) % 7  # quantos dias do mês anterior
        start = self.view - datetime.timedelta(days=offset)
        for i, btn in enumerate(self.days):
            day = start + datetime.timedelta(days=i)
            btn.day = day
            btn.set_label(str(day.day))
            ctx = btn.get_style_context()
            for cls, on in (("other", day.month != month),
                            ("today", day == self.today),
                            ("selected", day == self.selected)):
                (ctx.add_class if on else ctx.remove_class)(cls)
        self.update_info()

    def update_info(self):
        d = self.selected
        delta = (d - self.today).days
        when = {0: "hoje", 1: "amanhã", -1: "ontem"}.get(
            delta, f"daqui a {delta} dias" if delta > 0 else f"há {-delta} dias")
        text = f"{WEEKDAYS[d.weekday()]}, {d.day} de {MONTHS[d.month - 1]}"
        # a linha embaixo da hora mostra o dia clicado (e quanto falta)
        self.date.set_text(text if delta == 0 else f"{text} · {when}")

    def shift(self, months):
        index = self.view.year * 12 + self.view.month - 1 + months
        self.view = datetime.date(index // 12, index % 12 + 1, 1)
        self.render()

    def go_today(self):
        self.view = self.today.replace(day=1)
        self.selected = self.today
        self.render()

    def on_day(self, btn):
        self.selected = btn.day
        if btn.day.month != self.view.month or btn.day.year != self.view.year:
            self.view = btn.day.replace(day=1)  # dia de outro mês: vai pra ele
        self.render()

    def on_scroll(self, _w, event):
        direction = event.direction
        if direction == Gdk.ScrollDirection.SMOOTH:
            # touchpad manda deltas pequenos: acumula até dar um "passo"
            self.scroll_acc = getattr(self, "scroll_acc", 0) + event.get_scroll_deltas()[2]
            if abs(self.scroll_acc) >= 1:
                self.shift(1 if self.scroll_acc > 0 else -1)
                self.scroll_acc = 0
        elif direction == Gdk.ScrollDirection.DOWN:
            self.shift(1)
        elif direction == Gdk.ScrollDirection.UP:
            self.shift(-1)
        return True


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


class DeskPlayer(Gtk.Box):
    """Player de música (MPRIS via playerctl): Spotify, Firefox, mpv...
    Segue sozinho o player que começar a tocar; com mais de um aberto,
    aparecem abas pra escolher. Arrastar a barra avança/volta a música."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_name("player")
        self.set_no_show_all(True)
        self.players = []
        self.current = None
        self.art_url = None
        self.length = 0
        self.dragging = False

        self.sources = Gtk.Box(spacing=2)
        self.pack_start(self.sources, False, False, 0)

        top = Gtk.Box(spacing=12)
        self.art = Gtk.Image()
        self.art.set_name("player-art")
        self.art.set_size_request(ART_SIZE, ART_SIZE)
        self.art.set_valign(Gtk.Align.CENTER)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        texts.set_valign(Gtk.Align.CENTER)
        self.title = Gtk.Label(xalign=0)
        self.title.set_name("player-title")
        self.artist = Gtk.Label(xalign=0)
        self.artist.set_name("player-artist")
        for lbl in (self.title, self.artist):
            lbl.set_ellipsize(3)  # Pango.EllipsizeMode.END
            lbl.set_max_width_chars(1)
            lbl.set_single_line_mode(True)
            texts.pack_start(lbl, False, False, 0)
        # sem player aberto: ícone do Spotify no lugar da capa ("player fake")
        self.placeholder = Gtk.Label(label="\U000f04c7")
        self.placeholder.set_name("player-placeholder")
        self.placeholder.set_size_request(ART_SIZE, ART_SIZE)
        art = Gtk.Box()
        art.pack_start(self.art, False, False, 0)
        art.pack_start(self.placeholder, False, False, 0)
        top.pack_start(art, False, False, 0)
        top.pack_start(texts, True, True, 0)
        # clicar na capa/nome: abre o Spotify (ou mostra/esconde a gaveta dele)
        top_box = Gtk.EventBox()
        top_box.set_visible_window(False)
        top_box.add(top)
        top_box.connect("button-press-event", lambda _w, e: e.button == 1 and self.raise_player())
        self.pack_start(top_box, False, False, 0)
        self.texts = texts

        self.progress_box = Gtk.Box(spacing=8)
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.scale.set_draw_value(False)
        self.scale.set_can_focus(False)
        self.scale.connect("button-press-event", lambda *_: setattr(self, "dragging", True))
        self.scale.connect("button-release-event", self.on_seek)
        self.scale.nav_adjust = lambda d: (self.scale.set_value(self.scale.get_value() + 5 * d),
                                           self.on_seek())
        self.scale.set_valign(Gtk.Align.CENTER)
        self.pos_label = Gtk.Label()
        self.len_label = Gtk.Label()
        for lbl in (self.pos_label, self.len_label):
            lbl.get_style_context().add_class("player-time")
        self.progress_box.pack_start(self.pos_label, False, False, 0)
        self.progress_box.pack_start(self.scale, True, True, 0)
        self.progress_box.pack_start(self.len_label, False, False, 0)

        self.controls = controls = Gtk.Box(spacing=0)
        controls.set_halign(Gtk.Align.START)
        controls.set_margin_top(2)
        self.shuffle = self._ctrl("\U000f049d", lambda *_: self.toggle_shuffle(), "shuffle")
        prev = self._ctrl("\U000f04ae", lambda *_: self.call("previous"))
        self.play = self._ctrl("\U000f040a", lambda *_: self.call("play_pause"))
        self.play.get_style_context().add_class("main")
        nxt = self._ctrl("\U000f04ad", lambda *_: self.call("next"))
        self.loop = self._ctrl("\U000f0456", lambda *_: self.cycle_loop(), "repetir")
        for btn in (self.shuffle, prev, self.play, nxt, self.loop):
            controls.pack_start(btn, False, False, 0)
        self.texts.pack_start(controls, False, False, 0)
        self.pack_start(self.progress_box, False, False, 0)

        # rolar em cima do player muda o volume dele
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("scroll-event", self.on_scroll)

        self.manager = Playerctl.PlayerManager()
        self.manager.connect("name-appeared", lambda _m, name: self.add_player(name))
        self.manager.connect("player-vanished", lambda _m, player: self.remove_player(player))
        for name in self.manager.props.player_names:
            self.add_player(name)
        GLib.timeout_add_seconds(1, self.update_position)
        self.refresh()

    def _ctrl(self, glyph, callback, tooltip=None):
        btn = Gtk.Button(label=glyph)
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("ctrl")
        if tooltip:
            btn.set_tooltip_text(tooltip)
        btn.connect("clicked", callback)
        return btn

    # --- players ---------------------------------------------------------------
    def add_player(self, name):
        try:
            player = Playerctl.Player.new_from_name(name)
        except GLib.Error:
            return
        player.connect("playback-status", self.on_status)
        player.connect("metadata", lambda p, _m: p is self.current and self.refresh())
        player.connect("seeked", lambda p, _pos: p is self.current and self.update_position())
        player.connect("shuffle", lambda p, _s: p is self.current and self.refresh())
        player.connect("loop-status", lambda p, _l: p is self.current and self.refresh())
        self.manager.manage_player(player)
        self.players.append(player)
        if (self.current is None or is_playing(player)
                or (is_spotify(player) and not is_playing(self.current))):
            self.current = player
        self.refresh()

    def remove_player(self, player):
        self.players = [p for p in self.players if p is not player]
        if self.current is player:
            playing = [p for p in self.players if is_playing(p)]
            spotify = [p for p in self.players if is_spotify(p)]
            self.current = (playing or spotify or self.players or [None])[0]
        self.refresh()

    def on_status(self, player, _status):
        if is_playing(player):
            self.current = player  # segue quem começou a tocar
        elif player is self.current:
            # pausou: se outro player está tocando, passa pra ele
            playing = [p for p in self.players if is_playing(p)]
            if playing:
                self.current = playing[0]
        self.refresh()

    def select(self, player):
        self.current = player
        self.refresh()

    def call(self, method):
        if self.current:
            try:
                getattr(self.current, method)()
            except GLib.Error:
                pass

    def raise_player(self):
        if self.current is None:
            # player fake: abre o Spotify como janela normal
            if not any(is_spotify(p) for p in self.players):
                spawn("spotify-launcher")
                self.title.set_text("Abrindo o Spotify…")
        elif is_spotify(self.current):
            threading.Thread(target=show_spotify, daemon=True).start()
        else:
            self.call("raise")
        return True

    def toggle_shuffle(self):
        if self.current:
            try:
                self.current.set_shuffle(not self.current.props.shuffle)
            except GLib.Error:
                pass

    def cycle_loop(self):
        if not self.current:
            return
        order = [Playerctl.LoopStatus.NONE, Playerctl.LoopStatus.PLAYLIST, Playerctl.LoopStatus.TRACK]
        try:
            now = self.current.props.loop_status
            self.current.set_loop_status(order[(order.index(now) + 1) % 3])
        except (GLib.Error, ValueError):
            pass

    # --- tela ------------------------------------------------------------------
    def refresh(self):
        player = self.current
        self.show()
        for child in self.get_children():
            child.show_all()
        self.emit_visibility()
        self.placeholder.set_visible(player is None)
        self.art.set_visible(player is not None)
        if player is None:
            # player fake, só pra não ficar vazio: clicar abre o Spotify
            self.art_url = None
            self.sources.hide()
            self.controls.hide()
            self.progress_box.hide()
            self.title.set_text("Nada tocando")
            self.artist.set_text("abrir o Spotify")
            self.title.set_tooltip_text(None)
            return

        # abas só quando tem mais de um player aberto
        for child in self.sources.get_children():
            self.sources.remove(child)
        if len(self.players) > 1:
            for p in self.players:
                btn = Gtk.Button(label=player_label(p))
                btn.set_can_focus(False)
                btn.set_relief(Gtk.ReliefStyle.NONE)
                ctx = btn.get_style_context()
                ctx.add_class("source")
                if p is player:
                    ctx.add_class("current")
                btn.connect("clicked", lambda _b, p=p: self.select(p))
                self.sources.pack_start(btn, False, False, 0)
            self.sources.show_all()
        else:
            self.sources.hide()

        title = safe(player.get_title) or player_label(player)
        artist = safe(player.get_artist) or safe(player.get_album) or ""
        self.title.set_text(title)
        self.artist.set_text(artist)
        self.title.set_tooltip_text(f"{title}\n{artist}".strip())

        self.play.set_label("\U000f03e4" if is_playing(player) else "\U000f040a")

        # shuffle/repetir só aparecem se o player suporta (Spotify sim, Firefox não)
        shuffle = safe(lambda: player.props.shuffle)
        loop = safe(lambda: player.props.loop_status)
        self._set_toggle(self.shuffle, shuffle, bool(shuffle))
        if loop is None:
            self.loop.hide()
        else:
            self.loop.set_label("\U000f0458" if loop == Playerctl.LoopStatus.TRACK else "\U000f0456")
            self._set_toggle(self.loop, True, loop != Playerctl.LoopStatus.NONE)

        try:
            self.length = int(player.print_metadata_prop("mpris:length") or 0) / 1e6
        except (GLib.Error, ValueError):
            self.length = 0
        self.progress_box.set_visible(self.length > 0)
        if self.length > 0:
            self.scale.set_range(0, self.length)
            self.len_label.set_text(fmt_time(self.length))
        self.update_position()

        url = safe(lambda: player.print_metadata_prop("mpris:artUrl")) or ""
        if url != self.art_url:
            self.art_url = url
            self.load_art(url)

    def _set_toggle(self, btn, supported, active):
        btn.set_visible(supported is not None)
        ctx = btn.get_style_context()
        ctx.remove_class("on" if not active else "off")
        ctx.add_class("on" if active else "off")

    def emit_visibility(self):
        sep = getattr(self, "separator", None)
        if sep:
            sep.set_visible(True)

    def update_position(self):
        if self.current and self.length > 0 and not self.dragging:
            try:
                pos = self.current.get_position() / 1e6
            except GLib.Error:
                pos = 0
            self.scale.set_value(min(pos, self.length))
            self.pos_label.set_text(fmt_time(pos))
        return True

    def on_seek(self, *_):
        self.dragging = False
        if self.current and self.length > 0:
            try:
                self.current.set_position(int(self.scale.get_value() * 1e6))
            except GLib.Error:
                pass
        return False

    def on_scroll(self, _w, event):
        if not self.current:
            return False
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            dy = event.get_scroll_deltas()[2]
        else:
            dy = {Gdk.ScrollDirection.UP: -1, Gdk.ScrollDirection.DOWN: 1}.get(event.direction, 0)
        if dy:
            try:
                vol = self.current.props.volume - dy * 0.05
                self.current.set_volume(max(0.0, min(1.0, vol)))
            except GLib.Error:
                pass
        return True

    # --- capa do álbum (em preto e branco) ---------------------------------------
    def load_art(self, url):
        self.art.set_from_icon_name("audio-x-generic-symbolic", Gtk.IconSize.DIALOG)
        self.art.set_pixel_size(ART_SIZE // 2)
        if not url:
            return

        def worker():
            path = url[len("file://"):] if url.startswith("file://") else None
            if path is None and url.startswith("http"):
                os.makedirs(ART_CACHE, exist_ok=True)
                path = os.path.join(ART_CACHE, hashlib.sha1(url.encode()).hexdigest())
                if not os.path.exists(path):
                    try:
                        with urllib.request.urlopen(url, timeout=10) as r, open(path + ".tmp", "wb") as f:
                            f.write(r.read())
                        os.replace(path + ".tmp", path)
                    except OSError:
                        return
            if path:
                path = urllib.parse.unquote(path)
                GLib.idle_add(self.set_art, url, path)

        threading.Thread(target=worker, daemon=True).start()

    def set_art(self, url, path):
        if url != self.art_url:
            return False  # já trocou de música
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file(path)
        except GLib.Error:
            return False
        side = min(pix.get_width(), pix.get_height())  # recorta quadrado
        pix = pix.new_subpixbuf((pix.get_width() - side) // 2, (pix.get_height() - side) // 2, side, side)
        pix = pix.scale_simple(ART_SIZE, ART_SIZE, GdkPixbuf.InterpType.BILINEAR)
        pix.saturate_and_pixelate(pix, 0.0, False)  # tira a cor
        self.art.set_from_pixbuf(pix)
        return False


def safe(fn):
    try:
        return fn()
    except (GLib.Error, AttributeError, TypeError):
        return None


def is_playing(player):
    return safe(lambda: player.props.playback_status) == Playerctl.PlaybackStatus.PLAYING


def show_spotify():
    # Spotify escondido (special:music, ver close-window.sh): traz pro
    # workspace atual; se está num workspace normal, só vai até ele
    match = 'window = "class:^([Ss]potify)$"'
    hidden = any(c.get("class", "").lower() == "spotify"
                 and c.get("workspace", {}).get("name", "").startswith("special:")
                 for c in hypr("clients") or [])
    if hidden:
        ws = hypr("activeworkspace").get("id", 1)
        run("hyprctl", "dispatch", f"hl.dsp.window.move({{ workspace = {ws}, follow = false, {match} }})")
    run("hyprctl", "dispatch", f"hl.dsp.focus({{ {match} }})")


def is_spotify(player):
    return (safe(lambda: player.props.player_name) or "").startswith("spotify")


def player_label(player):
    name = safe(lambda: player.props.player_name) or "player"
    return name.split(".")[0].capitalize()


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def spawn(cmd):
    subprocess.Popen(cmd, shell=True, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def find_hwmon(*names):
    for base in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        if read(f"{base}/name") in names:
            return base
    return None


class Bar(Gtk.DrawingArea):
    """Barrinha fina de uso (a ProgressBar do GTK tem largura mínima de 150px)."""

    def __init__(self):
        super().__init__()
        self.fraction = 0.0
        self.alert = False
        self.set_size_request(-1, 2)
        self.connect("draw", self.on_draw)

    def set_fraction(self, fraction):
        if fraction != self.fraction:
            self.fraction = fraction
            self.queue_draw()

    def on_draw(self, _w, cr):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.set_source_rgba(1, 1, 1, 0.12)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        if self.alert:
            cr.set_source_rgb(0xf7 / 255, 0x76 / 255, 0x8e / 255)
        else:
            cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, width * self.fraction, height)
        cr.fill()


class DeskStats(Gtk.Box):
    """Painel de status/configurações rápidas.
    Botões: clique liga/desliga, clique direito abre o menu completo.
    Sliders: volume (clique no ícone = mudo) e brilho.
    Números: CPU, RAM, disco, bateria, temperatura e tempo ligado."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_name("stats")
        self.cpu_prev = None
        self.temp_dir = find_hwmon("k10temp", "coretemp", "zenpower", "acpitz")
        self.dragging = set()

        # --- botões rápidos ---------------------------------------------------
        toggles = Gtk.Box(homogeneous=True)
        self.wifi = self._tile(lambda: self.toggle_wifi(), f"{WAYBAR_SCRIPTS}/wifi-menu.sh")
        self.bt = self._tile(lambda: self.toggle_bt(), f"{WAYBAR_SCRIPTS}/bluetooth-menu.sh")
        self.dnd = self._tile(lambda: self.after(run, "dunstctl", "set-paused", "toggle"),
                              "dunstctl history-pop")
        self.power = self._tile(lambda: self.after(run, f"{WAYBAR_SCRIPTS}/battery-toggle.sh"), None)
        for tile in (self.wifi, self.bt, self.dnd, self.power):
            toggles.pack_start(tile, True, True, 0)
        self.pack_start(toggles, False, False, 0)

        # --- sliders ----------------------------------------------------------
        self.vol_icon, self.vol, self.vol_pct = self._slider(
            "\U000f057e", self.set_volume,
            lambda: self.after(run, "wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"))
        self.bri_icon, self.bri, self.bri_pct = self._slider("\U000f00e0", self.set_brightness, None)

        # --- números ----------------------------------------------------------
        grid = Gtk.Grid(column_spacing=12, row_spacing=4, column_homogeneous=True)
        monitor = f"{TERMINAL} -e htop" if shutil.which("htop") else None
        self.cpu = self._stat(grid, 0, 0, "CPU", monitor)
        self.ram = self._stat(grid, 1, 0, "RAM", monitor)
        self.temp = self._stat(grid, 2, 0, "°C", monitor)
        self.disk = self._stat(grid, 0, 1, "DISCO", FILE_MANAGER)
        self.bat = self._stat(grid, 1, 1, "BAT", None,
                              lambda: self.after(run, f"{WAYBAR_SCRIPTS}/battery-toggle.sh"))
        self.up = self._stat(grid, 2, 1, "UP", None)
        self.pack_start(grid, False, False, 2)

        self.update_fast()
        self.refresh_slow()
        GLib.timeout_add_seconds(2, self.update_fast)
        GLib.timeout_add_seconds(4, self.refresh_slow)

    # --- construção -------------------------------------------------------------
    def _tile(self, on_click, menu_cmd):
        btn = Gtk.Button()
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        btn.icon = Gtk.Label()
        btn.icon.get_style_context().add_class("tile-icon")
        btn.text = Gtk.Label()
        btn.text.get_style_context().add_class("tile-text")
        btn.text.set_ellipsize(3)
        btn.text.set_max_width_chars(9)  # 4 por linha cabem nos 280 da coluna
        box.pack_start(btn.icon, False, False, 0)
        box.pack_start(btn.text, False, False, 0)
        btn.add(box)
        btn.connect("clicked", lambda *_: on_click())
        if menu_cmd:
            def on_press(_w, event):
                if event.button == 3:
                    spawn(menu_cmd)
                    return True
                return False
            btn.connect("button-press-event", on_press)
        return btn

    def _slider(self, glyph, on_change, on_icon):
        row = Gtk.Box(spacing=8)
        icon = Gtk.Button(label=glyph)
        icon.set_can_focus(False)
        icon.set_relief(Gtk.ReliefStyle.NONE)
        icon.get_style_context().add_class("slider-icon")
        if on_icon:
            icon.connect("clicked", lambda *_: on_icon())
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(False)
        scale.set_can_focus(False)
        scale.set_valign(Gtk.Align.CENTER)
        scale.connect("button-press-event", lambda *_: self.dragging.add(scale))
        scale.connect("button-release-event", lambda *_: self.dragging.discard(scale))
        scale.connect("change-value", lambda _s, _t, value: on_change(max(0, min(100, value))))
        pct = Gtk.Label(xalign=1)
        pct.get_style_context().add_class("slider-pct")
        pct.set_width_chars(4)
        row.pack_start(icon, False, False, 0)
        row.pack_start(scale, True, True, 0)
        row.pack_start(pct, False, False, 0)
        self.pack_start(row, False, False, 0)
        return icon, scale, pct

    def _stat(self, grid, col, row, title, open_cmd, on_click=None):
        btn = Gtk.Button()
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("stat")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        line = Gtk.Box()
        head = Gtk.Label(label=title, xalign=0)
        head.get_style_context().add_class("stat-title")
        btn.value = Gtk.Label(xalign=1)
        btn.value.get_style_context().add_class("stat-value")
        btn.bar = Bar()
        line.pack_start(head, False, False, 0)
        line.pack_end(btn.value, False, False, 0)
        box.pack_start(line, False, False, 0)
        box.pack_start(btn.bar, False, False, 0)
        btn.add(box)
        if on_click:
            btn.connect("clicked", lambda *_: on_click())
        elif open_cmd:
            btn.connect("clicked", lambda *_: spawn(open_cmd))
        grid.attach(btn, col, row, 1, 1)
        return btn

    def _set_tile(self, tile, icon, text, active, tooltip):
        tile.icon.set_text(icon)
        tile.text.set_text(text)
        tile.set_tooltip_text(tooltip)
        ctx = tile.get_style_context()
        ctx.add_class("on" if active else "off")
        ctx.remove_class("off" if active else "on")

    def _set_stat(self, stat, text, fraction, tooltip=None, alert=False):
        stat.value.set_text(text)
        stat.bar.set_fraction(max(0.0, min(1.0, fraction)))
        stat.set_tooltip_text(tooltip)
        ctx = stat.get_style_context()
        (ctx.add_class if alert else ctx.remove_class)("alert")
        if stat.bar.alert != alert:
            stat.bar.alert = alert
            stat.bar.queue_draw()

    # --- ações ----------------------------------------------------------------------
    def after(self, fn, *args):
        # roda o comando fora da interface e atualiza o painel logo depois
        def worker():
            fn(*args)
            GLib.idle_add(lambda: self.refresh_slow() and False)  # uma vez só: refresh_slow retorna True
        threading.Thread(target=worker, daemon=True).start()

    def toggle_wifi(self):
        on = run("nmcli", "radio", "wifi") == "enabled"
        self.after(run, "nmcli", "radio", "wifi", "off" if on else "on")

    def toggle_bt(self):
        on = "Powered: yes" in run("bluetoothctl", "show")
        self.after(run, "bluetoothctl", "power", "off" if on else "on")

    def set_volume(self, value):
        self.vol_pct.set_text(f"{int(value)}%")
        threading.Thread(target=run, daemon=True, args=(
            "wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{value / 100:.2f}")).start()
        return False

    def set_brightness(self, value):
        value = max(1, value)  # 0% apaga a tela
        self.bri_pct.set_text(f"{int(value)}%")
        threading.Thread(target=run, daemon=True, args=(
            "brightnessctl", "-q", "set", f"{int(value)}%")).start()
        return False

    # --- leituras rápidas (arquivos do /proc e /sys) ---------------------------------
    def update_fast(self):
        if not DESKTOP_VISIBLE[0]:
            return True  # tem janela na frente: não gasta CPU à toa

        # CPU: diferença entre duas leituras do /proc/stat
        fields = [int(x) for x in read("/proc/stat").split("\n")[0].split()[1:]]
        idle, total = fields[3] + fields[4], sum(fields)
        if self.cpu_prev:
            d_idle, d_total = idle - self.cpu_prev[0], total - self.cpu_prev[1]
            usage = 1 - d_idle / d_total if d_total else 0
            self._set_stat(self.cpu, f"{usage * 100:.0f}%", usage, "abrir htop", usage > 0.9)
        self.cpu_prev = (idle, total)

        mem = {}
        for line in read("/proc/meminfo").split("\n"):
            key, _, rest = line.partition(":")
            mem[key] = int(rest.split()[0]) if rest.split() else 0
        used = mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)
        frac = used / mem["MemTotal"] if mem.get("MemTotal") else 0
        self._set_stat(self.ram, f"{used / 1048576:.1f}G", frac,
                       f"{used / 1048576:.1f} de {mem.get('MemTotal', 0) / 1048576:.1f} GB", frac > 0.9)

        if self.temp_dir:
            celsius = int(read(f"{self.temp_dir}/temp1_input", "0")) / 1000
            self._set_stat(self.temp, f"{celsius:.0f}", celsius / 100, "temperatura do processador",
                           celsius >= 85)

        disk = shutil.disk_usage("/")
        self._set_stat(self.disk, f"{disk.used / disk.total * 100:.0f}%", disk.used / disk.total,
                       f"{disk.free / 1e9:.0f} GB livres de {disk.total / 1e9:.0f} GB · abrir arquivos")

        bat = glob.glob("/sys/class/power_supply/BAT*")
        if bat:
            cap = int(read(f"{bat[0]}/capacity", "0"))
            status = read(f"{bat[0]}/status")
            charging = status in ("Charging", "Full")
            now = int(read(f"{bat[0]}/energy_now", read(f"{bat[0]}/charge_now", "0")))
            full = int(read(f"{bat[0]}/energy_full", read(f"{bat[0]}/charge_full", "0")))
            rate = int(read(f"{bat[0]}/power_now", read(f"{bat[0]}/current_now", "0")))
            tip = {"Charging": "carregando", "Full": "carregada",
                   "Discharging": "na bateria"}.get(status, status.lower())
            if rate > 0:
                hours = ((full - now) if status == "Charging" else now) / rate
                if status in ("Charging", "Discharging") and hours < 48:
                    tip += f" · {int(hours)}h{int(hours % 1 * 60):02d} " + (
                        "pra encher" if status == "Charging" else "restantes")
            self._set_stat(self.bat, f"{cap}%" + (" \U000f0084" if charging else ""), cap / 100,
                           tip + " · clique muda o modo de energia", cap <= 15 and not charging)

        secs = float(read("/proc/uptime", "0").split()[0])
        h, m = int(secs // 3600), int(secs % 3600 // 60)
        self._set_stat(self.up, f"{h}h{m:02d}" if h else f"{m}min", min(secs / 86400, 1),
                       "tempo desde que o PC ligou")
        return True

    # --- leituras lentas (comandos), numa thread -------------------------------------
    def refresh_slow(self):
        if DESKTOP_VISIBLE[0]:
            threading.Thread(target=self._collect_slow, daemon=True).start()
        return True

    def _collect_slow(self):
        data = {
            "wifi": run("nmcli", "radio", "wifi"),
            "conn": run("nmcli", "-t", "-f", "NAME,TYPE", "con", "show", "--active"),
            "bt": run("bluetoothctl", "show"),
            "bt_dev": run("bluetoothctl", "devices", "Connected"),
            "dnd": run("dunstctl", "is-paused"),
            "waiting": run("dunstctl", "count", "waiting"),
            "profile": run("powerprofilesctl", "get"),
            "vol": run("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"),
        }
        GLib.idle_add(self._apply_slow, data)

    def _apply_slow(self, d):
        wifi_on = d["wifi"] == "enabled"
        ssid = next((l.rsplit(":", 1)[0] for l in d["conn"].split("\n")
                     if l.endswith(":802-11-wireless")), "")
        wired = any(l.endswith(":802-3-ethernet") for l in d["conn"].split("\n"))
        self._set_tile(self.wifi, "\U000f05a9" if wifi_on else "\U000f05aa",
                       ssid or ("cabo" if wired else "ligado" if wifi_on else "desligado"),
                       wifi_on, f"Wi-Fi: {ssid or 'sem rede'}\nclique liga/desliga · direito escolhe a rede")

        bt_on = "Powered: yes" in d["bt"]
        devices = [l.split(" ", 2)[2] for l in d["bt_dev"].split("\n") if l.count(" ") >= 2]
        self._set_tile(self.bt, ("\U000f00b1" if devices else "\U000f00af") if bt_on else "\U000f00b2",
                       (devices[0] if len(devices) == 1 else f"{len(devices)} conect." if devices
                        else "ligado") if bt_on else "desligado",
                       bt_on, ("Bluetooth: " + (", ".join(devices) or "nada conectado")
                               + "\nclique liga/desliga · direito abre os dispositivos"))

        paused = d["dnd"] == "true"
        waiting = d["waiting"] or "0"
        self._set_tile(self.dnd, "\U000f009b" if paused else "\U000f009a",
                       f"{waiting} novas" if paused and waiting != "0" else "silêncio" if paused else "avisos",
                       not paused, "Não perturbe " + ("ligado" if paused else "desligado")
                       + "\nclique alterna · direito mostra a última notificação")

        profile = d["profile"] or "balanced"
        icon, label = {"performance": ("", "desempenho"),
                       "power-saver": ("", "economia")}.get(profile, ("", "equilibrado"))
        self._set_tile(self.power, icon, label, profile != "power-saver",
                       "Modo de energia: " + label + "\nclique troca o modo")

        # volume: "Volume: 0.45 [MUTED]"
        parts = d["vol"].split()
        if len(parts) >= 2 and self.vol not in self.dragging:
            muted = "[MUTED]" in d["vol"]
            value = float(parts[1]) * 100
            self.vol.set_value(value)
            self.vol_pct.set_text("mudo" if muted else f"{value:.0f}%")
            self.vol_icon.set_label("\U000f075f" if muted else "\U000f057e")
            ctx = self.vol_icon.get_style_context()
            (ctx.add_class if muted else ctx.remove_class)("off")

        if self.bri not in self.dragging:
            base = (glob.glob("/sys/class/backlight/*") or [None])[0]
            if base:
                value = int(read(f"{base}/brightness", "0")) / max(1, int(read(f"{base}/max_brightness", "1"))) * 100
                self.bri.set_value(value)
                self.bri_pct.set_text(f"{value:.0f}%")
        return False


HOVER_EVENTS = Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK


class DeskTodo(Gtk.Box):
    """Checklist: digita embaixo e Enter adiciona. Clicar na caixinha (ou no
    texto) marca como feita e risca; o x aparece ao passar o mouse e apaga.
    Fica salvo na nota TODO_NOTE do Obsidian (concluídas de outros dias somem
    do painel mas ficam na nota)."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_name("todo")
        self.tasks = self.load()
        self.max_height = 300  # SidePanel.align_to ajusta pro espaço que sobra

        head = Gtk.Box()
        title = Gtk.Label(label="TAREFAS", xalign=0)
        title.get_style_context().add_class("todo-head")
        self.count = Gtk.Label(xalign=1)
        self.count.get_style_context().add_class("todo-head")
        head.pack_start(title, False, False, 0)
        head.pack_end(self.count, False, False, 0)
        self.pack_start(head, False, False, 0)

        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.list)
        self.pack_start(self.scroll, False, False, 0)
        self.scroll.connect("size-allocate", lambda *_: GLib.idle_add(self.fit_height))

        add = Gtk.Box(spacing=8)
        plus = Gtk.Label(label="\U000f0415")  # +
        plus.get_style_context().add_class("todo-plus")
        self.entry = Gtk.Entry()
        self.entry.own_keys = True  # a janela não manda essas teclas pro launcher
        self.entry.set_placeholder_text("nova tarefa…")
        self.entry.connect("activate", self.on_add)
        add.pack_start(plus, False, False, 0)
        add.pack_start(self.entry, True, True, 0)
        self.pack_start(add, False, False, 0)

        self.render()
        GLib.timeout_add_seconds(3, self.watch)

    # --- arquivo (nota do Obsidian) ---------------------------------------------
    # Cada tarefa é uma linha "- [ ] texto" ou "- [x] texto ✅ AAAA-MM-DD" (formato
    # do plugin Tasks). O resto da nota fica intacto; editar no Obsidian também vale.
    TASK_LINE = re.compile(r"^(\s*[-*] \[)([ xX])(\] )(.*?)(?:\s+✅ (\d{4}-\d{2}-\d{2}))?\s*$")

    @staticmethod
    def note_path():
        return os.path.join(OBSIDIAN_VAULT, TODO_NOTE)

    def read_lines(self):
        try:
            with open(self.note_path()) as f:
                return f.read().splitlines()
        except OSError:
            return None

    def write_lines(self, lines):
        path = self.note_path()
        with open(path + ".tmp", "w") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(path + ".tmp", path)
        self.mtime = os.path.getmtime(path)

    def load(self):
        lines = self.read_lines()
        if lines is None:
            lines = self.create_note()
        try:
            self.mtime = os.path.getmtime(self.note_path())
        except OSError:
            self.mtime = None
        tasks = []
        for i, line in enumerate(lines):
            m = self.TASK_LINE.match(line)
            if m:
                tasks.append({"line": i, "text": m[4], "done": m[2] != " ", "date": m[5]})
        return tasks

    def create_note(self):
        lines = ["---", "tags: [tarefas]", "---", "# ✅ Tarefas", "",
                 "Lista sincronizada com o painel da área de trabalho. Pode editar daqui também.", ""]
        try:  # traz as tarefas da lista antiga do painel
            with open(TODO_FILE) as f:
                for t in json.load(f):
                    lines.append(f"- [{'x' if t.get('done') else ' '}] {t['text']}")
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            self.write_lines(lines)
        except OSError:
            pass
        return lines

    def edit(self, task, new_line):
        """Troca (ou apaga, com None) a linha da tarefa, conferindo que ela não mudou."""
        lines = self.read_lines() or []
        i = task["line"]
        if i >= len(lines) or not (m := self.TASK_LINE.match(lines[i])) or m[4] != task["text"]:
            self.reload()  # a nota mudou por fora: só recarrega
            return
        if new_line is None:
            del lines[i]
        else:
            lines[i] = new_line
        self.write_lines(lines)
        self.reload()

    def reload(self):
        self.tasks = self.load()
        GLib.idle_add(self.render)  # não recria a linha no meio do clique
        return False

    def watch(self):
        # pega edições feitas no Obsidian (ou no celular, se o cofre sincroniza)
        if DESKTOP_VISIBLE[0]:
            try:
                mtime = os.path.getmtime(self.note_path())
            except OSError:
                mtime = None
            if mtime != self.mtime:
                self.reload()
        return True

    def visible_tasks(self):
        # pendentes + as concluídas hoje (as mais antigas ficam só na nota)
        today = datetime.date.today().isoformat()
        return [t for t in self.tasks if not t["done"] or t["date"] in (today, None)]

    # --- lista -----------------------------------------------------------------
    def render(self):
        for child in self.list.get_children():
            self.list.remove(child)
        tasks = self.visible_tasks()
        for task in tasks:
            self.list.pack_start(self.make_row(task), False, False, 0)
        self.list.show_all()
        self.scroll.set_no_show_all(True)
        self.scroll.set_visible(bool(tasks))  # vazia: não reserva espaço
        self.fit_height()
        done = sum(t["done"] for t in tasks)
        self.count.set_text(f"{done} de {len(tasks)} feitas hoje" if tasks else "")
        return False

    def make_row(self, task):
        row = Gtk.EventBox()
        row.set_visible_window(False)
        row.add_events(HOVER_EVENTS)
        box = Gtk.Box(spacing=8)
        box.get_style_context().add_class("todo-row")
        check = Gtk.Label(label="\U000f0132" if task.get("done") else "\U000f0131")
        check.get_style_context().add_class("todo-check")
        check.set_valign(Gtk.Align.START)
        text = Gtk.Label(xalign=0)
        text.set_line_wrap(True)
        text.set_line_wrap_mode(2)  # Pango.WrapMode.WORD_CHAR
        text.set_max_width_chars(1)
        # largura fixa: sem isso o GTK mede o texto quebrado letra a letra e sobra espaço
        text.set_size_request(PANEL_WIDTH - 100, -1)
        escaped = GLib.markup_escape_text(task["text"])
        text.set_markup(f"<s>{escaped}</s>" if task.get("done") else escaped)
        ctx = text.get_style_context()
        ctx.add_class("todo-text")
        if task.get("done"):
            ctx.add_class("done")
            check.get_style_context().add_class("done")
        delete = Gtk.Button(label="\U000f0156")  # x
        delete.set_can_focus(False)
        delete.set_relief(Gtk.ReliefStyle.NONE)
        delete.get_style_context().add_class("todo-del")
        delete.set_valign(Gtk.Align.START)
        delete.set_opacity(0)
        delete.connect("clicked", lambda *_: self.remove(task))
        box.pack_start(check, False, False, 0)
        box.pack_start(text, True, True, 0)
        box.pack_start(delete, False, False, 0)
        row.add(box)

        def on_press(_w, event):
            if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
                self.toggle(task)
            return False

        row.connect("button-press-event", on_press)
        row.nav_style = box
        row.nav_activate = lambda: self.toggle(task)
        row.nav_delete = lambda: self.remove(task)
        row.highlight = lambda on: delete.set_opacity(1 if on else 0)
        row.connect("enter-notify-event", lambda *_: delete.set_opacity(1))
        row.connect("leave-notify-event", lambda _w, e: e.detail != Gdk.NotifyType.INFERIOR
                    and delete.set_opacity(0))
        return row

    def fit_height(self, *_):
        # altura = a da lista, até max_height; dali pra frente rola
        # (o propagate-natural-height do GTK3 erra com texto que quebra linha)
        width = self.scroll.get_allocated_width()
        if width <= 1:
            width = PANEL_WIDTH - 32
        height = min(self.list.get_preferred_height_for_width(width)[1], self.max_height)
        if height != self.scroll.get_min_content_height():
            self.scroll.set_min_content_height(height)
        return False

    def on_add(self, entry):
        text = entry.get_text().strip()
        if text:
            lines = self.read_lines()
            if lines is None:
                lines = self.create_note()
            # entra logo depois da última tarefa (ou no fim da nota)
            last = max([t["line"] for t in self.load()], default=len(lines) - 1)
            lines.insert(last + 1, f"- [ ] {text}")
            try:
                self.write_lines(lines)
            except OSError:
                return
            self.reload()
        entry.set_text("")

    def toggle(self, task):
        if task["done"]:
            line = f"- [ ] {task['text']}"
        else:
            line = f"- [x] {task['text']} ✅ {datetime.date.today().isoformat()}"
        self.edit(task, line)
        return False

    def remove(self, task):
        self.edit(task, None)


class SidePanel(Gtk.EventBox):
    """Coluna colada na waybar e na borda direita.
    Fixo: relógio + tarefas em cima; status do PC e player presos no rodapé
    (as tarefas usam todo o espaço do meio). Mouse em cima do relógio troca as tarefas pelo
    calendário; tirar o mouse volta."""

    def __init__(self):
        super().__init__()
        self.set_visible_window(False)
        self.add_events(HOVER_EVENTS)
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.FILL)
        self.set_margin_top(WAYBAR_HEIGHT)
        self.set_margin_bottom(PANEL_BOTTOM)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.set_name("side-panel")
        panel.set_size_request(PANEL_WIDTH, -1)
        self.add(panel)

        calendar = DeskCalendar()
        clock_area = Gtk.EventBox()
        clock_area.set_visible_window(False)
        clock_area.add_events(HOVER_EVENTS)
        clock_area.add(calendar.header)
        clock_area.connect("enter-notify-event", lambda *_: self.show_details(True))
        clock_area.nav_style = calendar.header
        clock_area.nav_activate = lambda: self.stack.set_visible_child_name(
            "todo" if self.stack.get_visible_child_name() == "details" else "details")
        panel.pack_start(clock_area, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        self.stack.set_vhomogeneous(False)
        self.stack.set_interpolate_size(True)
        self.todo = DeskTodo()
        self.stack.add_named(self.todo, "todo")

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        details.pack_start(calendar, False, False, 0)
        self.stack.add_named(details, "details")
        panel.pack_start(self.stack, True, True, 0)
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.pack_start(DeskStats(), False, False, 0)
        if Playerctl is not None:  # player fixo embaixo do status
            player = DeskPlayer()
            player.separator = Gtk.Separator()
            player.separator.set_no_show_all(True)
            bottom.pack_start(player.separator, False, False, 0)
            bottom.pack_start(player, False, False, 0)
            player.emit_visibility()
        panel.pack_end(bottom, False, False, 0)

        self.connect("leave-notify-event", self.on_leave)
        self.stack.set_visible_child_name("todo")

    def align_to(self, _target):
        # a lista de tarefas rola dentro do espaço entre o relógio e o status
        space = self.stack.get_allocated_height()
        if space > 1:
            max_height = max(TODO_MIN_HEIGHT, space - 80)
            if self.todo.max_height != max_height:
                self.todo.max_height = max_height
                self.todo.fit_height()
        return False

    def show_details(self, show):
        self.stack.set_visible_child_name("details" if show else "todo")
        if show and not getattr(self, "watching", False):
            # o leave-notify às vezes não chega (ex.: mouse sai rápido por cima
            # de um botão), então confere a posição do mouse enquanto está aberto
            self.watching = True
            GLib.timeout_add(250, self.check_pointer)
        return False

    def check_pointer(self):
        x, y = self.get_pointer()
        alloc = self.get_allocation()
        if not (0 <= x < alloc.width and 0 <= y < alloc.height):
            self.watching = False
            self.show_details(False)
            return False
        return True

    def on_leave(self, _w, event):
        if event.detail != Gdk.NotifyType.INFERIOR:  # saiu do painel de verdade
            self.show_details(False)
        return False


# --- coluna da esquerda: clima e notificações (favoritos ficam embaixo do input) ----------------------

# código WMO (Open-Meteo) -> (ícone de dia, ícone de noite, descrição)
WEATHER_CODES = {
    0: ("\U000f0599", "\U000f0594", "céu limpo"),
    1: ("\U000f0595", "\U000f0f31", "poucas nuvens"),
    2: ("\U000f0595", "\U000f0f31", "parcialmente nublado"),
    3: ("\U000f0590", "\U000f0590", "nublado"),
    45: ("\U000f0591", "\U000f0591", "neblina"),
    48: ("\U000f0591", "\U000f0591", "neblina"),
    51: ("\U000f0597", "\U000f0597", "garoa"),
    53: ("\U000f0597", "\U000f0597", "garoa"),
    55: ("\U000f0597", "\U000f0597", "garoa forte"),
    56: ("\U000f0597", "\U000f0597", "garoa gelada"),
    57: ("\U000f0597", "\U000f0597", "garoa gelada"),
    61: ("\U000f0597", "\U000f0597", "chuva fraca"),
    63: ("\U000f0597", "\U000f0597", "chuva"),
    65: ("\U000f0596", "\U000f0596", "chuva forte"),
    66: ("\U000f0597", "\U000f0597", "chuva gelada"),
    67: ("\U000f0596", "\U000f0596", "chuva gelada"),
    71: ("\U000f0598", "\U000f0598", "neve fraca"),
    73: ("\U000f0598", "\U000f0598", "neve"),
    75: ("\U000f0598", "\U000f0598", "neve forte"),
    77: ("\U000f0598", "\U000f0598", "neve"),
    80: ("\U000f0597", "\U000f0597", "pancadas de chuva"),
    81: ("\U000f0596", "\U000f0596", "pancadas de chuva"),
    82: ("\U000f0596", "\U000f0596", "temporal"),
    85: ("\U000f0598", "\U000f0598", "neve"),
    86: ("\U000f0598", "\U000f0598", "neve forte"),
    95: ("\U000f067e", "\U000f067e", "tempestade"),
    96: ("\U000f067e", "\U000f067e", "tempestade com granizo"),
    99: ("\U000f067e", "\U000f067e", "tempestade com granizo"),
}
WEEKDAYS_SHORT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "welcome-desktop"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


class DeskWeather(Gtk.Box):
    """Localização (pelo IP, ou WEATHER_PLACE fixo) + clima atual e próximos dias
    (Open-Meteo, sem chave). Atualiza a cada 15 min; clicar atualiza na hora."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.set_name("weather")

        self.place = Gtk.Label(xalign=0)
        self.place.set_name("weather-place")
        self.pack_start(self.place, False, False, 0)

        now = Gtk.Box(spacing=12)
        self.icon = Gtk.Label()
        self.icon.set_name("weather-icon")
        self.temp = Gtk.Label(xalign=0)
        self.temp.set_name("weather-temp")
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side.set_valign(Gtk.Align.CENTER)
        self.desc = Gtk.Label(xalign=0)
        self.desc.set_name("weather-desc")
        self.range = Gtk.Label(xalign=0)
        self.range.get_style_context().add_class("weather-muted")
        for lbl in (self.desc, self.range):
            lbl.set_ellipsize(3)
            lbl.set_max_width_chars(1)
            side.pack_start(lbl, False, False, 0)
        now.pack_start(self.icon, False, False, 0)
        now.pack_start(self.temp, False, False, 0)
        now.pack_start(side, True, True, 0)
        self.pack_start(now, False, False, 0)

        self.details = Gtk.Label(xalign=0)
        self.details.get_style_context().add_class("weather-muted")
        self.details.set_margin_bottom(10)
        self.details.set_line_wrap(True)
        self.details.set_max_width_chars(1)
        self.pack_start(self.details, False, False, 0)

        self.days = Gtk.Box(homogeneous=True)
        self.pack_start(self.days, False, False, 0)

        self.place.set_text("\U000f034e  localizando…")
        try:
            with open(WEATHER_CACHE) as f:
                self.apply(json.load(f))
        except (OSError, ValueError, KeyError):
            pass
        self.refresh()
        GLib.timeout_add_seconds(15 * 60, self.refresh)

    def refresh(self):
        threading.Thread(target=self._fetch, daemon=True).start()
        return True

    def _fetch(self):
        try:
            if WEATHER_PLACE:
                place = dict(WEATHER_PLACE)
            else:
                loc = fetch_json("http://ip-api.com/json/?fields=status,city,regionName,lat,lon&lang=pt-BR")
                place = {"city": loc["city"], "region": loc["regionName"], "lat": loc["lat"], "lon": loc["lon"]}
            data = fetch_json(
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={place['lat']}&longitude={place['lon']}"
                "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
                "weather_code,wind_speed_10m,is_day"
                "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                "&timezone=auto&forecast_days=5")
            data["place"] = place
        except (OSError, ValueError, KeyError):
            GLib.idle_add(self.place.set_tooltip_text, "sem internet: mostrando o último clima salvo")
            return
        try:
            os.makedirs(os.path.dirname(WEATHER_CACHE), exist_ok=True)
            with open(WEATHER_CACHE, "w") as f:
                json.dump(data, f)
        except OSError:
            pass
        GLib.idle_add(self.apply, data)

    def apply(self, data):
        place, cur, daily = data["place"], data["current"], data["daily"]
        self.place.set_text(f"\U000f034e  {place['city']}, {place['region']}")
        self.place.set_tooltip_text(None)
        day_icon, night_icon, desc = WEATHER_CODES.get(cur["weather_code"], ("\U000f0590", "\U000f0590", ""))
        self.icon.set_text(day_icon if cur.get("is_day", 1) else night_icon)
        self.temp.set_text(f"{round(cur['temperature_2m'])}°")
        self.desc.set_text(desc)
        self.range.set_text(f"{round(daily['temperature_2m_max'][0])}° / {round(daily['temperature_2m_min'][0])}°"
                            f"   \U000f0597 {daily['precipitation_probability_max'][0] or 0}%")
        self.range.set_tooltip_text("máxima / mínima de hoje · chance de chuva")
        self.details.set_text(f"sensação {round(cur['apparent_temperature'])}°   "
                              f"\U000f058e {cur['relative_humidity_2m']}%   "
                              f"\U000f059d {round(cur['wind_speed_10m'])} km/h")
        self.details.set_tooltip_text("sensação térmica · umidade · vento")

        for child in self.days.get_children():
            self.days.remove(child)
        for i in range(1, len(daily["time"])):
            date = datetime.date.fromisoformat(daily["time"][i])
            icon, _night, desc = WEATHER_CODES.get(daily["weather_code"][i], ("\U000f0590", "", ""))
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_tooltip_text(f"{WEEKDAYS[date.weekday()]}: {desc}, "
                                 f"chuva {daily['precipitation_probability_max'][i] or 0}%")
            name = Gtk.Label(label=WEEKDAYS_SHORT[date.weekday()])
            name.get_style_context().add_class("weather-day")
            glyph = Gtk.Label(label=icon)
            glyph.get_style_context().add_class("weather-day-icon")
            temps = Gtk.Label(label=f"{round(daily['temperature_2m_max'][i])}° "
                                    f"{round(daily['temperature_2m_min'][i])}°")
            temps.get_style_context().add_class("weather-muted")
            for w in (name, glyph, temps):
                col.pack_start(w, False, False, 0)
            self.days.pack_start(col, True, True, 0)
        self.days.show_all()
        return False


def time_ago(seconds):
    if seconds < 60:
        return "agora"
    if seconds < 3600:
        return f"{int(seconds // 60)} min"
    if seconds < 86400:
        return f"{int(seconds // 3600)} h"
    return f"{int(seconds // 86400)} d"


def clear_claude_waybar():
    # mesmo arquivo/sinal de ~/.config/waybar/scripts/claude-notify.sh
    try:
        os.remove(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "claude-notify"))
    except OSError:
        pass
    run("pkill", "-RTMIN+12", "-x", "waybar")


class DeskNotifications(Gtk.Box):
    """Histórico do dunst. O x (aparece ao passar o mouse) apaga uma,
    'limpar' apaga todas. Atualiza sozinho a cada 3 s."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_name("notifs")
        self.max_height = 200
        self.signature = None

        head = Gtk.Box()
        title = Gtk.Label(label="NOTIFICAÇÕES", xalign=0)
        title.get_style_context().add_class("todo-head")
        self.count = Gtk.Label()
        self.count.get_style_context().add_class("todo-head")
        self.count.set_margin_start(6)
        clear = Gtk.Button(label="limpar")
        clear.set_can_focus(False)
        clear.set_relief(Gtk.ReliefStyle.NONE)
        clear.get_style_context().add_class("notif-clear")
        clear.connect("clicked", lambda *_: self.after("history-clear", claude=True))
        head.pack_start(title, False, False, 0)
        head.pack_start(self.count, False, False, 0)
        head.pack_end(clear, False, False, 0)
        self.pack_start(head, False, False, 0)

        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.add(self.list)
        self.pack_start(self.scroll, False, False, 0)
        self.empty = Gtk.Label(label="nenhuma notificação", xalign=0)
        self.empty.get_style_context().add_class("notif-empty")
        self.pack_start(self.empty, False, False, 0)

        self.refresh()
        GLib.timeout_add_seconds(3, self.refresh)

    def after(self, *args, claude=False):
        def worker():
            run("dunstctl", *args)
            if claude:  # some também o "Claude aguardando" da waybar
                clear_claude_waybar()
            GLib.idle_add(lambda: self.refresh() and False)  # uma vez só: refresh retorna True
        threading.Thread(target=worker, daemon=True).start()

    def refresh(self):
        if DESKTOP_VISIBLE[0]:
            threading.Thread(target=self._collect, daemon=True).start()
        return True

    def _collect(self):
        try:
            raw = json.loads(run("dunstctl", "history") or "{}")
            items = [{k: v["data"] for k, v in n.items()} for n in raw.get("data", [[]])[0]]
        except (ValueError, KeyError, IndexError, TypeError):
            items = []
        GLib.idle_add(self.render, items)

    def render(self, items):
        uptime = float(read("/proc/uptime", "0").split()[0])
        # só refaz a lista se mudou algo (ou virou o minuto do "há x min")
        signature = (tuple(n.get("id") for n in items), int(uptime // 60))
        if signature == self.signature:
            return False
        self.signature = signature
        for child in self.list.get_children():
            self.list.remove(child)
        for n in items:
            self.list.pack_start(self.make_row(n, uptime - n.get("timestamp", 0) / 1e6), False, False, 0)
        self.list.show_all()
        self.count.set_text(str(len(items)) if items else "")
        self.scroll.set_visible(bool(items))
        self.empty.set_visible(not items)
        self.fit_height()
        return False

    def fit_height(self):
        width = self.scroll.get_allocated_width()
        if width <= 1:
            width = PANEL_WIDTH - 32
        height = min(self.list.get_preferred_height_for_width(width)[1], self.max_height)
        if height != self.scroll.get_min_content_height():
            self.scroll.set_min_content_height(height)

    def make_row(self, n, age):
        row = Gtk.EventBox()
        row.set_visible_window(False)
        row.add_events(HOVER_EVENTS)
        box = Gtk.Box(spacing=10)
        box.get_style_context().add_class("notif-row")

        icon = Gtk.Image()
        icon.set_valign(Gtk.Align.START)
        path = n.get("icon_path") or ""
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(path, 20, 20)
            pix.saturate_and_pixelate(pix, 0.0, False)  # preto e branco, como o resto
            icon.set_from_pixbuf(pix)
        except GLib.Error:
            icon.set_from_icon_name("dialog-information-symbolic", Gtk.IconSize.MENU)
        icon.set_size_request(20, 20)

        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        top = Gtk.Box()
        summary = Gtk.Label(label=n.get("summary") or n.get("appname") or "", xalign=0)
        summary.get_style_context().add_class("notif-summary")
        summary.set_ellipsize(3)
        summary.set_max_width_chars(1)
        when = Gtk.Label(label=time_ago(age))
        when.get_style_context().add_class("notif-time")
        top.pack_start(summary, True, True, 0)
        top.pack_end(when, False, False, 0)
        body_text = re.sub(r"<[^>]+>", "", n.get("body") or "").strip()
        body = Gtk.Label(label=body_text, xalign=0)
        body.get_style_context().add_class("notif-body")
        body.set_line_wrap(True)
        body.set_line_wrap_mode(2)
        body.set_lines(2)
        body.set_ellipsize(3)
        body.set_max_width_chars(1)
        body.set_size_request(PANEL_WIDTH - 110, -1)
        texts.pack_start(top, False, False, 0)
        if body_text:
            texts.pack_start(body, False, False, 0)

        delete = Gtk.Button(label="\U000f0156")
        delete.set_can_focus(False)
        delete.set_relief(Gtk.ReliefStyle.NONE)
        delete.get_style_context().add_class("todo-del")
        delete.set_valign(Gtk.Align.START)
        delete.set_opacity(0)
        delete.connect("clicked", lambda *_: self.after("history-rm", str(n.get("id")),
                                                         claude=n.get("summary") == "Claude Code"))

        box.pack_start(icon, False, False, 0)
        box.pack_start(texts, True, True, 0)
        box.pack_start(delete, False, False, 0)
        row.add(box)
        row.set_tooltip_text(n.get("appname") or None)
        row.nav_style = box
        row.nav_activate = lambda: None
        row.nav_delete = delete.clicked
        row.highlight = lambda on: delete.set_opacity(1 if on else 0)
        row.connect("enter-notify-event", lambda *_: delete.set_opacity(1))
        row.connect("leave-notify-event", lambda _w, e: e.detail != Gdk.NotifyType.INFERIOR
                    and delete.set_opacity(0))
        return row


def icon_pixbufs(gicon, size):
    """(colorido, preto e branco) do ícone de um app."""
    theme = Gtk.IconTheme.get_default()
    pix = None
    for candidate in (gicon, Gio.ThemedIcon.new("application-x-executable")):
        if candidate is None:
            continue
        info = theme.lookup_by_gicon(candidate, size, Gtk.IconLookupFlags.FORCE_SIZE)
        if info:
            try:
                pix = info.load_icon()
                break
            except GLib.Error:
                pass
    if pix is None:
        pix = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
        pix.fill(0)
    gray = pix.copy()
    gray.saturate_and_pixelate(gray, 0.0, False)
    return pix, gray


class SysInfo(Gtk.Box):
    """Ficha do PC no estilo do fastfetch, embaixo dos favoritos.
    Lê tudo do `fastfetch --format json` numa thread; atualiza a cada minuto."""

    FIELDS = [("os", "OS"), ("host", "Host"), ("kernel", "Kernel"), ("uptime", "Uptime"),
              ("pkgs", "Pacotes"), ("shell", "Shell"), ("wm", "WM"), ("term", "Terminal"),
              ("cpu", "CPU"), ("gpu", "GPU"), ("mem", "Memória"), ("disk", "Disco")]

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_name("sysinfo")
        grid = Gtk.Grid(column_spacing=14, row_spacing=3)
        self.values = {}
        half = (len(self.FIELDS) + 1) // 2
        for i, (key, label) in enumerate(self.FIELDS):
            col, row = (0, i) if i < half else (2, i - half)
            k = Gtk.Label(label=label, xalign=0)
            k.get_style_context().add_class("sysinfo-key")
            v = Gtk.Label(label="…", xalign=0)
            v.get_style_context().add_class("sysinfo-val")
            v.set_ellipsize(Pango.EllipsizeMode.END)
            v.set_max_width_chars(26)
            v.set_width_chars(26)
            grid.attach(k, col, row, 1, 1)
            grid.attach(v, col + 1, row, 1, 1)
            self.values[key] = v
        self.pack_start(grid, False, False, 0)
        self.refresh()
        GLib.timeout_add_seconds(60, self.refresh)

    def refresh(self):
        if DESKTOP_VISIBLE[0]:
            threading.Thread(target=self._collect, daemon=True).start()
        return True

    def _collect(self):
        out = run("fastfetch", "-s", "Title:OS:Host:Kernel:Uptime:Packages:WM:CPU:GPU:Memory:Disk",
                  "--format", "json")
        try:
            data = {m["type"]: m.get("result") for m in json.loads(out)}
        except (ValueError, TypeError, KeyError):
            return
        GLib.idle_add(self._apply, data)

    @staticmethod
    def _gib(n):
        return f"{n / 1024 ** 3:.1f} GiB"

    def _apply(self, d):
        def get(key, fn):
            try:
                return fn(d[key]) or "?"
            except (KeyError, TypeError, IndexError, ZeroDivisionError):
                return "?"

        def uptime(u):
            secs = u["uptime"] // 1000
            h, m = secs // 3600, secs % 3600 // 60
            return f"{h}h {m:02d}min" if h else f"{m}min"

        def mem(m):
            return f"{self._gib(m['used'])} / {self._gib(m['total'])} ({m['used'] * 100 // m['total']}%)"

        def disk(ds):
            r = next(x for x in ds if x["mountpoint"] == "/")["bytes"]
            return f"{self._gib(r['used'])} / {self._gib(r['total'])} ({r['used'] * 100 // r['total']}%)"

        vals = {
            "os": get("OS", lambda o: f"{o['prettyName']} {d['Kernel']['architecture']}"),
            "host": get("Host", lambda h: h["family"] or h["name"]),
            "kernel": get("Kernel", lambda k: k["release"]),
            "uptime": get("Uptime", uptime),
            "pkgs": get("Packages", lambda p: f"{p['all']} (pacman)"),
            "shell": get("Title", lambda t: os.path.basename(t["userShell"])),  # o Shell do fastfetch seria o python
            "wm": get("WM", lambda w: f"{w['prettyName']} {w['version']} ({w['protocolName']})"),
            "term": TERMINAL,
            "cpu": get("CPU", lambda c: f"{c['cpu']} ({c['cores']['logical']})"),
            "gpu": get("GPU", lambda g: " + ".join(x["name"] for x in g)),
            "mem": get("Memory", mem),
            "disk": get("Disk", disk),
        }
        for key, val in vals.items():
            self.values[key].set_text(val)
            self.values[key].set_tooltip_text(val)
        return False


class DeskFavorites(Gtk.Stack):
    """Atalhos pros apps favoritos. Clique abre; clique direito tira da lista;
    o + abre uma busca pra escolher um app novo (Enter adiciona o primeiro)."""

    def __init__(self, launch):
        super().__init__()
        self.set_name("favorites")
        self.launch = launch
        self.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.set_transition_duration(150)
        self.set_vhomogeneous(False)
        self.set_interpolate_size(True)
        self.apps = {a["info"].get_id(): a for a in load_apps()}
        self.favorites = self.load()

        grid_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        head = Gtk.Label(label="FAVORITOS", xalign=0)
        head.get_style_context().add_class("todo-head")
        grid_page.pack_start(head, False, False, 0)
        self.grid = Gtk.FlowBox()
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_min_children_per_line(FAV_COLUMNS)
        self.grid.set_max_children_per_line(FAV_COLUMNS)
        self.grid.set_homogeneous(True)
        self.grid.set_row_spacing(6)
        self.grid.set_column_spacing(4)
        grid_page.pack_start(self.grid, False, False, 0)
        self.add_named(grid_page, "grid")

        picker = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        top = Gtk.Box(spacing=8)
        back = Gtk.Button(label="\U000f004d")  # seta pra esquerda
        back.set_can_focus(False)
        back.set_relief(Gtk.ReliefStyle.NONE)
        back.get_style_context().add_class("nav")
        back.connect("clicked", lambda *_: self.close_picker())
        self.search = Gtk.Entry()
        self.search.own_keys = True
        self.search.on_escape = self.close_picker
        self.search.set_placeholder_text("adicionar app…")
        self.search.connect("changed", lambda *_: self.fill_results())
        self.search.on_arrow = self.pick_move
        self.search.connect("activate", lambda *_: self.results and self.add(self.results[self.pick]))
        top.pack_start(back, False, False, 0)
        top.pack_start(self.search, True, True, 0)
        picker.pack_start(top, False, False, 0)
        self.result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        picker.pack_start(self.result_box, False, False, 0)
        self.add_named(picker, "picker")
        self.results = []
        self.pick = 0  # resultado marcado no picker (setas)

        self.render()
        self.set_visible_child_name("grid")

    # --- arquivo -----------------------------------------------------------------
    def load(self):
        try:
            with open(FAVORITES_FILE) as f:
                return [i for i in json.load(f) if isinstance(i, str)]
        except (OSError, ValueError):
            # primeira vez: alguns apps que já estão instalados
            return [i for i in FAV_DEFAULTS if i in self.apps]

    def save(self):
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, "w") as f:
            json.dump(self.favorites, f, indent=1)

    # --- grade ---------------------------------------------------------------------
    def render(self):
        for child in self.grid.get_children():
            self.grid.remove(child)
        self.tiles = [self.tile(self.apps[i]) for i in self.favorites if i in self.apps]
        self.tiles.append(self.tile(None))
        for btn in self.tiles:
            self.grid.add(btn)
        self.grid.show_all()
        return False

    def tile(self, app):
        btn = Gtk.Button()
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("fav")
        btn.set_size_request(FAV_TILE_WIDTH, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        btn.app = app
        btn.highlight = lambda on: None
        if app:
            color, gray = icon_pixbufs(app["info"].get_icon(), FAV_ICON_SIZE)
            icon = Gtk.Image.new_from_pixbuf(gray)
            icon.set_size_request(FAV_ICON_SIZE, FAV_ICON_SIZE)
            btn.highlight = lambda on: icon.set_from_pixbuf(color if on else gray)
            btn.nav_delete = lambda: self.remove(app)
            btn.connect("enter-notify-event", lambda *_: icon.set_from_pixbuf(color))
            btn.connect("leave-notify-event", lambda *_: icon.set_from_pixbuf(gray))
            label = Gtk.Label(label=app["name"])
            btn.set_tooltip_text(f"{app['name']}\nclique direito tira dos favoritos")
            btn.connect("clicked", lambda *_: self.launch(app))
            btn.connect("button-press-event", lambda _w, e: e.button == 3 and self.remove(app))
        else:
            icon = Gtk.Label(label="\U000f0415")
            icon.get_style_context().add_class("fav-plus")
            icon.set_size_request(FAV_ICON_SIZE, FAV_ICON_SIZE)
            label = Gtk.Label(label="adicionar")
            btn.set_tooltip_text("adicionar um app aos favoritos")
            btn.connect("clicked", lambda *_: self.open_picker())
        label.get_style_context().add_class("fav-name")
        label.set_ellipsize(3)
        label.set_max_width_chars(7)
        box.pack_start(icon, False, False, 0)
        box.pack_start(label, False, False, 0)
        btn.add(box)
        return btn

    def remove(self, app):
        self.favorites = [i for i in self.favorites if i != app["info"].get_id()]
        self.save()
        GLib.idle_add(self.render)
        return True

    # --- escolher app ------------------------------------------------------------------
    def open_picker(self):
        self.apps = {a["info"].get_id(): a for a in load_apps()}  # pega apps novos
        self.search.set_text("")
        self.fill_results()
        self.set_visible_child_name("picker")
        self.search.grab_focus()

    def close_picker(self):
        self.set_visible_child_name("grid")

    def fill_results(self):
        query = self.search.get_text().strip().lower()
        candidates = [a for i, a in self.apps.items() if i not in self.favorites]
        if query:
            ranked = sorted(((score(a, query), a["name"].lower(), a) for a in candidates
                             if score(a, query) is not None), key=lambda t: (t[0], t[1]))
            self.results = [a for *_, a in ranked[:FAV_RESULTS]]
        else:
            self.results = candidates[:FAV_RESULTS]
        for child in self.result_box.get_children():
            self.result_box.remove(child)
        for app in self.results:
            btn = Gtk.Button()
            btn.set_can_focus(False)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class("fav-result")
            row = Gtk.Box(spacing=10)
            icon = Gtk.Image.new_from_gicon(
                app["info"].get_icon() or Gio.ThemedIcon.new("application-x-executable"), Gtk.IconSize.MENU)
            icon.set_pixel_size(20)
            name = Gtk.Label(label=app["name"], xalign=0)
            name.set_ellipsize(3)
            name.set_max_width_chars(1)
            row.pack_start(icon, False, False, 0)
            row.pack_start(name, True, True, 0)
            btn.add(row)
            btn.connect("clicked", lambda _b, a=app: self.add(a))
            self.result_box.pack_start(btn, False, False, 0)
        self.result_box.show_all()
        self.pick = 0
        self.pick_move(None)

    def pick_move(self, key):
        rows = self.result_box.get_children()
        if not rows:
            return
        if key == Gdk.KEY_Down:
            self.pick = min(self.pick + 1, len(rows) - 1)
        elif key == Gdk.KEY_Up:
            self.pick = max(self.pick - 1, 0)
        for i, row in enumerate(rows):
            (row.get_style_context().add_class if i == self.pick
             else row.get_style_context().remove_class)("kbd")

    def add(self, app):
        self.favorites.append(app["info"].get_id())
        self.save()
        self.render()
        self.close_picker()
        get_window = self.get_toplevel()
        if hasattr(get_window, "entry"):
            get_window.entry.grab_focus_without_selecting()


class DeskFocus(Gtk.Box):
    """Timer de foco (pomodoro): 25 min de foco e 5 de pausa (15 a cada 4 focos).
    Durante o foco liga o Não Perturbe do dunst e depois volta como estava.
    O estado fica salvo, então reiniciar o painel não perde o timer."""

    PHASE_NAMES = {"focus": "foco", "short": "pausa", "long": "pausa longa"}

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_name("focus")
        self.state = self.load()

        head = Gtk.Box()
        title = Gtk.Label(label="FOCO", xalign=0)
        title.get_style_context().add_class("todo-head")
        self.today = Gtk.Label()
        self.today.get_style_context().add_class("todo-head")
        head.pack_start(title, False, False, 0)
        head.pack_end(self.today, False, False, 0)
        self.pack_start(head, False, False, 0)

        row = Gtk.Box(spacing=10)
        self.time = Gtk.Label(xalign=0)
        self.time.set_name("focus-time")
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        info.set_valign(Gtk.Align.CENTER)
        self.phase = Gtk.Label(xalign=0)
        self.phase.set_ellipsize(3)
        self.phase.set_max_width_chars(1)  # ocupa só o que sobra: trocar o texto não estica a linha
        self.phase.get_style_context().add_class("focus-phase")
        self.dots = Gtk.Label(xalign=0)
        self.dots.get_style_context().add_class("focus-dots")
        info.pack_start(self.phase, False, False, 0)
        info.pack_start(self.dots, False, False, 0)
        controls = Gtk.Box(spacing=2)
        controls.set_valign(Gtk.Align.CENTER)
        reset = self._ctrl("\U000f0450", lambda *_: self.reset(), "recomeçar")
        self.play = self._ctrl("\U000f040a", lambda *_: self.toggle())
        self.play.get_style_context().add_class("main")
        skip = self._ctrl("\U000f04ad", lambda *_: self.finish(skipped=True), "pular etapa")
        controls.pack_start(reset, False, False, 0)
        controls.pack_start(self.play, False, False, 0)
        controls.pack_start(skip, False, False, 0)
        row.pack_start(self.time, False, False, 0)
        row.pack_start(info, True, True, 0)
        row.pack_end(controls, False, False, 0)
        self.pack_start(row, False, False, 0)

        self.bar = Bar()
        self.pack_start(self.bar, False, False, 0)

        self.update()
        GLib.timeout_add_seconds(1, self.update)

    def _ctrl(self, glyph, callback, tooltip=None):
        btn = Gtk.Button(label=glyph)
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("ctrl")
        if tooltip:
            btn.set_tooltip_text(tooltip)
        btn.connect("clicked", callback)
        return btn

    # --- arquivo -------------------------------------------------------------------
    def load(self):
        try:
            with open(FOCUS_FILE) as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        state.setdefault("phase", "focus")
        state.setdefault("running", False)
        state.setdefault("left", FOCUS_MINUTES[state["phase"]] * 60)
        state.setdefault("cycles", 0)
        state.setdefault("dnd_prev", None)
        return state

    def save(self):
        os.makedirs(os.path.dirname(FOCUS_FILE), exist_ok=True)
        with open(FOCUS_FILE, "w") as f:
            json.dump(self.state, f, indent=1)

    # --- não perturbe ----------------------------------------------------------------
    def dnd_on(self):
        if self.state["dnd_prev"] is None:  # guarda como estava antes do foco
            self.state["dnd_prev"] = run("dunstctl", "is-paused") == "true"
            run("dunstctl", "set-paused", "true")

    def dnd_restore(self):
        if self.state["dnd_prev"] is not None:
            run("dunstctl", "set-paused", "true" if self.state["dnd_prev"] else "false")
            self.state["dnd_prev"] = None

    def sync_dnd(self):
        # foco rodando = Não Perturbe ligado; qualquer outra coisa = como estava
        if self.state["running"] and self.state["phase"] == "focus":
            self.dnd_on()
        else:
            self.dnd_restore()
        self.save()

    # --- ações ---------------------------------------------------------------------
    def left(self):
        if self.state["running"]:
            return max(0, int(round(self.state["ends"] - time.time())))
        return self.state["left"]

    def toggle(self):
        if self.state["running"]:
            self.state["left"] = self.left()
            self.state["running"] = False
        else:
            self.state["ends"] = time.time() + self.state["left"]
            self.state["running"] = True
        self.sync_dnd()
        self.update()

    def reset(self):
        self.state.update(phase="focus", running=False, left=FOCUS_MINUTES["focus"] * 60)
        self.sync_dnd()
        self.update()

    def finish(self, skipped=False):
        phase = self.state["phase"]
        if phase == "focus":
            if not skipped:
                self.count_cycle()
            long_break = self.state["cycles"] and self.state["cycles"] % FOCUS_LONG_EVERY == 0
            nxt, running = ("long" if long_break and not skipped else "short"), True
        else:
            nxt, running = "focus", False  # depois da pausa espera você dar play
        self.state.update(phase=nxt, running=running, left=FOCUS_MINUTES[nxt] * 60)
        if running:
            self.state["ends"] = time.time() + self.state["left"]
        self.sync_dnd()
        if not skipped:
            if phase == "focus":
                self.alert("Foco concluído", f"Hora de uma {self.PHASE_NAMES[nxt]} de {FOCUS_MINUTES[nxt]} min.")
            else:
                self.alert("Pausa acabou", "Bora pro próximo foco?")
        self.update()

    def count_cycle(self):
        today = datetime.date.today().isoformat()
        if self.state.get("day") != today:
            self.state.update(day=today, cycles=0)
        self.state["cycles"] += 1

    def alert(self, title, body):
        def worker():
            run("notify-send", "-a", "Foco", title, body)
            run("pw-play", FOCUS_SOUND)
        threading.Thread(target=worker, daemon=True).start()

    # --- tela ---------------------------------------------------------------------------
    def update(self):
        if self.state["running"] and self.left() <= 0:
            self.finish()
            return True
        left = self.left()
        total = FOCUS_MINUTES[self.state["phase"]] * 60
        self.time.set_text(f"{left // 60:02d}:{left % 60:02d}")
        ctx = self.time.get_style_context()
        (ctx.remove_class if self.state["running"] else ctx.add_class)("paused")
        self.phase.set_text(self.PHASE_NAMES[self.state["phase"]])  # pausado = tempo cinza
        if self.state.get("day") != datetime.date.today().isoformat():
            cycles = 0
        else:
            cycles = self.state["cycles"]
        done = cycles % FOCUS_LONG_EVERY
        self.dots.set_text("\u25cf" * done + "\u25cb" * (FOCUS_LONG_EVERY - done))
        self.today.set_text(f"{cycles} hoje" if cycles else "")
        self.play.set_label("\U000f03e4" if self.state["running"] else "\U000f040a")
        self.play.set_tooltip_text("pausar" if self.state["running"] else "começar")
        self.bar.set_fraction(1 - left / total if total else 0)
        return True


class DeskCapture(Gtk.Box):
    """Captura rápida pro Obsidian: digita, Enter e a linha vai pro fim da nota
    de capturas no INBOX. Embaixo, as notas editadas por último (clique abre)."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_name("capture")
        self.signature = None

        head = Gtk.Box()
        title = Gtk.Label(label="OBSIDIAN", xalign=0)
        title.get_style_context().add_class("todo-head")
        self.status = Gtk.Label()
        self.status.get_style_context().add_class("todo-head")
        head.pack_start(title, False, False, 0)
        head.pack_end(self.status, False, False, 0)
        self.pack_start(head, False, False, 0)

        add = Gtk.Box(spacing=8)
        pen = Gtk.Label(label="\U000f03eb")  # lápis
        pen.get_style_context().add_class("todo-plus")
        self.entry = Gtk.Entry()
        self.entry.own_keys = True
        self.entry.on_escape = lambda: self.entry.set_text("")
        self.entry.set_placeholder_text("anotar no inbox…")
        self.entry.connect("activate", self.on_capture)
        add.pack_start(pen, False, False, 0)
        add.pack_start(self.entry, True, True, 0)
        self.pack_start(add, False, False, 0)

        self.recent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(self.recent, False, False, 0)

        self.refresh()
        GLib.timeout_add_seconds(30, self.refresh)

    # --- capturar -------------------------------------------------------------------
    def on_capture(self, entry):
        text = entry.get_text().strip()
        if not text:
            return
        try:
            self.append(text)
        except OSError as e:
            self.flash(f"erro: {e.strerror}")
            return
        entry.set_text("")
        self.flash("salvo \U000f012c")
        self.refresh()

    def append(self, text):
        path = os.path.join(OBSIDIAN_VAULT, OBSIDIAN_CAPTURE)
        name = os.path.splitext(os.path.basename(OBSIDIAN_CAPTURE))[0]
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("---\ntags: [inbox]\n---\n# ⚡ Capturas rápidas\n\n"
                        "Anotações feitas pela área de trabalho. Revise junto com o "
                        "[[📥 Inbox]] e mova o que valer pra uma nota própria.\n\n")
            self.link_in_inbox(name)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(path, "a") as f:
            f.write(f"- **{stamp}** {text}\n")

    def link_in_inbox(self, name):
        # põe [[⚡ Capturas rápidas]] em "## Pendentes" do Inbox, uma vez só
        inbox = os.path.join(OBSIDIAN_VAULT, OBSIDIAN_INBOX)
        try:
            with open(inbox) as f:
                content = f.read()
        except OSError:
            return
        link = f"[[{name}]]"
        if link in content or "## Pendentes\n" not in content:
            return
        content = content.replace("## Pendentes\n", f"## Pendentes\n- {link}\n", 1)
        with open(inbox, "w") as f:
            f.write(content)

    def flash(self, text):
        self.status.set_text(text)
        GLib.timeout_add_seconds(2, lambda: self.status.set_text("") or False)

    # --- recentes ------------------------------------------------------------------
    def refresh(self):
        if not DESKTOP_VISIBLE[0]:
            return True
        notes = []
        for root, dirs, files in os.walk(OBSIDIAN_VAULT):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.endswith(".md"):
                    path = os.path.join(root, name)
                    try:
                        notes.append((os.path.getmtime(path), path))
                    except OSError:
                        pass
        notes = sorted(notes, reverse=True)[:OBSIDIAN_RECENT]
        now = time.time()
        signature = tuple((p, int((now - m) // 60)) for m, p in notes)
        if signature == self.signature:
            return True
        self.signature = signature
        for child in self.recent.get_children():
            self.recent.remove(child)
        for mtime, path in notes:
            self.recent.pack_start(self.note_row(path, now - mtime), False, False, 0)
        self.recent.show_all()
        return True

    def note_row(self, path, age):
        btn = Gtk.Button()
        btn.set_can_focus(False)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("note")
        row = Gtk.Box(spacing=8)
        name = Gtk.Label(label=os.path.splitext(os.path.basename(path))[0], xalign=0)
        name.get_style_context().add_class("note-name")
        name.set_ellipsize(3)
        name.set_max_width_chars(1)
        when = Gtk.Label(label=time_ago(age))
        when.get_style_context().add_class("note-age")
        row.pack_start(name, True, True, 0)
        row.pack_end(when, False, False, 0)
        btn.add(row)
        rel = os.path.relpath(path, OBSIDIAN_VAULT)
        btn.set_tooltip_text(rel)
        btn.connect("clicked", lambda *_: self.open_note(rel))
        return btn

    def open_note(self, rel):
        vault = os.path.basename(OBSIDIAN_VAULT)
        url = ("obsidian://open?vault=" + urllib.parse.quote(vault)
               + "&file=" + urllib.parse.quote(rel))
        subprocess.Popen(["xdg-open", url], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class LeftPanel(Gtk.EventBox):
    """Coluna da esquerda, espelho da direita: clima em cima, timer de foco,
    captura pro Obsidian e notificações ocupando o resto da altura."""

    def __init__(self, launch):
        super().__init__()
        self.set_visible_window(False)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.FILL)
        self.set_margin_top(WAYBAR_HEIGHT)
        self.set_margin_bottom(PANEL_BOTTOM)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.set_name("side-panel")
        panel.set_size_request(PANEL_WIDTH, -1)
        self.add(panel)

        weather = DeskWeather()
        weather_area = Gtk.EventBox()  # clicar no clima atualiza na hora
        weather_area.set_visible_window(False)
        weather_area.set_tooltip_text("clique pra atualizar")
        weather_area.connect("button-press-event", lambda *_: weather.refresh())
        weather_area.add(weather)
        weather_area.nav_style = weather
        weather_area.nav_activate = weather.refresh
        weather_area.set_margin_bottom(14)
        panel.pack_start(weather_area, False, False, 0)
        self.focus = focus = DeskFocus()
        focus.set_margin_bottom(18)
        panel.pack_start(focus, False, False, 0)
        capture = DeskCapture()
        capture.set_margin_bottom(18)
        panel.pack_start(capture, False, False, 0)
        self.notifs = DeskNotifications()
        self.middle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.middle.pack_start(self.notifs, False, False, 0)
        panel.pack_start(self.middle, True, True, 0)

    def align_to(self, _target):
        # a lista de notificações rola dentro do espaço que sobra até o rodapé
        space = self.middle.get_allocated_height()
        if space > 1:
            max_height = max(TODO_MIN_HEIGHT, space - 50)
            if self.notifs.max_height != max_height:
                self.notifs.max_height = max_height
                self.notifs.fit_height()
        return False


class Welcome(Gtk.Window):
    def __init__(self):
        super().__init__()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "welcome")
        if MENU_MODE:
            self.set_visual(self.get_screen().get_rgba_visual())
            self.get_style_context().add_class("menu")
            GtkLayerShell.set_namespace(self, "welcome-menu")
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        else:
            GtkLayerShell.set_layer(self, GtkLayerShell.Layer.BACKGROUND)
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)
        GtkLayerShell.set_exclusive_zone(self, -1)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE if MENU_MODE
                                        else GtkLayerShell.KeyboardMode.ON_DEMAND)

        self.apps = load_apps()
        self.results = []
        self.typing_id = None
        self.nav = None  # item marcado pelas setas (None = barra de busca)

        self.outer = outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_size_request(MENU_WIDTH if MENU_MODE else DESK_WIDTH, -1)
        self.root = root = Gtk.Overlay()
        root.add(outer)
        if not MENU_MODE:
            self.side = SidePanel()
            root.add_overlay(self.side)
            self.left = LeftPanel(self.launch)
            root.add_overlay(self.left)
        self.add(root)

        # Logo do Arch (branco) centralizado acima da frase
        logo = Gtk.Image()
        try:
            logo.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(GHOST, GHOST_SIZE, GHOST_SIZE))
        except GLib.Error:
            logo = Gtk.Label(label="\uf303")
        logo.set_halign(Gtk.Align.CENTER)
        outer.pack_start(logo, False, False, 0)

        self.greeting = Gtk.Label(xalign=0.5)
        self.greeting.set_justify(Gtk.Justification.CENTER)
        self.greeting.set_name("greeting")
        self.greeting.set_margin_top(20)
        self.greeting.set_margin_bottom(16)
        outer.pack_start(self.greeting, False, False, 0)

        hints_bar = Gtk.Box(spacing=10)
        hints_bar.set_name("hints-bar")
        hints_bar.set_halign(Gtk.Align.CENTER)
        for key, desc in [("=", "calc"), ("?", "web"), ("n ", "notas"), (">", "cmd")]:
            chip = Gtk.Box(spacing=4)
            chip.get_style_context().add_class("hint-chip")
            key_lbl = Gtk.Label(label=key.strip())
            key_lbl.get_style_context().add_class("hint-key")
            sep = Gtk.Label(label="→")
            sep.get_style_context().add_class("hint-sep")
            desc_lbl = Gtk.Label(label=desc)
            chip.pack_start(key_lbl, False, False, 0)
            chip.pack_start(sep, False, False, 0)
            chip.pack_start(desc_lbl, False, False, 0)
            hints_bar.pack_start(chip, False, False, 0)
        outer.pack_start(hints_bar, False, False, 0)

        self.prompt_box = prompt_box = Gtk.Box(spacing=8)
        prompt_box.set_name("prompt-box")
        prompt = Gtk.Label(label=">")
        prompt.set_name("prompt")
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.nav_skip = True  # a barra é o "ponto de partida" das setas, não um item
        self.entry.connect("changed", self.on_changed)
        self.entry.connect("activate", lambda *_: self.launch_selected())
        prompt_box.pack_start(prompt, False, False, 0)
        prompt_box.pack_start(self.entry, True, True, 0)
        outer.pack_start(prompt_box, False, False, 0)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.revealer.set_transition_duration(180)
        results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        results_box.set_margin_top(10)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.listbox.connect("row-activated", lambda _lb, row: self.launch(row.app))
        self.listbox.connect("row-selected", self.on_row_selected)
        self.empty = Gtk.Label(label="nenhum app encontrado", xalign=0)
        self.empty.set_name("empty")
        results_box.pack_start(self.listbox, False, False, 0)
        results_box.pack_start(self.empty, False, False, 0)
        self.revealer.add(results_box)
        outer.pack_start(self.revealer, False, False, 0)

        # favoritos embaixo da barra de input (somem enquanto tem busca aberta)
        self.favorites = None
        if not MENU_MODE:
            self.favorites = DeskFavorites(self.launch)
            self.favorites.set_margin_top(20)
            self.favorites.set_halign(Gtk.Align.CENTER)
            outer.pack_start(self.favorites, False, False, 0)
            # ficha do PC fica num overlay pra não empurrar o resto pra cima;
            # on_allocate cola ela embaixo dos favoritos
            self.sysinfo = SysInfo()
            self.sysinfo.set_halign(Gtk.Align.CENTER)
            self.sysinfo.set_valign(Gtk.Align.START)
            self.root.add_overlay(self.sysinfo)

        self.connect("key-press-event", self.on_key)
        if not MENU_MODE:
            self.connect("size-allocate", self.on_allocate)
            # com o teclado exclusivo o Hyprland manda até o mouse da waybar pra cá;
            # na faixa da waybar solta (ON_DEMAND) pra ela receber o clique
            self.bar_hover = False
            self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
            self.connect("motion-notify-event", self.on_motion)
        if MENU_MODE:
            self.connect("button-press-event", self.on_click)
        self.show_all()
        self.empty.hide()
        self.type_greeting()

    def on_allocate(self, *_):
        # com resultados abertos a barra sobe; o status fica onde estava
        if not self.revealer.get_reveal_child() and not self.revealer.get_child_revealed():
            GLib.idle_add(self.side.align_to, self.prompt_box)
            GLib.idle_add(self.left.align_to, self.prompt_box)
            GLib.idle_add(self.align_sysinfo)

    def align_sysinfo(self):
        pos = self.favorites.translate_coordinates(self.root, 0, 0)
        if pos:
            top = pos[1] + self.favorites.get_allocated_height() + 28
            if self.sysinfo.get_margin_top() != top:
                self.sysinfo.set_margin_top(top)
        return False

    # --- animação do texto -------------------------------------------------
    def type_greeting(self):
        if self.typing_id:
            GLib.source_remove(self.typing_id)
        text = greeting_text()
        pos = [0]

        def step():
            pos[0] += 1
            self.greeting.set_text(text[:pos[0]] + ("▌" if pos[0] < len(text) else ""))
            if pos[0] >= len(text):
                self.typing_id = None
                return False
            return True

        self.greeting.set_text("")
        self.typing_id = GLib.timeout_add(35, step)

    # --- busca -------------------------------------------------------------
    def on_changed(self, entry):
        raw = entry.get_text().lstrip()
        query = raw.strip().lower()
        if self.favorites:
            self.favorites.set_visible(not query)
            self.sysinfo.set_visible(not query)
        if not query:
            self.show_results([])
            self.revealer.set_reveal_child(False)
            return
        # prefixos: "=" conta, "?" pesquisa na web, "n " notas do Obsidian, ">" comando
        if raw.startswith("="):
            self.calculate(raw[1:].strip())
            return
        if raw.startswith("?"):
            term = raw[1:].strip()
            self.show_results([action(
                f"Pesquisar “{term}”" if term else "Pesquisar na web…", "\U000f0349",
                "Enter abre no navegador" if term else "digite o que procurar depois do ?",
                (lambda: open_url(WEB_SEARCH + urllib.parse.quote(term))) if term else None)])
            return
        if raw.lower().startswith("n "):
            self.show_results(self.note_results(raw[2:].strip()))
            return
        if raw.startswith(">"):
            cmd = raw[1:].strip()
            self.show_results([action(
                cmd or "Rodar um comando…", "\U000f018d",
                "Enter roda no terminal" if cmd else "digite o comando depois do >",
                (lambda: run_in_terminal(cmd)) if cmd else None)])
            return
        ranked = []
        for app in self.apps:
            s = score(app, query)
            if s is not None:
                ranked.append((s, app["name"].lower(), app))
        ranked.sort(key=lambda t: (t[0], t[1]))
        self.show_results([a for _, _, a in ranked[:MAX_RESULTS]])

    def show_results(self, results):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        self.results = results
        if not results and not self.entry.get_text().strip():
            return
        for app in self.results:
            self.listbox.add(self.make_row(app))
        self.listbox.show_all()
        self.empty.set_visible(not self.results)
        first = self.listbox.get_row_at_index(0)
        if first:
            self.listbox.select_row(first)
        self.revealer.set_reveal_child(True)

    # --- calculadora (qalc) e notas ------------------------------------------------
    def calculate(self, expr):
        if not expr:
            self.show_results([action("Calculadora…", "\U000f00ec",
                                      "ex.: = 15% de 340  ·  = 10 km to mi  ·  = 100 USD to BRL", None)])
            return
        text = self.entry.get_text()

        def worker():
            # "15% de 340" -> "15% * 340" (o qalc em português não entende o "de")
            fixed = re.sub(r"(\d[\d.,]*)\s*%\s*(?:de|of)\s+", r"\1% * ", expr, flags=re.I)
            result = run("qalc", "-t", fixed).splitlines()
            result = result[-1].strip() if result else ""
            GLib.idle_add(show, result)

        def show(result):
            if self.entry.get_text() != text:  # já digitou outra coisa
                return False
            if result:
                self.show_results([action(f"= {result}", "\U000f00ec", "Enter copia o resultado",
                                          lambda: copy_text(result), stay=True)])
            else:
                self.show_results([action("Conta inválida", "\U000f00ec", expr, None)])
            return False
        threading.Thread(target=worker, daemon=True).start()

    def note_results(self, term):
        notes = []
        for root, dirs, files in os.walk(OBSIDIAN_VAULT):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.endswith(".md"):
                    notes.append(os.path.relpath(os.path.join(root, name), OBSIDIAN_VAULT))
        term = term.lower()
        ranked = []
        for rel in notes:
            title = os.path.splitext(os.path.basename(rel))[0]
            plain = re.sub(r"[^\w\s]", "", title.lower()).strip()  # sem emoji na frente
            if not term:
                rank = 2
            elif plain.startswith(term) or title.lower().startswith(term):
                rank = 0
            elif term in title.lower():
                rank = 1
            else:
                continue
            ranked.append((rank, title.lower(), rel, title))
        ranked.sort()
        results = [action(title, "\U000f09ed", os.path.dirname(rel) or "cofre",
                          lambda rel=rel: open_url("obsidian://open?vault="
                                                   + urllib.parse.quote(os.path.basename(OBSIDIAN_VAULT))
                                                   + "&file=" + urllib.parse.quote(rel)))
                   for _rank, _key, rel, title in ranked[:MAX_RESULTS]]
        return results or [action("Nenhuma nota encontrada", "\U000f09ed", term, None)]

    def make_row(self, app):
        row = Gtk.ListBoxRow()
        row.app = app
        row.set_size_request(-1, ROW_HEIGHT)
        box = Gtk.Box(spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        row.arrow = Gtk.Label(label=" ")
        row.arrow.get_style_context().add_class("arrow")
        if "glyph" in app:  # ação (conta, pesquisa, nota, comando)
            icon = Gtk.Label(label=app["glyph"])
            icon.get_style_context().add_class("action-icon")
        else:
            icon = Gtk.Image.new_from_gicon(
                app["info"].get_icon() or Gio.ThemedIcon.new("application-x-executable"),
                Gtk.IconSize.DND)
            icon.set_pixel_size(ICON_SIZE)  # força o tamanho mesmo p/ ícone em arquivo/SVG
        icon.set_size_request(ICON_SIZE, ICON_SIZE)
        name = Gtk.Label(label=app["name"], xalign=0)
        name.get_style_context().add_class("app-name")
        name.set_ellipsize(3)  # Pango.EllipsizeMode.END
        name.set_max_width_chars(30)
        name.set_single_line_mode(True)
        desc = Gtk.Label(label=app["desc"], xalign=0)
        desc.get_style_context().add_class("app-desc")
        desc.set_ellipsize(3)
        desc.set_max_width_chars(1)  # não alarga o menu; ocupa só o que sobrar
        desc.set_single_line_mode(True)
        box.pack_start(row.arrow, False, False, 0)
        box.pack_start(icon, False, False, 0)
        box.pack_start(name, False, False, 0)
        box.pack_start(desc, True, True, 0)
        row.add(box)
        return row

    def on_row_selected(self, _lb, selected):
        for row in self.listbox.get_children():
            row.arrow.set_text("❯" if row is selected else " ")

    def move(self, delta):
        row = self.listbox.get_selected_row()
        idx = (row.get_index() if row else -1) + delta
        n = len(self.listbox.get_children())
        if n:
            self.listbox.select_row(self.listbox.get_row_at_index(max(0, min(n - 1, idx))))

    def on_key(self, _w, event):
        key = event.keyval
        if getattr(self.get_focus(), "own_keys", False):  # digitando uma tarefa / busca
            if key == Gdk.KEY_Escape:
                getattr(self.get_focus(), "on_escape", lambda: None)()
                self.get_focus().set_text("")
                self.entry.grab_focus_without_selecting()
                return True
            focus = self.get_focus()
            on_arrow = getattr(focus, "on_arrow", None)
            if on_arrow and key in (Gdk.KEY_Up, Gdk.KEY_Down):
                on_arrow(key)
                return True
            if key in (Gdk.KEY_Up, Gdk.KEY_Down) and not focus.get_text():
                # campo vazio: as setas saem dele e voltam a navegar
                self.entry.grab_focus_without_selecting()
                self.set_nav(focus)
                self.nav_move(key)
                return True
            return False
        if self.nav_key(key):
            return True
        if key == Gdk.KEY_Escape:
            if MENU_MODE:
                self.close()
            self.reset()
            return True
        if key in (Gdk.KEY_Down, Gdk.KEY_Tab):
            self.move(1)
            return True
        if key in (Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab):
            self.move(-1)
            return True
        self._focus_entry()
        return False

    # --- navegação pelo teclado: setas vão pro item mais perto naquela direção ----------
    NAV_ARROWS = (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right,
                  Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab)

    def nav_key(self, key):
        """Barra vazia: setas andam pela tela toda. True = tecla usada."""
        if MENU_MODE or self.entry.get_text().strip():
            return False
        nav = self.nav
        if nav is not None and not nav.get_mapped():
            self.set_nav(None)
            nav = None
        if key in self.NAV_ARROWS:
            if (isinstance(nav, Gtk.Scale) and key in (Gdk.KEY_Left, Gdk.KEY_Right)):
                d = 1 if key == Gdk.KEY_Right else -1
                if hasattr(nav, "nav_adjust"):
                    nav.nav_adjust(d)
                else:
                    nav.emit("change-value", Gtk.ScrollType.JUMP, nav.get_value() + 5 * d)
                return True
            if nav is None and key == Gdk.KEY_Up:
                return False
            self.nav_move(key)
            return True
        if nav is None:
            return False
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self.nav_run(nav, getattr(nav, "nav_activate", None))
            return True
        if key in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
            if hasattr(nav, "nav_delete"):
                self.nav_run(nav, nav.nav_delete)
            return True
        self.set_nav(None)  # Esc ou começou a digitar: volta pra barra
        return key == Gdk.KEY_Escape

    def set_nav(self, widget):
        old = getattr(self, "nav", None)
        if old is not None:
            getattr(old, "nav_style", old).get_style_context().remove_class("kbd")
            getattr(old, "highlight", lambda on: None)(False)
        self.nav = widget
        if widget is not None:
            getattr(widget, "nav_style", widget).get_style_context().add_class("kbd")
            getattr(widget, "highlight", lambda on: None)(True)
            self.scroll_into_view(widget)

    def nav_targets(self):
        out = []

        def walk(w):
            if not (w.get_visible() and w.get_mapped()) or getattr(w, "nav_skip", False):
                return
            if hasattr(w, "nav_activate") or (
                    isinstance(w, (Gtk.Button, Gtk.Entry, Gtk.Scale))
                    and w.get_sensitive() and w.get_opacity() > 0):
                out.append(w)
                return
            if isinstance(w, Gtk.Container):
                for child in w.get_children():
                    walk(child)
        walk(self.root)
        return out

    def nav_rect(self, w):
        if w is self.entry:
            w = self.prompt_box
        pos = w.translate_coordinates(self, 0, 0) or (0, 0)
        return pos[0], pos[1], w.get_allocated_width(), w.get_allocated_height()

    def nav_move(self, key):
        if key == Gdk.KEY_Tab:
            key = Gdk.KEY_Right
        elif key == Gdk.KEY_ISO_Left_Tab:
            key = Gdk.KEY_Left
        cur = self.nav or self.entry
        x, y, w, h = self.nav_rect(cur)
        cx, cy = x + w / 2, y + h / 2
        best, best_score = None, None
        for t in self.nav_targets():
            if t is cur:
                continue
            tx, ty, tw, th = self.nav_rect(t)
            tcx, tcy = tx + tw / 2, ty + th / 2
            vgap = max(0, ty - (y + h), y - (ty + th))
            hgap = max(0, tx - (x + w), x - (tx + tw))
            if key == Gdk.KEY_Right and tx >= cx and tcx > cx:
                score = hgap + 4 * vgap + 0.05 * abs(tcy - cy)
            elif key == Gdk.KEY_Left and tx + tw <= cx and tcx < cx:
                score = hgap + 4 * vgap + 0.05 * abs(tcy - cy)
            elif key == Gdk.KEY_Down and ty >= cy and tcy > cy:
                score = vgap + 4 * hgap + 0.05 * abs(tcx - cx)
            elif key == Gdk.KEY_Up and ty + th <= cy and tcy < cy:
                score = vgap + 4 * hgap + 0.05 * abs(tcx - cx)
            else:
                continue
            if best_score is None or score < best_score:
                best, best_score = t, score
        # subir pro campo de busca principal também vale
        if key == Gdk.KEY_Up and self.nav is not None:
            ex, ey, ew, eh = self.nav_rect(self.entry)
            if ey + eh <= cy:
                score = max(0, y - (ey + eh)) + 4 * max(0, ex - (x + w), x - (ex + ew))
                if best_score is None or score < best_score:
                    best = self.entry
        if best is self.entry:
            self.set_nav(None)
        elif best is not None:
            self.set_nav(best)

    def nav_run(self, widget, fn):
        rect = self.nav_rect(widget)
        if fn:
            fn()
        elif isinstance(widget, Gtk.Entry):
            self.set_nav(None)
            widget.grab_focus()
            return
        elif isinstance(widget, Gtk.Button):
            widget.clicked()
        if self.get_focus() is not self.entry:  # abriu outro campo (ex.: + dos favoritos)
            self.set_nav(None)
            return
        # se o item foi recriado (tarefa marcada, favorito removido), pega o mais perto
        GLib.timeout_add(80, self.nav_restore, widget, rect)

    def nav_restore(self, widget, rect):
        if self.nav is widget and not widget.get_mapped():
            x, y, w, h = rect
            targets = self.nav_targets()
            if targets:
                def dist(t):
                    tx, ty, tw, th = self.nav_rect(t)
                    return abs(tx + tw / 2 - x - w / 2) + abs(ty + th / 2 - y - h / 2)
                self.set_nav(min(targets, key=dist))
            else:
                self.set_nav(None)
        return False

    def scroll_into_view(self, widget):
        parent = widget.get_parent()
        while parent is not None and not isinstance(parent, Gtk.ScrolledWindow):
            parent = parent.get_parent()
        if parent is None:
            return
        child = parent.get_child()
        inner = child.get_child() if isinstance(child, Gtk.Viewport) else child
        pos = widget.translate_coordinates(inner, 0, 0)
        if not pos:
            return
        adj = parent.get_vadjustment()
        top, height = pos[1], widget.get_allocated_height()
        if top < adj.get_value():
            adj.set_value(top)
        elif top + height > adj.get_value() + adj.get_page_size():
            adj.set_value(top + height - adj.get_page_size())

    def on_click(self, _w, event):
        # clicou fora do conteúdo central -> fecha o menu
        if Gtk.get_event_widget(event) is not self:
            return False  # clique na lista/campo (coordenadas relativas a eles)
        alloc = self.outer.get_allocation()
        inside = (alloc.x <= event.x <= alloc.x + alloc.width
                  and alloc.y <= event.y <= alloc.y + alloc.height)
        if not inside:
            self.close()
        return False

    def _focus_entry(self):
        if not self.entry.has_focus():
            self.entry.grab_focus_without_selecting()
        return False

    # --- abrir apps ----------------------------------------------------------
    def launch_selected(self):
        row = self.listbox.get_selected_row()
        if row:
            self.launch(row.app)

    def launch(self, app):
        if "glyph" in app:  # ação
            if app["run"] is None:
                return
            app["run"]()
            if MENU_MODE:
                self.close()
            elif not app.get("stay"):
                self.set_workspace_empty(False)
                GLib.timeout_add_seconds(8, lambda: self.set_workspace_empty(workspace_is_empty()))
            self.reset()
            return
        app_id = app["info"].get_id()
        if app_id.endswith(".desktop"):
            app_id = app_id[:-len(".desktop")]
        # uwsm cria um scope systemd próprio pro app (não fica preso a este processo)
        cmd = ["uwsm", "app", "--", f"{app_id}.desktop"]
        try:
            subprocess.Popen(cmd, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            app["info"].launch([], None)
        if MENU_MODE:
            self.close()
        else:
            # solta o teclado já, pro app abrir com o foco; se ele não abrir
            # nada no workspace, volta a escutar depois de alguns segundos
            self.set_workspace_empty(False)
            GLib.timeout_add_seconds(8, lambda: self.set_workspace_empty(workspace_is_empty()))
        self.reset()

    def reset(self):
        self.set_nav(None)
        self.entry.set_text("")
        self.revealer.set_reveal_child(False)

    def on_motion(self, _w, event):
        over_bar = event.y_root < WAYBAR_HEIGHT
        if over_bar != self.bar_hover and DESKTOP_VISIBLE[0]:
            self.bar_hover = over_bar
            GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND if over_bar
                                            else GtkLayerShell.KeyboardMode.EXCLUSIVE)
        return False

    # --- foco automático -------------------------------------------------------
    def set_workspace_empty(self, empty):
        DESKTOP_VISIBLE[0] = empty
        # Workspace vazio: pega o teclado sozinha, pra já poder digitar.
        # Com janelas abertas: nunca pega o teclado (as janelas têm prioridade).
        mode = (GtkLayerShell.KeyboardMode.EXCLUSIVE if empty
                else GtkLayerShell.KeyboardMode.NONE)
        self.bar_hover = False
        if GtkLayerShell.get_keyboard_mode(self) != mode:
            GtkLayerShell.set_keyboard_mode(self, mode)
            if empty:
                self.apps = load_apps()  # pega apps instalados recentemente
                self.reset()
                self.type_greeting()
                self.entry.grab_focus()
        return False


def action(name, glyph, desc, run_fn, stay=False):
    """Resultado da barra de input que não é app (Enter roda run_fn).
    stay=True: não abre janela, então o painel continua com o teclado."""
    return {"name": name, "glyph": glyph, "desc": desc, "run": run_fn, "stay": stay}


def open_url(url):
    subprocess.Popen(["xdg-open", url], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_in_terminal(cmd):
    # --hold: o terminal fica aberto mostrando a saída
    subprocess.Popen([TERMINAL, "--hold", "sh", "-c", cmd], start_new_session=True,
                     cwd=os.path.expanduser("~"),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def copy_text(text):
    subprocess.run(["wl-copy", text], timeout=3)
    subprocess.Popen(["notify-send", "-a", "Calculadora", "Copiado", text],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def focus_window(address):
    # garante que a janela recém-aberta fique com o foco do teclado
    subprocess.run(["hyprctl", "dispatch", f"hl.dsp.focus({{ window = 'address:0x{address}' }})"],
                   capture_output=True)
    return False


def hypr(*args):
    out = subprocess.run(["hyprctl", *args, "-j"], capture_output=True, text=True).stdout
    return json.loads(out or "{}")


def workspace_is_empty():
    try:
        return hypr("activeworkspace").get("windows", 1) == 0
    except Exception:
        return False


def watch_hyprland(win):
    path = os.path.join(os.environ["XDG_RUNTIME_DIR"], "hypr",
                        os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket2.sock")
    events = (b"openwindow>>", b"closewindow>>", b"workspace>>", b"workspacev2>>",
              b"movewindow>>", b"movewindowv2>>", b"focusedmon>>", b"focusedmonv2>>")
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(path)
                buf = b""
                while chunk := s.recv(4096):
                    buf += chunk
                    *lines, buf = buf.split(b"\n")
                    if any(l.startswith(events) for l in lines):
                        GLib.idle_add(win.set_workspace_empty, workspace_is_empty())
                    for l in lines:
                        if l.startswith(b"openwindow>>"):
                            addr, workspace = l[len(b"openwindow>>"):].split(b",", 2)[:2]
                            if not workspace.startswith(b"special:"):  # não abre workspaces especiais
                                GLib.idle_add(focus_window, addr.decode())
        except OSError:
            pass
        threading.Event().wait(2)


def main():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    win = Welcome()
    win.connect("destroy", Gtk.main_quit)
    if MENU_MODE:
        win.entry.grab_focus()
    else:
        # clique no relógio da waybar = play/pause do foco
        with open(DESK_PIDFILE, "w") as f:
            f.write(str(os.getpid()))
        try:
            gi.require_version("GLibUnix", "2.0")
            from gi.repository import GLibUnix
            add_signal = GLibUnix.signal_add
        except (ValueError, ImportError):
            add_signal = GLib.unix_signal_add
        add_signal(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: win.left.focus.toggle() or True)
        win.set_workspace_empty(workspace_is_empty())
        threading.Thread(target=watch_hyprland, args=(win,), daemon=True).start()
    Gtk.main()


def toggle_menu():
    # Se o menu já está aberto, fecha ele em vez de abrir outro.
    try:
        with open(MENU_PIDFILE) as f:
            pid = int(f.read())
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            if b"welcome.py" in f.read():
                os.kill(pid, signal.SIGTERM)
                return True
    except (OSError, ValueError):
        pass
    with open(MENU_PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    return False


if __name__ == "__main__":
    if not (MENU_MODE and toggle_menu()):
        main()
