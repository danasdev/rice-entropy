#!/usr/bin/env bash
# Comando único para quem JÁ tem Arch instalado (não precisa ter o git antes):
#   curl -fsSL https://raw.githubusercontent.com/danasdev/rice-entropy/main/bootstrap.sh | bash
set -euo pipefail

REPO_URL="https://github.com/danasdev/rice-entropy.git"
DEST="${RICE_DIR:-$HOME/rice-entropy}"

[ "$EUID" -ne 0 ] || { echo "Não rode como root. Rode como o seu usuário."; exit 1; }
command -v pacman >/dev/null || { echo "Só para Arch Linux."; exit 1; }

command -v git >/dev/null || sudo pacman -S --needed --noconfirm git base-devel

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --ff-only
else
  git clone --depth 1 "$REPO_URL" "$DEST"
fi

exec "$DEST/install.sh"
