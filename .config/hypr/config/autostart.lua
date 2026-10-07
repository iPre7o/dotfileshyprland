-- See https://wiki.hypr.land/Configuring/Basics/Autostart/

hl.on("hyprland.start", function ()
  hl.exec_cmd("waybar")
  hl.exec_cmd("hyprpaper")
  -- erros do welcome vão pro ~/.cache/welcome.log (o da sessão anterior fica em welcome.log.old)
  hl.exec_cmd("sh -c 'mv -f $HOME/.cache/welcome.log $HOME/.cache/welcome.log.old 2>/dev/null; exec python3 -X faulthandler /home/gabryel/.config/hypr/scripts/welcome.py >$HOME/.cache/welcome.log 2>&1'")
  hl.exec_cmd("python3 /home/gabryel/.config/waybar/scripts/ws-daemon.py")
  -- guarda tudo que for copiado (texto e imagem) pro histórico do SUPER+V
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
  hl.exec_cmd("wl-paste --type image --watch cliphist store")
end)
