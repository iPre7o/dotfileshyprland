# Guia de instalação — dotfiles Arch + Hyprland

Guia completo com cada comando individualmente, para reinstalar após uma formatação.

---

## 1. Pré-requisitos — sistema base Arch Linux

Assumindo Arch Linux já instalado com internet e usuário normal com sudo.

---

## 2. Pacotes do repositório oficial

```bash
sudo pacman -S --needed \
  hyprland \
  hyprpaper \
  waybar \
  dunst \
  kitty \
  rofi \
  fastfetch \
  grim \
  slurp \
  wl-clipboard \
  cliphist \
  playerctl \
  brightnessctl \
  pipewire \
  pipewire-alsa \
  pipewire-jack \
  pipewire-pulse \
  wireplumber \
  bluez \
  bluez-utils \
  networkmanager \
  polkit-kde-agent \
  xdg-desktop-portal-hyprland \
  xdg-desktop-portal-gtk \
  power-profiles-daemon \
  sddm \
  noto-fonts \
  noto-fonts-cjk \
  noto-fonts-emoji \
  ttf-jetbrains-mono-nerd \
  gtk-layer-shell \
  python-gobject \
  python-requests \
  python-psutil \
  thunar \
  gsimplecal \
  qt5ct \
  qt6ct \
  kvantum \
  gst-plugin-pipewire
```

---

## 3. Pacotes AUR

Precisas de um helper AUR como `yay` ou `paru`. Exemplo com `yay`:

```bash
# Instalar yay (caso não tenha)
sudo pacman -S --needed git base-devel
git clone https://aur.archlinux.org/yay.git /tmp/yay
cd /tmp/yay && makepkg -si

# Tema do SDDM
yay -S sddm-theme-blackarch

# Opcional: Vesktop (Discord alternativo), Obsidian, etc.
# yay -S vesktop-bin obsidian
```

---

## 4. Ativar serviços do sistema

```bash
# NetworkManager
sudo systemctl enable --now NetworkManager

# Bluetooth
sudo systemctl enable --now bluetooth

# SDDM (login manager)
sudo systemctl enable sddm

# PipeWire (audio) — como usuário normal
systemctl --user enable --now pipewire pipewire-pulse wireplumber

# Power profiles
sudo systemctl enable --now power-profiles-daemon
```

---

## 5. Configurar o tema do SDDM

```bash
sudo mkdir -p /etc/sddm.conf.d
sudo cp sddm/theme.conf /etc/sddm.conf.d/theme.conf
```

Conteúdo do `theme.conf`:
```ini
[Theme]
Current=blackarch
```

---

## 6. Copiar os dotfiles

```bash
# Criar diretórios necessários
mkdir -p ~/.config/hypr/config
mkdir -p ~/.config/hypr/scripts
mkdir -p ~/.config/hypr/assets
mkdir -p ~/.config/waybar/scripts
mkdir -p ~/.config/dunst
mkdir -p ~/.config/kitty
mkdir -p ~/.config/rofi
mkdir -p ~/.config/fastfetch
mkdir -p ~/Pictures/Screenshots

# Copiar configurações
cp -r .config/hypr/ ~/.config/
cp -r .config/waybar/ ~/.config/
cp -r .config/dunst/ ~/.config/
cp -r .config/kitty/ ~/.config/
cp -r .config/rofi/ ~/.config/
cp -r .config/fastfetch/ ~/.config/
```

---

## 7. Tornar scripts executáveis

```bash
chmod +x ~/.config/hypr/scripts/*.sh
chmod +x ~/.config/hypr/scripts/*.py
chmod +x ~/.config/waybar/scripts/*.sh
chmod +x ~/.config/waybar/scripts/*.py
```

---

## 8. Dependências Python do welcome.py

O painel `welcome.py` usa GTK3 via `gi` (python-gobject) e gtk-layer-shell:

```bash
# Verificar se as dependências estão disponíveis
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK ok')"
python3 -c "import gi; gi.require_version('GtkLayerShell', '0.1'); from gi.repository import GtkLayerShell; print('layer-shell ok')"
python3 -c "import psutil; print('psutil ok')"
python3 -c "import requests; print('requests ok')"
```

Se algum falhar, instale via pacman:
```bash
sudo pacman -S python-gobject gtk-layer-shell python-psutil python-requests
```

---

## 9. Ajustar caminhos no autostart.lua

O arquivo `~/.config/hypr/config/autostart.lua` contém caminhos absolutos. Edite para o seu usuário:

```bash
sed -i 's|/home/gabryel|'"$HOME"'|g' ~/.config/hypr/config/autostart.lua
sed -i 's|/home/gabryel|'"$HOME"'|g' ~/.config/hypr/config/variables.lua
sed -i 's|/home/gabryel|'"$HOME"'|g' ~/.config/hypr/hyprpaper.conf
sed -i 's|/home/gabryel|'"$HOME"'|g' ~/.config/waybar/scripts/*.sh
sed -i 's|/home/gabryel|'"$HOME"'|g' ~/.config/waybar/scripts/*.py
```

---

## 10. Ajustar o wallpaper no hyprpaper.conf

```bash
# Editar o monitor no hyprpaper.conf se necessário
# Por padrão está configurado para eDP-1 (laptop)
# Para desktop com HDMI: trocar eDP-1 por HDMI-A-1
nano ~/.config/hypr/hyprpaper.conf
```

---

## 11. Testar individualmente antes de reiniciar

### Testar Hyprland sem reiniciar
```bash
# A partir de um TTY (Ctrl+Alt+F2), como usuário normal:
Hyprland
```

### Testar waybar
```bash
waybar &
```

### Testar dunst
```bash
dunst &
notify-send "Teste" "Notificação funcionando"
```

### Testar welcome.py
```bash
python3 ~/.config/hypr/scripts/welcome.py
# Log de erros:
tail -f ~/.cache/welcome.log
```

### Testar hyprpaper
```bash
hyprpaper &
```

---

## 12. Recarregar configurações sem reiniciar

```bash
# Recarregar Hyprland
hyprctl reload

# Recarregar Waybar
pkill -SIGUSR2 -x waybar

# Reiniciar painel welcome.py
pkill -f 'python3 -X faulthandler .*[w]elcome'
setsid -f sh -c 'python3 -X faulthandler ~/.config/hypr/scripts/welcome.py >>~/.cache/welcome.log 2>&1'

# Reiniciar dunst
pkill dunst && dunst &
```

---

## 13. Obsidian Vault (para o painel de tarefas)

O `welcome.py` lê tarefas de `~/Obsidian Vault/✅ Tarefas.md`. Se não usar Obsidian, o painel simplesmente não mostrará tarefas.

```bash
# Criar estrutura mínima para o painel funcionar
mkdir -p ~/Obsidian\ Vault
touch ~/Obsidian\ Vault/✅\ Tarefas.md
```

---

## 14. Configurar GTK e ícones

```bash
# Copiar configs do GTK
cp -r .config/gtk-3.0/ ~/.config/
cp -r .config/gtk-4.0/ ~/.config/

# Instalar tema de ícones Adwaita (geralmente já incluído no GNOME/GTK)
sudo pacman -S adwaita-icon-theme
```

---

## 15. Shell — zsh

```bash
# Instalar zsh e plugins
sudo pacman -S zsh zsh-autosuggestions zsh-syntax-highlighting

# Definir como shell padrão
chsh -s $(which zsh)

# Copiar configs
cp .zshrc ~/.zshrc
cp .bashrc ~/.bashrc
cp .bash_profile ~/.bash_profile
```

---

## 16. Temas Qt (Kvantum, qt5ct, qt6ct)

```bash
sudo pacman -S kvantum qt5ct qt6ct

cp -r .config/Kvantum/ ~/.config/
cp -r .config/qt5ct/   ~/.config/
cp -r .config/qt6ct/   ~/.config/
```

> Configura a aparência de apps Qt para usar o estilo Fusion com paleta preto e branco.

---

## 17. Associações de arquivos e pastas XDG

```bash
cp .config/mimeapps.list    ~/.config/
cp .config/user-dirs.dirs   ~/.config/
cp .config/user-dirs.locale ~/.config/

# Criar as pastas esperadas
xdg-user-dirs-update
mkdir -p ~/Imagens/Screenshots
```

---

## 18. Scripts locais (~/.local/bin)

```bash
mkdir -p ~/.local/bin
cp -r .local/bin/ ~/.local/
chmod +x ~/.local/bin/*
```

Scripts incluídos:
- `rclone-sync-drives-compartilhados` — sincroniza lista de Google Drives compartilhados
- `dbus-watch.sh` — monitora fds do dbus-broker (diagnóstico)

---

## 19. Serviços systemd do usuário (rclone)

```bash
mkdir -p ~/.config/systemd/user/dbus-broker.service.d
cp -r .config/systemd/ ~/.config/
systemctl --user daemon-reload

# Aumento do limite de file descriptors do dbus (evita crash por "Too many open files")
# (já incluído em .config/systemd/user/dbus-broker.service.d/limits.conf)

# Habilitar serviços rclone
systemctl --user enable rclone-gdrive.service
systemctl --user enable rclone-drives-compartilhados.service
systemctl --user enable rclone-sync-drives-compartilhados.timer
```

> **Atenção:** Os serviços rclone só funcionam após configurar o remote `gdrive`. Veja seção 20.

---

## 20. Configurar rclone (Google Drive)

```bash
# Instalar rclone
sudo pacman -S rclone fuse3

# Criar remotes interativamente
rclone config
# → Criar remote chamado 'gdrive' do tipo 'drive' (Google Drive)
# → Autenticar via OAuth no navegador

# Testar montagem manual
rclone mount gdrive: ~/GoogleDrive --vfs-cache-mode full &

# Após autenticado, iniciar serviços automáticos
systemctl --user start rclone-gdrive.service

# Sincronizar lista de drives compartilhados
~/.local/bin/rclone-sync-drives-compartilhados
systemctl --user start rclone-drives-compartilhados.service
```

---

## 21. Autostart (nm-applet)

```bash
cp -r .config/autostart/ ~/.config/
# nm-applet inicia automaticamente via Hyprland e aparece na bandeja do waybar
```

---

## Ordem recomendada após instalação limpa

1. Instalar pacotes oficiais (seção 2)
2. Instalar AUR + helper (seção 3)
3. Instalar zsh e definir como shell padrão (seção 15)
4. Ativar serviços do sistema (seção 4)
5. Configurar tema do SDDM (seção 5)
6. Copiar dotfiles principais (seção 6)
7. Copiar Qt/Kvantum (seção 16)
8. Copiar shell configs (seção 15)
9. Copiar mimeapps e user-dirs (seção 17)
10. Copiar local bin scripts (seção 18)
11. Copiar serviços systemd (seção 19)
12. Tornar scripts executáveis (seção 7)
13. Ajustar caminhos para seu usuário (seção 9)
14. Configurar rclone (seção 20) — opcional, para Google Drive
15. Criar Obsidian Vault mínimo (seção 13)
16. Testar componentes individualmente (seção 11)
17. Reiniciar → logar via SDDM → Hyprland inicia automaticamente
