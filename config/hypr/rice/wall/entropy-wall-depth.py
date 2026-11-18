#!/usr/bin/env python3
"""Gera um mapa de profundidade (cinza: claro = perto) a partir de uma imagem, sem IA:
mistura brilho e "destaque" (distância da cor do fundo/bordas). Funciona bem para sujeito iluminado sobre fundo escuro.
Para cenas complexas, use um mapa melhor (ex.: Depth Anything) e passe como depth.png.
uso: entropy-wall-depth.py entrada.png saida.png"""
import sys
from PIL import Image, ImageFilter, ImageOps, ImageChops, ImageStat

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
w, h = im.size
small = im.resize((max(64, w // 4), max(64, h // 4)))
lum = ImageOps.autocontrast(small.convert("L").filter(ImageFilter.GaussianBlur(3)), cutoff=1)
# cor típica do fundo = mediana das bordas
px = small.load(); sw, sh = small.size
edge = [px[x, y] for x in range(0, sw, 3) for y in (0, sh - 1)] + [px[x, y] for y in range(0, sh, 3) for x in (0, sw - 1)]
bg = tuple(sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3))
diff = ImageChops.difference(small, Image.new("RGB", small.size, bg)).convert("L").filter(ImageFilter.GaussianBlur(6))
diff = ImageOps.autocontrast(diff, cutoff=2)
depth = ImageChops.add(lum.point(lambda v: int(v * 0.5)), diff.point(lambda v: int(v * 0.7)))
depth = ImageOps.autocontrast(depth, cutoff=1).filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.BICUBIC)
depth.save(dst)
