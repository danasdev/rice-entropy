#!/usr/bin/env bash
# Alterna entre o workspace atual e um workspace vazio ("mostrar área de trabalho").
state="${XDG_RUNTIME_DIR:-/tmp}/hypr-show-desktop"
cur=$(hyprctl activeworkspace -j | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["id"],d["windows"])')
id=${cur% *}; wins=${cur#* }

if [ -f "$state" ] && [ "$wins" = 0 ]; then
    hyprctl dispatch workspace "$(cat "$state")" >/dev/null
    rm -f "$state"
else
    echo "$id" > "$state"
    hyprctl dispatch workspace empty >/dev/null
fi
