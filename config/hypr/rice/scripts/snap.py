#!/usr/bin/env python3
"""Encaixe de janelas usando o mosaico do Hyprland (as janelas dividem a tela
e se ajustam juntas ao redimensionar).

Teclado (SUPER+setas):
  esquerda/direita -> leva a janela para aquele lado (troca com a vizinha;
                      na borda, passa para o outro monitor)
  cima             -> se tem janela acima, troca com ela; senão maximiza
  baixo            -> maximizada: volta; senão leva a janela para baixo
Mouse:
  snap.py drop     -> ao soltar SUPER+arrastar: na borda esquerda/direita a janela
                      vai para aquele lado do mosaico; no topo, maximiza
"""
import json
import subprocess
import sys

EDGE = 24  # distância (px) da borda que conta como "soltou na borda"


def hj(*args):
    out = subprocess.run(["hyprctl", "-j", *args], capture_output=True, text=True).stdout
    return json.loads(out or "null")


def batch(*cmds):
    subprocess.run(["hyprctl", "--batch", " ; ".join(cmds)], capture_output=True)


def tile(win):
    """Garante que a janela está no mosaico (desfaz flutuante/maximizado)."""
    cmds = [f"dispatch focuswindow address:{win['address']}"]
    if win.get("fullscreen", 0):
        cmds.append("dispatch fullscreen 1")
    if win["floating"]:
        cmds.append(f"dispatch settiled address:{win['address']}")
    batch(*cmds)


def vizinha(win, direcao):
    """Existe outra janela do mesmo workspace naquela direção?"""
    x, y = win["at"]; w, h = win["size"]
    for c in hj("clients") or []:
        if c["address"] == win["address"] or c["workspace"]["id"] != win["workspace"]["id"] or c["floating"]:
            continue
        cx, cy = c["at"]; cw, ch = c["size"]
        if direcao == "u" and cy + ch <= y + 2 and cx < x + w and cx + cw > x:
            return True
        if direcao == "d" and cy >= y + h - 2 and cx < x + w and cx + cw > x:
            return True
    return False


def key(direcao):
    win = hj("activewindow")
    if not win or not win.get("address"):
        return
    if direcao in ("left", "right"):
        tile(win)
        batch(f"dispatch movewindow {direcao[0]}")
    elif direcao == "up":
        if not win.get("fullscreen", 0) and not win["floating"] and vizinha(win, "u"):
            batch("dispatch movewindow u")
        elif not win.get("fullscreen", 0):
            if win["floating"]:
                tile(win)
            batch("dispatch fullscreen 1")
    elif direcao == "down":
        if win.get("fullscreen", 0) or win["floating"]:
            tile(win)
        elif vizinha(win, "d"):
            batch("dispatch movewindow d")


def drop():
    win = hj("activewindow")
    if not win or not win.get("address"):
        return
    cur = hj("cursorpos")
    cx, cy = cur["x"], cur["y"]
    for m in hj("monitors"):
        w, h = m["width"] / m["scale"], m["height"] / m["scale"]
        if m["x"] <= cx < m["x"] + w and m["y"] <= cy < m["y"] + h:
            lx, ly = cx - m["x"], cy - m["y"]
            if ly <= m["reserved"][1] + EDGE:
                tile(win); batch("dispatch fullscreen 1")
            elif lx <= EDGE:
                tile(win); batch("dispatch movewindow l")
            elif lx >= w - EDGE:
                tile(win); batch("dispatch movewindow r")
            return


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "drop":
        drop()
    elif arg in ("left", "right", "up", "down"):
        key(arg)
    else:
        print(__doc__)
