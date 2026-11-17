#!/bin/bash
# Carrega os plugins do Hyprland na ordem certa: o hyprpm descarrega o que não é dele, então o WindowShade vem depois.
for i in 1 2 3 4 5 6; do hyprctl version >/dev/null 2>&1 && break; sleep 1; done
hyprpm reload -n
sleep 1
[ -f @HOME@/.local/share/hyprland/plugins/HyprWindowShade.so ] && ! hyprctl plugin list | grep -q 'HyprWindowShade' && hyprctl plugin load @HOME@/.local/share/hyprland/plugins/HyprWindowShade.so
