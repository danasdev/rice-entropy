#!/usr/bin/env bash
# Foca a janela do app que está tocando música (ou o primeiro player, se nenhum estiver tocando).
players=$(playerctl -l 2>/dev/null) || exit 0
nome=""
for p in $players; do
    [ "$(playerctl -p "$p" status 2>/dev/null)" = "Playing" ] && { nome=$p; break; }
done
[ -z "$nome" ] && nome=$(echo "$players" | head -n1)
[ -z "$nome" ] && exit 0
base=${nome%%.instance*}   # firefox.instance123 -> firefox
addr=$(hyprctl -j clients | python3 -c '
import json,sys
b=sys.argv[1].lower()
for c in json.load(sys.stdin):
    if b in c["class"].lower() or b in c["initialClass"].lower():
        print(c["address"]); break' "$base")
[ -n "$addr" ] && hyprctl dispatch focuswindow "address:$addr"
