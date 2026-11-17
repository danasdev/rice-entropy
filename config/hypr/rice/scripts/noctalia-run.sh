#!/usr/bin/env bash
# Mantém o Noctalia rodando: se ele fechar por erro, reinicia (com pausa para não entrar em loop).
pgrep -x noctalia >/dev/null && exit 0
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/noctalia/quedas.log"
mkdir -p "$(dirname "$LOG")"
falhas=0
while true; do
    inicio=$(date +%s)
    noctalia
    code=$?
    [[ $code -eq 0 ]] && exit 0            # saiu normalmente (ex.: logout)
    echo "$(date '+%F %T') noctalia saiu com código $code" >> "$LOG"
    (( $(date +%s) - inicio < 30 )) && falhas=$((falhas+1)) || falhas=0
    (( falhas >= 5 )) && { notify-send -u critical "Noctalia" "Caiu 5 vezes seguidas; veja $LOG"; exit 1; }
    sleep 2
done
