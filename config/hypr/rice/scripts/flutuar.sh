#!/usr/bin/env bash
# SUPER+V: alterna flutuante. Ao flutuar, a janela encolhe (70% da tela) e centraliza,
# assim ela fica visivelmente sobreposta as outras e dá pra arrastar com SUPER+mouse.
if [ "$(hyprctl -j activewindow | python3 -c 'import json,sys;print(json.load(sys.stdin).get("floating",False))')" = "True" ]; then
    hyprctl dispatch settiled
else
    hyprctl --batch "dispatch setfloating ; dispatch resizeactive exact 70% 70% ; dispatch centerwindow"
fi
