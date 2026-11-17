#!/usr/bin/env python3
"""Minimizar/restaurar janelas no Hyprland (gaveta escondida 'special:minimizadas').

  minimizar.py min      -> esconde a janela em foco
  minimizar.py restore  -> traz de volta a última minimizada para o workspace atual
  minimizar.py all      -> traz todas de volta
"""
import json, subprocess, sys, time

FADE = 0.2  # segundos de fade antes de esconder

GAVETA = "special:minimizadas"


def hj(*a):
    return json.loads(subprocess.run(["hyprctl", "-j", *a], capture_output=True, text=True).stdout or "null")


def d(*cmds):
    subprocess.run(["hyprctl", "--batch", " ; ".join("dispatch " + c for c in cmds)], capture_output=True)


def minimizadas():
    # mais recente primeiro (focusHistoryID menor = usada mais recentemente)
    cl = [c for c in hj("clients") if c["workspace"]["name"] == GAVETA]
    return sorted(cl, key=lambda c: c["focusHistoryID"])


def main(acao):
    if acao == "min":
        w = hj("activewindow")
        if w and w.get("address") and w["workspace"]["name"] != GAVETA:
            a = w["address"]
            d(f"setprop address:{a} opacity 0")
            time.sleep(FADE)
            d(f"movetoworkspacesilent {GAVETA},address:{a}", f"setprop address:{a} opacity 1")
    elif acao in ("restore", "all"):
        ws = hj("activeworkspace")["id"]
        alvo = minimizadas()
        for c in (alvo if acao == "all" else alvo[:1]):
            a = c["address"]
            d(f"setprop address:{a} opacity 0", f"movetoworkspace {ws},address:{a}", f"focuswindow address:{a}")
            time.sleep(0.04)
            d(f"setprop address:{a} opacity 1")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "min")
