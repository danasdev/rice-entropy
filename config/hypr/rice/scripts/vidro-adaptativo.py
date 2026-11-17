#!/usr/bin/env python3
"""Vidro adaptativo: mede o brilho do wallpaper e escurece o vidro quando ele é claro.

Ajusta (1) o blur do Hyprland (afeta o Claude e outros), (2) o brilho do hyprglass (kitty)
e (3) a opacidade do vidro dentro do Claude (arquivo lido pelo patch do app).
Uso: vidro-adaptativo.py [--lum 0..1]   (--lum força um brilho, para testar)
"""
import os, subprocess, sys

CONF = os.path.expanduser("~/.config/hypr/rice/glass-adaptive.conf")
ALPHA = os.path.expanduser("~/.cache/glass-adaptive/alpha")
OUTPUT = "eDP-1"


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def brilho_wallpaper():
    wp = run("noctalia", "msg", "wallpaper-get", OUTPUT)
    if not wp or not os.path.exists(wp):
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wp, "-vf", "scale=1:1,format=gray",
                          "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True).stdout
    return raw[0] / 255 if raw else None


def lerp(a, b, t):
    return a + (b - a) * t


def main():
    if "--lum" in sys.argv:
        lum = float(sys.argv[sys.argv.index("--lum") + 1])
    else:
        lum = brilho_wallpaper()
        if lum is None:
            return
    t = max(0.0, min(1.0, (lum - 0.40) / 0.40))          # 0 = escuro, 1 = bem claro
    blur_bri = lerp(0.90, 0.40, t)
    blur_con = lerp(1.00, 1.25, t)
    glass_bri = lerp(1.50, 0.75, t)
    alpha = lerp(0.38, 0.68, t)

    conf = (f"# gerado por vidro-adaptativo.py (brilho do wallpaper = {lum:.2f})\n"
            f"decoration:blur:brightness = {blur_bri:.2f}\n"
            f"decoration:blur:contrast = {blur_con:.2f}\n"
            f"plugin:hyprglass:dark:brightness = {glass_bri:.2f}\n")
    open(CONF, "w").write(conf)
    for linha in conf.splitlines()[1:]:
        k, v = [x.strip() for x in linha.split("=")]
        run("hyprctl", "keyword", k, v)
    os.makedirs(os.path.dirname(ALPHA), exist_ok=True)
    open(ALPHA, "w").write(f"{alpha:.2f}")
    print(f"brilho={lum:.2f} blur_bri={blur_bri:.2f} glass_bri={glass_bri:.2f} alpha={alpha:.2f}")


if __name__ == "__main__":
    main()
