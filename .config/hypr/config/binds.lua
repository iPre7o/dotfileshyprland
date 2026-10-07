local mainMod = "SUPER" -- Define a tecla "Windows" como modificador principal
-- fecha a janela; o Spotify em vez de fechar vai pro fundo e continua tocando
local CLOSE_WINDOW = "/home/gabryel/.config/hypr/scripts/close-window.sh"

-- ATALHOS (não dependem de plugin)
hl.bind("ALT + Tab", hl.dsp.exec_cmd(WINDOW_SWITCHER))
hl.bind("CONTROL + SHIFT + Escape", hl.dsp.exec_cmd("kitty --class floating_btop -e btop"))
hl.bind(mainMod .. " + R", hl.dsp.exec_cmd(TERMINAL))
hl.bind("ALT + F4", hl.dsp.exec_cmd(CLOSE_WINDOW))
hl.bind(mainMod .. " + Return", hl.dsp.exec_cmd(CLOSE_WINDOW))
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd(
  "command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"
))
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(FILE_MANAGER))
hl.bind(mainMod .. " + SHIFT + V", hl.dsp.window.float({ action = "toggle" }))
-- histórico da área de transferência (cliphist); o mesmo menu abre pelo ícone na waybar
hl.bind(mainMod .. " + V", hl.dsp.exec_cmd("/home/gabryel/.config/waybar/scripts/clipboard-menu.sh"))
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(MENU))
hl.bind(mainMod .. " + P", hl.dsp.window.pseudo())
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit")) -- dwindle

-- MOVIMENTACAO DE JANELAS
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

hl.bind(mainMod .. " + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))

hl.bind("SUPER + ALT + left",  hl.dsp.window.move({ direction = "left" }))
hl.bind("SUPER + ALT + right", hl.dsp.window.move({ direction = "right" }))
hl.bind("SUPER + ALT + up",    hl.dsp.window.move({ direction = "up" }))
hl.bind("SUPER + ALT + down",  hl.dsp.window.move({ direction = "down" }))

hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- WORKSPACES
for i = 1, 10 do
  local key = i % 10 -- 10 mapeia para a tecla 0
  hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
  hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))

-- Teclas multimídia (volume e brilho) — direto via wpctl/brightnessctl, sem OSD (mostrado na waybar)
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true, repeating = true })
hl.bind("XF86AudioMicMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%+"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl -e4 -n2 set 5%-"), { locked = true, repeating = true })

-- Requer playerctl
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })

-- CAPTURA DE TELA
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.exec_cmd("grim -g \"$(slurp)\" - | wl-copy"))
hl.bind("PRINT", hl.dsp.exec_cmd("grim ~/Pictures/Screenshots/$(date +'%Y-%m-%d_%H-%M-%S').png"))
hl.bind(mainMod .. " + PRINT", hl.dsp.exec_cmd("grim - | wl-copy"))
