#!/usr/bin/env bash
# gravar.sh area|tela -> liga/desliga gravação (wf-recorder) em ~/Vídeos, com o áudio do sistema.
# Apertar o mesmo atalho de novo para a gravação e salva.
dir=~/Vídeos
estado="${XDG_RUNTIME_DIR:-/tmp}/gravar-tela.arq"

if pgrep -x wf-recorder >/dev/null; then
    pkill -INT -x wf-recorder
    notify-send -a Gravador -t 3000 "Gravação salva" "$(basename "$(cat "$estado" 2>/dev/null)") em Vídeos"
    exit 0
fi

command -v wf-recorder >/dev/null || {
    notify-send -a Gravador -u critical "wf-recorder não instalado" "sudo pacman -S wf-recorder"
    exit 1
}

mkdir -p "$dir"
arq="$dir/$(date +%F_%H-%M-%S).mp4"
if [ "$1" = "area" ]; then
    reg=$(slurp) || exit 0          # Esc cancela
    alvo=(-g "$reg")
else
    mon=$(hyprctl -j activeworkspace | python3 -c 'import json,sys;print(json.load(sys.stdin)["monitor"])')
    alvo=(-o "$mon")
fi

echo "$arq" > "$estado"
notify-send -a Gravador -t 1500 "Gravando" "Aperte o atalho de novo pra parar"
sleep 1.6   # espera a notificação sumir pra não aparecer no vídeo
exec wf-recorder "${alvo[@]}" --audio="$(pactl get-default-sink).monitor" -f "$arq"
