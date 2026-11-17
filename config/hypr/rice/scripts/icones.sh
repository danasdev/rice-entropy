#!/bin/bash
# Regenera o tema de ícones Entropy com a paleta atual e recarrega o dock
ENTROPY_ICON_STYLE=logo python3 "$HOME/.config/hypr/rice/painel/gen-icons.py" >/dev/null 2>&1
noctalia msg dock-reload >/dev/null 2>&1
