#!/bin/bash
# Recarrega a paleta nos painéis Entropy (ilha, painel, menu de apps) depois de trocar o wallpaper
sleep 2
RT="${XDG_RUNTIME_DIR:-/tmp}"
D="$HOME/.config/hypr/rice/painel"
for s in entropy-cc entropy-launcher entropy-island; do
  [ "$(cat "$RT/$s.open" 2>/dev/null)" = "1" ] && exit 0   # algo aberto: não atrapalha
done
for s in entropy-island entropy-cc entropy-launcher; do
  for p in $(pgrep -x python3); do grep -qa "$s.py" /proc/$p/cmdline && kill "$p"; done
done
sleep 0.6
setsid python3 "$D/entropy-island.py" >/dev/null 2>&1 < /dev/null &
setsid python3 "$D/entropy-cc.py" --daemon >/dev/null 2>&1 < /dev/null &
setsid python3 "$D/entropy-launcher.py" --daemon >/dev/null 2>&1 < /dev/null &
