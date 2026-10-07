#!/usr/bin/env python3
"""custom/active-app da waybar: nome do app em foco (o nome do atalho .desktop,
ex.: "Visual Studio Code" em vez de "code"). Escuta o socket de eventos do
Hyprland e imprime uma linha JSON a cada troca de foco."""
import json
import os
import re
import socket
import subprocess
import sys
import time

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402
try:
    gi.require_version("GioUnix", "2.0")
    from gi.repository import GioUnix  # noqa: E402
    DesktopAppInfo = GioUnix.DesktopAppInfo
except (ValueError, ImportError):
    DesktopAppInfo = Gio.DesktopAppInfo


def app_index():
    # prioridade: id do .desktop > StartupWMClass > executável (só apps visíveis)
    infos = [i for i in Gio.AppInfo.get_all() if isinstance(i, DesktopAppInfo)]
    getters = [lambda i: (i.get_id() or "").removesuffix(".desktop"),
               lambda i: i.get_startup_wm_class() or "",
               lambda i: os.path.basename(i.get_executable() or "") if i.should_show() else ""]
    index = {}
    for get in getters:
        for info in infos:
            key = get(info).lower()
            if not key:
                continue
            name = re.sub(r"\s*\(.*\)$", "", info.get_display_name() or info.get_name() or "")
            index.setdefault(key, name)
            index.setdefault(key.split(".")[-1], name)
    return index


APPS = app_index()


def emit(window_class, title):
    if not window_class:
        out = {"text": "", "class": "empty"}
    else:
        name = APPS.get(window_class.lower()) or APPS.get(window_class.lower().split(".")[-1]) \
            or window_class.capitalize()
        out = {"text": name, "tooltip": title or name, "class": "app"}
    print(json.dumps(out), flush=True)


def current():
    out = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True).stdout
    try:
        data = json.loads(out)
        return data.get("class", ""), data.get("title", "")
    except (ValueError, AttributeError):
        return "", ""


path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "hypr",
                    os.environ["HYPRLAND_INSTANCE_SIGNATURE"], ".socket2.sock")
emit(*current())
while True:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(path)
            buf = b""
            while chunk := s.recv(4096):
                buf += chunk
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    if line.startswith(b"activewindow>>"):
                        cls, _, title = line[len(b"activewindow>>"):].decode(errors="replace").partition(",")
                        emit(cls, title)
    except OSError:
        pass
    except BrokenPipeError:
        sys.exit(0)
    time.sleep(2)
