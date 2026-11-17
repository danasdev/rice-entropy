#!/usr/bin/env bash
# Instalador da rice Entropy (Arch Linux). Rode como usuário normal (usa sudo para os pacotes).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

[ "$EUID" -ne 0 ] || { echo "Não rode como root. Rode como o seu usuário."; exit 1; }
command -v pacman >/dev/null || { echo "Este instalador é só para Arch Linux."; exit 1; }

say "Pacotes oficiais"
grep -vE '^\s*(#|$)' "$REPO/packages/pacman.txt" | sudo pacman -S --needed --noconfirm -

say "Serviços"
sudo systemctl enable --now NetworkManager bluetooth power-profiles-daemon upower || true

say "Configurações (backup do que já existe)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BK="$HOME/.config-backup-rice-$STAMP"
mkdir -p "$HOME/.config"
for d in hypr kitty noctalia; do
  if [ -e "$HOME/.config/$d" ]; then
    mkdir -p "$BK"
    mv "$HOME/.config/$d" "$BK/$d"
    echo "backup: ~/.config/$d -> $BK/$d"
  fi
done
cp -r "$REPO/config/hypr" "$REPO/config/kitty" "$REPO/config/noctalia" "$HOME/.config/"

# o repositório guarda @HOME@ no lugar do caminho da pessoa
grep -rIl '@HOME@' "$HOME/.config/hypr" "$HOME/.config/noctalia" "$HOME/.config/kitty" 2>/dev/null \
  | xargs -r sed -i "s|@HOME@|$HOME|g"

chmod +x "$HOME/.config/hypr/rice/scripts/"* "$HOME/.config/hypr/rice/painel/"*-toggle \
         "$HOME/.config/hypr/rice/painel/"*.py 2>/dev/null || true

say "Papel de parede padrão"
mkdir -p "$HOME/Pictures/Wallpapers"
cp -n "$REPO/wallpapers/"* "$HOME/Pictures/Wallpapers/"

say "Pasta de usuário e nome na saudação do painel"
xdg-user-dirs-update || true
[ -f "$HOME/.config/entropy-name" ] || printf '%s\n' "$(getent passwd "$USER" | cut -d: -f5 | cut -d, -f1 | awk '{print $1}')" > "$HOME/.config/entropy-name"
[ -s "$HOME/.config/entropy-name" ] || printf '%s\n' "${USER^}" > "$HOME/.config/entropy-name"

cat <<EOF

Pronto. Falta o que precisa rodar DENTRO do Hyprland:
  1) Reinicie e entre no Hyprland (escolha "Hyprland" no login, ou rode 'Hyprland' no TTY).
  2) Abra um terminal (Super+Q) e rode:   $REPO/setup-plugins.sh
  3) Ajuste seus monitores em ~/.config/hypr/rice/monitors.conf (veja 'hyprctl monitors')
     e o nome dos monitores nos widgets de ~/.config/noctalia/config.toml (linhas 'output = ...').

Backup das suas configs antigas (se existiam): $BK
EOF
