#!/usr/bin/env bash
# Rodar DENTRO de uma sessão do Hyprland (o hyprpm precisa dela para saber a versão).
set -euo pipefail
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] || { echo "Rode isto dentro do Hyprland."; exit 1; }

say "hyprglass (efeito de vidro com refração)"
hyprpm update
yes | hyprpm add https://github.com/hyprnux/hyprglass || true
hyprpm enable hyprglass

say "Tema de ícones Entropy (gerado com a paleta do wallpaper)"
ENTROPY_ICON_STYLE=logo python3 "$HOME/.config/hypr/rice/painel/gen-icons.py" || true
gsettings set org.gnome.desktop.interface icon-theme 'Entropy' || true

say "Recarregando"
hyprpm reload -n || true
hyprctl reload || true

cat <<'EOF'

Pronto. Atalhos principais:
  Super+S           painel de controle
  Super+Espaço      menu de apps
  Super+M           minimizar (Super+Shift+M restaura)
Veja ~/.config/hypr/rice/binds.conf para todos.
EOF
