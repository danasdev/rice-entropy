#!/usr/bin/env bash
# Instalador da rice Entropy (Arch Linux). Rode como usuário normal (usa sudo para os pacotes).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }

[ "$EUID" -ne 0 ] || { echo "Não rode como root. Rode como o seu usuário."; exit 1; }
command -v pacman >/dev/null || { echo "Este instalador é só para Arch Linux."; exit 1; }

say "Verificando o sudo"
if ! sudo -v; then
  echo "ERRO: seu usuário não consegue usar sudo. Entre como root e rode: usermod -aG wheel SEU_USUARIO"
  echo "e habilite o grupo wheel no sudoers (EDITOR=nano visudo, descomente a linha '%wheel ALL=(ALL:ALL) ALL')."
  exit 1
fi

say "Pacotes oficiais"
PKGS="$(grep -vE '^\s*(#|$)' "$REPO/packages/pacman.txt")"
sudo pacman -Sy --noconfirm >/dev/null 2>&1 || true
if ! printf '%s\n' "$PKGS" | sudo pacman -S --needed --noconfirm -; then
  echo "Instalação em lote falhou; tentando pacote por pacote para não travar a rice..."
  FAILED=()
  while read -r pkg; do
    sudo pacman -S --needed --noconfirm "$pkg" || FAILED+=("$pkg")
  done <<< "$PKGS"
  [ "${#FAILED[@]}" -eq 0 ] || echo "ATENÇÃO: não instalou: ${FAILED[*]}"
fi

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

say "Teclado"
echo "  1) ABNT2 (brasileiro, com Ç)   2) US internacional   3) US"
K=""
read -r -p "Escolha [1]: " K </dev/tty 2>/dev/null || K=""
case "${K:-1}" in
  2) KL=us; KV=intl;  KM="" ;;
  3) KL=us; KV="";    KM="" ;;
  *) KL=br; KV=abnt2; KM=abnt2 ;;
esac
sed -i "s/^ *kb_layout.*/    kb_layout = $KL/; s/^ *kb_variant.*/    kb_variant = $KV/; s/^ *kb_model.*/    kb_model = $KM/" "$HOME/.config/hypr/rice/input.conf"
echo "teclado: $KL ${KV:+($KV)}"

say "Monitores (para os widgets do Noctalia)"
MONS=()
for st in /sys/class/drm/card*-*/status; do
  [ -e "$st" ] || continue
  [ "$(cat "$st")" = connected ] && MONS+=("$(basename "$(dirname "$st")" | sed 's/^card[0-9]*-//')")
done
LAP=""; EXT=""
for m in "${MONS[@]:-}"; do [ -z "$LAP" ] && [[ "$m" == eDP* ]] && LAP="$m"; done
[ -n "$LAP" ] || LAP="${MONS[0]:-eDP-1}"
for m in "${MONS[@]:-}"; do [ "$m" != "$LAP" ] && [ -z "$EXT" ] && EXT="$m"; done
[ -n "$EXT" ] || EXT="HDMI-A-1"
sed -i "s/output = \"eDP-1\"/output = \"$LAP\"/; s/output = \"HDMI-A-1\"/output = \"$EXT\"/" "$HOME/.config/noctalia/config.toml"
echo "monitor principal: $LAP   secundário: $EXT"

say "Papel de parede padrão"
mkdir -p "$HOME/Pictures/Wallpapers"
cp -n "$REPO/wallpapers/"* "$HOME/Pictures/Wallpapers/"

say "Pasta de usuário e nome na saudação do painel"
xdg-user-dirs-update || true
[ -f "$HOME/.config/entropy-name" ] || printf '%s\n' "$(getent passwd "$USER" | cut -d: -f5 | cut -d, -f1 | awk '{print $1}')" > "$HOME/.config/entropy-name"
[ -s "$HOME/.config/entropy-name" ] || printf '%s\n' "${USER^}" > "$HOME/.config/entropy-name"

# o Hyprland dá prioridade a um hyprland.lua; se existir, ele ignora o hyprland.conf da rice
if [ -f "$HOME/.config/hypr/hyprland.lua" ]; then
  mv "$HOME/.config/hypr/hyprland.lua" "$HOME/.config/hypr/hyprland.lua.bak-rice"
  echo "aviso: havia um hyprland.lua (renomeado para hyprland.lua.bak-rice). Saia e entre de novo no Hyprland."
fi

if [ -f "$HOME/.config/hypr/rice/binds.conf" ]; then
  echo "OK: configuração da rice instalada em ~/.config/hypr"
else
  echo "ERRO: a configuração não foi copiada. Rode de novo: $REPO/install.sh 2>&1 | tee ~/install.log"
  exit 1
fi

cat <<EOF

Pronto. Falta o que precisa rodar DENTRO do Hyprland:
  1) Reinicie e entre no Hyprland (escolha "Hyprland" no login, ou rode 'Hyprland' no TTY).
  2) Abra um terminal (Super+Enter) e rode:   $REPO/setup-plugins.sh
  3) Se precisar de escala ou posição de monitores: ~/.config/hypr/rice/monitors.conf (veja 'hyprctl monitors').

Backup das suas configs antigas (se existiam): $BK
EOF
