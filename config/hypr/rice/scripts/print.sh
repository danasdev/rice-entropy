#!/usr/bin/env bash
# print.sh area|tela -> salva em ~/Pictures/Screenshots, copia pro clipboard,
# toca o som de obturador e mostra notificação com miniatura.
dir=~/Pictures/Screenshots
mkdir -p "$dir"
arq="$dir/$(date +%F_%H-%M-%S).png"
if [ "$1" = "area" ]; then
    reg=$(slurp) || exit 0          # Esc cancela
    grim -g "$reg" "$arq" || exit 1
else
    grim "$arq" || exit 1
fi
wl-copy < "$arq"
paplay /usr/share/sounds/freedesktop/stereo/screen-capture.oga &
notify-send -a Print -i "$arq" -t 3000 "Print salvo" "Copiado e salvo em Screenshots"
