#!/usr/bin/env python3
"""Mixer de volume estilo popup, no mesmo espirito do menu de bluetooth
da waybar: uma janelinha ancorada no canto superior direito, com sliders
arrastaveis para o volume geral e para cada app tocando audio."""

import gi
import json
import re
import subprocess

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

REFRESH_MS = 1000
MAX_VOL = 150

ICON_MUTE = "\U000f075f"   # 󰝟
ICON_LOW = "\U000f057f"    # 󰕿
ICON_MID = "\U000f0580"    # 󰖀
ICON_HIGH = "\U000f057e"   # 󰕾


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return ""


def icon_for(vol, muted):
    if muted or vol <= 0:
        return ICON_MUTE
    if vol < 33:
        return ICON_LOW
    if vol < 66:
        return ICON_MID
    return ICON_HIGH


def get_master():
    out = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r"Volume:\s*([\d.]+)", out)
    vol = round(float(m.group(1)) * 100) if m else 0
    muted = "MUTED" in out
    return vol, muted


def set_master_volume(pct):
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct / 100:.2f}"])


def toggle_master_mute():
    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])


def get_sink_inputs():
    out = run(["pactl", "-f", "json", "list", "sink-inputs"])
    try:
        data = json.loads(out)
    except Exception:
        data = []

    apps = []
    for item in data:
        idx = item.get("index")
        props = item.get("properties", {})
        name = (
            props.get("application.name")
            or props.get("media.name")
            or props.get("node.name")
            or "App"
        )
        vols = item.get("volume", {})
        pct = 0
        for v in vols.values():
            vp = v.get("value_percent", "0%").rstrip("%")
            try:
                pct = max(pct, round(float(vp)))
            except ValueError:
                pass
        apps.append({"id": idx, "name": name, "volume": pct, "muted": bool(item.get("mute"))})
    apps.sort(key=lambda a: a["id"])
    return apps


def set_app_volume(idx, pct):
    subprocess.run(["pactl", "set-sink-input-volume", str(idx), f"{int(pct)}%"])


def toggle_app_mute(idx):
    subprocess.run(["pactl", "set-sink-input-mute", str(idx), "toggle"])


class Row(Gtk.Box):
    def __init__(self, name, volume, muted, on_volume, on_mute):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_name("row")
        self.on_volume = on_volume
        self.dragging = False

        self.icon_btn = Gtk.Button(label=icon_for(volume, muted))
        self.icon_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.icon_btn.get_style_context().add_class("icon-btn")
        self.icon_btn.connect("clicked", lambda _b: on_mute())
        self.pack_start(self.icon_btn, False, False, 0)

        self.name_lbl = Gtk.Label(label=name)
        self.name_lbl.set_xalign(0)
        self.name_lbl.set_width_chars(11)
        self.name_lbl.set_max_width_chars(11)
        self.name_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self.pack_start(self.name_lbl, False, False, 0)

        adj = Gtk.Adjustment(value=volume, lower=0, upper=MAX_VOL, step_increment=1, page_increment=5)
        self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self.scale.set_draw_value(False)
        self.scale.add_mark(100, Gtk.PositionType.TOP, None)
        self.scale.set_hexpand(True)
        self.scale.connect("value-changed", self._on_change)
        self.scale.connect("button-press-event", lambda *_a: self._set_dragging(True))
        self.scale.connect("button-release-event", lambda *_a: self._set_dragging(False))
        self.pack_start(self.scale, True, True, 0)

        self.pct_lbl = Gtk.Label(label=f"{volume}%")
        self.pct_lbl.set_width_chars(4)
        self.pack_start(self.pct_lbl, False, False, 0)

        self.muted = muted
        self._apply_mute_style()

    def _set_dragging(self, state):
        self.dragging = state

    def _on_change(self, scale):
        val = round(scale.get_value())
        self.pct_lbl.set_text(f"{val}%")
        self.on_volume(val)

    def _apply_mute_style(self):
        ctx = self.get_style_context()
        if self.muted:
            ctx.add_class("muted")
        else:
            ctx.remove_class("muted")

    def refresh(self, volume, muted):
        self.muted = muted
        self._apply_mute_style()
        self.icon_btn.set_label(icon_for(volume, muted))
        if not self.dragging:
            self.scale.set_value(volume)
            self.pct_lbl.set_text(f"{volume}%")


class VolumeMixer(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_default_size(320, -1)
        self.set_resizable(False)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 36)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 8)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.set_name("mixer")
        outer.set_border_width(10)
        self.add(outer)

        vol, muted = get_master()
        self.master_row = Row("Geral", vol, muted, set_master_volume, self._toggle_master_mute)
        outer.pack_start(self.master_row, False, False, 0)

        outer.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        self.apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        outer.pack_start(self.apps_box, False, False, 0)

        self.empty_lbl = Gtk.Label(label="Nenhum app tocando audio")
        self.empty_lbl.get_style_context().add_class("empty")
        self.apps_box.pack_start(self.empty_lbl, False, False, 4)

        self.app_rows = {}
        self.missing_ticks = {}

        self.connect("key-press-event", self._on_key)

        self._load_css()
        self.show_all()
        self._refresh_apps()
        GLib.timeout_add(REFRESH_MS, self._tick)

    def _toggle_master_mute(self):
        toggle_master_mute()
        vol, muted = get_master()
        self.master_row.refresh(vol, muted)

    def _load_css(self):
        css = b"""
        window { background-color: #000000; }
        #mixer label { color: #ffffff; font-family: "JetBrainsMono Nerd Font", sans-serif; font-size: 13px; }
        #row.muted label { color: #777777; }
        .icon-btn { color: #ffffff; font-size: 15px; min-width: 22px; }
        #row.muted .icon-btn { color: #777777; }
        .empty { color: #777777; font-style: italic; }
        scale { min-height: 22px; padding: 0; }
        scale trough { min-height: 6px; background-color: rgba(255,255,255,0.15); border-radius: 4px; }
        scale trough highlight { background-color: #ffffff; border-radius: 4px; }
        scale slider { min-width: 14px; min-height: 14px; background-color: #ffffff; border-radius: 8px; }
        scale slider:hover { background-color: #cccccc; }
        separator { background-color: rgba(255,255,255,0.15); }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self._close()
        return False

    def _close(self):
        Gtk.main_quit()

    def _refresh_apps(self):
        apps = get_sink_inputs()
        current_ids = {a["id"] for a in apps}

        # so remove uma linha depois de 2 leituras seguidas sem o app, pra
        # nao sumir a linha por causa de uma falha passageira do pactl
        for idx in list(self.app_rows):
            if idx in current_ids:
                self.missing_ticks.pop(idx, None)
                continue
            if self.app_rows[idx].dragging:
                continue
            misses = self.missing_ticks.get(idx, 0) + 1
            if misses >= 2:
                self.app_rows[idx].destroy()
                del self.app_rows[idx]
                self.missing_ticks.pop(idx, None)
            else:
                self.missing_ticks[idx] = misses

        for app in apps:
            idx = app["id"]
            if idx in self.app_rows:
                self.app_rows[idx].refresh(app["volume"], app["muted"])
            else:
                row = Row(
                    app["name"],
                    app["volume"],
                    app["muted"],
                    lambda v, i=idx: set_app_volume(i, v),
                    lambda i=idx: (toggle_app_mute(i), None)[1],
                )
                self.app_rows[idx] = row
                self.apps_box.pack_start(row, False, False, 0)
                row.show_all()

        self.empty_lbl.set_visible(len(self.app_rows) == 0)

    def _tick(self):
        vol, muted = get_master()
        self.master_row.refresh(vol, muted)
        self._refresh_apps()
        return True


if __name__ == "__main__":
    win = VolumeMixer()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
