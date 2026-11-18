#!/usr/bin/env python3
"""Separa uma imagem em camadas RGBA (fundo -> frente) para o ASCII em camadas.
uso: entropy-wall-layers.py imagem.png pasta_saida [modo]
modos: depth (usa o mapa de brilho/destaque; 2 camadas), magenta (frente = tons magenta/rosa, fundo = o resto),
       red (frente = vermelho/branco, meio = o resto claro, fundo = borrado e escurecido)
Gera camada0.png (fundo), camada1.png ... e imprime o manifest sugerido."""
import json, os, sys
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

src, out = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "depth"
os.makedirs(out, exist_ok=True)
W, H = 1920, 1080
im = Image.open(src).convert("RGB")
k = min(W / im.width, H / im.height) if mode == "red" else max(W / im.width, H / im.height)
canvas = Image.new("RGB", (W, H), (4, 4, 8))
big = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
canvas.paste(big, ((W - big.width) // 2, (H - big.height) // 2))
px = canvas.load()


def mask_from(fn):
    m = Image.new("L", (W, H), 0); mp = m.load()
    for y in range(H):
        for x in range(W):
            if fn(*px[x, y]):
                mp[x, y] = 255
    return m


def clean(m, grow=2, close=5):
    m = m.filter(ImageFilter.MaxFilter(close * 2 + 1)).filter(ImageFilter.MinFilter(close * 2 + 1))   # fecha buracos
    return m.filter(ImageFilter.GaussianBlur(grow)).point(lambda v: 255 if v > 110 else 0)


def fill_holes(img, hole, passes=14):
    """preenche o que a camada da frente cobriu com a cor vizinha (para o fundo não ficar com buraco)"""
    img = img.copy(); known = ImageOps.invert(hole)
    for _ in range(passes):
        grown = img.filter(ImageFilter.MaxFilter(5))
        img.paste(grown, mask=ImageOps.invert(known))
        known = known.filter(ImageFilter.MaxFilter(5))
    return img


def rgba(img, alpha):
    r, g, b = img.split(); return Image.merge("RGBA", (r, g, b, alpha))


layers = []
if mode == "magenta":
    near = clean(mask_from(lambda r, g, b: r > g + 28 and b > g + 18), 1, 2)
    far = fill_holes(canvas, near)
    layers = [rgba(far, Image.new("L", (W, H), 255)), rgba(canvas, near)]
    manifest = {"depths": [0.35, 1.0]}
elif mode == "red":
    near = clean(mask_from(lambda r, g, b: (r > b + 14 and r > 40) or (min(r, g, b) > 190)), 4, 14)
    mid = mask_from(lambda r, g, b: max(r, g, b) > 70 and not (r > b + 14))
    mid = ImageChops.subtract(mid, near)
    bg = ImageEnhance.Brightness(canvas.filter(ImageFilter.GaussianBlur(26))).enhance(0.8)
    layers = [rgba(bg, Image.new("L", (W, H), 255)), rgba(canvas, mid), rgba(canvas, near)]
    manifest = {"depths": [0.2, 0.6, 1.0]}
else:
    import subprocess
    d = os.path.join(out, "_d.png")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "entropy-wall-depth.py"), src, d], check=True)
    dm = Image.open(d).convert("L").resize((W, H))
    near = clean(dm.point(lambda v: 255 if v > 120 else 0), 3, 8)
    far = fill_holes(canvas, near)
    layers = [rgba(far, Image.new("L", (W, H), 255)), rgba(canvas, near)]
    manifest = {"depths": [0.3, 1.0]}
names = []
for i, l in enumerate(layers):
    n = f"camada{i}.png"; l.save(os.path.join(out, n)); names.append(n)
m = {"type": "shader", "shader": "ascii-camadas.frag", "channels": names, "atlas": {"chars": " .·:;+=*xX#%@", "cell": 48},
     "params": [8, 0.05, 0, 0.85], **manifest}
print(json.dumps(m))
