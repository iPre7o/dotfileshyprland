#!/usr/bin/env bash
# Script de instalação automatizada dos dotfiles Arch + Hyprland
# Execute como usuário normal (com sudo disponível), a partir do diretório dotfiles/

set -e

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="$HOME"

log() { echo -e "\033[1;32m[install]\033[0m $*"; }
warn() { echo -e "\033[1;33m[aviso]\033[0m $*"; }
err() { echo -e "\033[1;31m[erro]\033[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] && err "Não execute como root. Use um usuário normal com sudo."
[[ ! -d "$DOTFILES_DIR/.config/hypr" ]] && err "Execute a partir do diretório dotfiles/ (onde está o README.md)"

log "=== Dotfiles Arch + Hyprland ==="
log "Destino: $USER_HOME"
echo ""

# ─── 1. Pacotes oficiais ──────────────────────────────────────────────────────
log "Instalando pacotes do repositório oficial..."
sudo pacman -S --needed --noconfirm \
  hyprland hyprpaper waybar dunst kitty rofi fastfetch \
  grim slurp wl-clipboard cliphist \
  playerctl brightnessctl \
  pipewire pipewire-alsa pipewire-jack pipewire-pulse wireplumber \
  bluez bluez-utils networkmanager polkit-kde-agent \
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk \
  power-profiles-daemon sddm \
  noto-fonts noto-fonts-cjk noto-fonts-emoji ttf-jetbrains-mono-nerd \
  gtk-layer-shell python-gobject python-requests python-psutil \
  thunar gsimplecal qt5ct qt6ct kvantum \
  gst-plugin-pipewire adwaita-icon-theme

# ─── 2. AUR — sddm-theme-blackarch ───────────────────────────────────────────
log "Instalando tema do SDDM (AUR)..."
if command -v yay &>/dev/null; then
  yay -S --needed --noconfirm sddm-theme-blackarch
elif command -v paru &>/dev/null; then
  paru -S --needed --noconfirm sddm-theme-blackarch
else
  warn "Nenhum helper AUR encontrado (yay/paru). Instalando yay primeiro..."
  sudo pacman -S --needed --noconfirm git base-devel
  git clone https://aur.archlinux.org/yay.git /tmp/yay-install
  (cd /tmp/yay-install && makepkg -si --noconfirm)
  rm -rf /tmp/yay-install
  yay -S --needed --noconfirm sddm-theme-blackarch
fi

# ─── 3. Serviços do sistema ───────────────────────────────────────────────────
log "Ativando serviços do sistema..."
sudo systemctl enable --now NetworkManager
sudo systemctl enable --now bluetooth
sudo systemctl enable sddm
sudo systemctl enable --now power-profiles-daemon

log "Ativando serviços de áudio (PipeWire)..."
systemctl --user enable --now pipewire pipewire-pulse wireplumber

# ─── 4. SDDM — tema blackarch ─────────────────────────────────────────────────
log "Configurando tema do SDDM..."
sudo mkdir -p /etc/sddm.conf.d
sudo cp "$DOTFILES_DIR/sddm/theme.conf" /etc/sddm.conf.d/theme.conf

# ─── 5. Copiar dotfiles ───────────────────────────────────────────────────────
log "Copiando configurações..."
mkdir -p \
  "$USER_HOME/.config/hypr/config" \
  "$USER_HOME/.config/hypr/scripts" \
  "$USER_HOME/.config/hypr/assets" \
  "$USER_HOME/.config/waybar/scripts" \
  "$USER_HOME/.config/dunst" \
  "$USER_HOME/.config/kitty" \
  "$USER_HOME/.config/rofi" \
  "$USER_HOME/.config/fastfetch" \
  "$USER_HOME/Pictures/Screenshots"

cp -r "$DOTFILES_DIR/.config/hypr/"     "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/waybar/"   "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/dunst/"    "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/kitty/"    "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/rofi/"     "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/fastfetch/" "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/gtk-3.0/"  "$USER_HOME/.config/"
cp -r "$DOTFILES_DIR/.config/gtk-4.0/"  "$USER_HOME/.config/"

# Qt / Kvantum temas
[[ -d "$DOTFILES_DIR/.config/Kvantum" ]]  && cp -r "$DOTFILES_DIR/.config/Kvantum/"  "$USER_HOME/.config/"
[[ -d "$DOTFILES_DIR/.config/qt5ct" ]]    && cp -r "$DOTFILES_DIR/.config/qt5ct/"    "$USER_HOME/.config/"
[[ -d "$DOTFILES_DIR/.config/qt6ct" ]]    && cp -r "$DOTFILES_DIR/.config/qt6ct/"    "$USER_HOME/.config/"

# mimeapps e user-dirs
[[ -f "$DOTFILES_DIR/.config/mimeapps.list" ]]    && cp "$DOTFILES_DIR/.config/mimeapps.list"    "$USER_HOME/.config/"
[[ -f "$DOTFILES_DIR/.config/user-dirs.dirs" ]]   && cp "$DOTFILES_DIR/.config/user-dirs.dirs"   "$USER_HOME/.config/"
[[ -f "$DOTFILES_DIR/.config/user-dirs.locale" ]] && cp "$DOTFILES_DIR/.config/user-dirs.locale" "$USER_HOME/.config/"

# autostart
[[ -d "$DOTFILES_DIR/.config/autostart" ]] && cp -r "$DOTFILES_DIR/.config/autostart/" "$USER_HOME/.config/"

# Systemd user services (rclone + dbus-broker override)
if [[ -d "$DOTFILES_DIR/.config/systemd" ]]; then
  mkdir -p "$USER_HOME/.config/systemd/user/dbus-broker.service.d"
  cp -r "$DOTFILES_DIR/.config/systemd/" "$USER_HOME/.config/"
  systemctl --user daemon-reload
  log "Habilitando serviços rclone..."
  systemctl --user enable rclone-gdrive.service
  systemctl --user enable rclone-drives-compartilhados.service
  systemctl --user enable rclone-sync-drives-compartilhados.timer
  warn "rclone precisa ser configurado manualmente antes de iniciar os serviços."
  warn "Execute: rclone config  (crie o remote 'gdrive' do tipo 'drive')"
fi

# Scripts locais (~/.local/bin)
if [[ -d "$DOTFILES_DIR/.local/bin" ]]; then
  mkdir -p "$USER_HOME/.local/bin"
  cp -r "$DOTFILES_DIR/.local/bin/" "$USER_HOME/.local/"
  chmod +x "$USER_HOME/.local/bin/"* 2>/dev/null || true
fi

# Shell (zsh / bash)
[[ -f "$DOTFILES_DIR/.zshrc" ]]       && cp "$DOTFILES_DIR/.zshrc"       "$USER_HOME/.zshrc"
[[ -f "$DOTFILES_DIR/.bashrc" ]]      && cp "$DOTFILES_DIR/.bashrc"      "$USER_HOME/.bashrc"
[[ -f "$DOTFILES_DIR/.bash_profile" ]] && cp "$DOTFILES_DIR/.bash_profile" "$USER_HOME/.bash_profile"

# ─── 6. Tornar scripts executáveis ───────────────────────────────────────────
log "Ajustando permissões dos scripts..."
chmod +x "$USER_HOME/.config/hypr/scripts/"*.sh 2>/dev/null || true
chmod +x "$USER_HOME/.config/hypr/scripts/"*.py 2>/dev/null || true
chmod +x "$USER_HOME/.config/waybar/scripts/"*.sh 2>/dev/null || true
chmod +x "$USER_HOME/.config/waybar/scripts/"*.py 2>/dev/null || true

# ─── 7. Ajustar caminhos absolutos ───────────────────────────────────────────
log "Ajustando caminhos para $USER_HOME..."
ORIGINAL_HOME="/home/gabryel"
if [[ "$USER_HOME" != "$ORIGINAL_HOME" ]]; then
  find "$USER_HOME/.config/hypr" "$USER_HOME/.config/waybar" \
       -type f \( -name "*.lua" -o -name "*.py" -o -name "*.sh" -o -name "*.conf" \) \
       -exec sed -i "s|$ORIGINAL_HOME|$USER_HOME|g" {} +
  log "Caminhos atualizados de $ORIGINAL_HOME para $USER_HOME"
else
  log "Mesmo usuário (gabryel) — caminhos mantidos"
fi

# ─── 8. Obsidian Vault mínimo para o painel ──────────────────────────────────
if [[ ! -d "$USER_HOME/Obsidian Vault" ]]; then
  warn "Criando estrutura mínima do Obsidian Vault para o painel welcome.py..."
  mkdir -p "$USER_HOME/Obsidian Vault/00 INBOX"
  touch "$USER_HOME/Obsidian Vault/✅ Tarefas.md"
fi

# ─── 9. Verificar dependências Python ────────────────────────────────────────
log "Verificando dependências Python..."
python3 -c "
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell
import psutil, requests, dbus
print('Todas as dependências Python OK')
" 2>/dev/null || warn "Algumas dependências Python podem estar faltando. Veja INSTALL.md seção 8."

# ─── Fim ──────────────────────────────────────────────────────────────────────
echo ""
log "=== Instalação concluída! ==="
echo ""
echo "  Próximos passos:"
echo "  1. Revise ~/.config/hypr/hyprpaper.conf e ajuste o monitor (padrão: eDP-1)"
echo "  2. Revise ~/.config/hypr/config/monitors.lua se quiser resolução/escala fixas"
echo "  3. Reinicie e selecione Hyprland no SDDM"
echo ""
echo "  Para testar sem reiniciar: pressione Ctrl+Alt+F2 e execute: Hyprland"
echo "  Log do painel: ~/.cache/welcome.log"
echo ""
echo "  Serviços rclone (Google Drive):"
echo "  1. Configure: rclone config  (crie remote 'gdrive', tipo 'drive')"
echo "  2. Ative:     systemctl --user start rclone-gdrive.service"
echo "  3. Sync:      ~/.local/bin/rclone-sync-drives-compartilhados"
