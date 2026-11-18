#!/usr/bin/env python3
"""Gera spiderman.png (RGBA): cor do desenho + profundidade no canal alfa (herói à frente, teias ao fundo)."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter
OUT = sys.argv[1] if len(sys.argv) > 1 else "spiderman.png"
S = 2; W, H = 1600 * S, 900 * S
col = Image.new("RGBA", (W, H), (6, 8, 20, 255)); dep = Image.new("L", (W, H), 0)
dc, dd = ImageDraw.Draw(col), ImageDraw.Draw(dep)
F = 1.2; CX, CY = 760, 470


def T(x, y): return (CX + (x - 790) * F, CY + (y - 480) * F)
def P(x, y): return (x * S, y * S)
def PT(x, y): return P(*T(x, y))


def cap(a, b, w0, w1, color, depth, steps=60):
    a, b = T(*a), T(*b)
    for i in range(steps + 1):
        t = i / steps; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t; r = (w0 + (w1 - w0) * t) * F / 2
        box = [(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S]; dc.ellipse(box, fill=color); dd.ellipse(box, fill=depth)


def web(cx, cy, R, rays, rings, rot=0.0):
    for k in range(rays):
        a = rot + k * 2 * math.pi / rays
        dc.line([P(cx, cy), P(cx + R * math.cos(a), cy + R * math.sin(a))], fill=(120, 135, 170, 255), width=3 * S)
        dd.line([P(cx, cy), P(cx + R * math.cos(a), cy + R * math.sin(a))], fill=70, width=3 * S)
    for r in range(1, rings + 1):
        rr = R * r / rings
        pts = [P(cx + rr * math.cos(rot + k * 2 * math.pi / rays) * 0.98, cy + rr * math.sin(rot + k * 2 * math.pi / rays) * 0.98) for k in range(rays + 1)]
        dc.line(pts, fill=(95, 110, 150, 255), width=2 * S); dd.line(pts, fill=55, width=2 * S)


web(1380, 120, 520, 12, 7, 0.2); web(130, 820, 430, 11, 6, 0.5)
RED = (215, 22, 40, 255); BLU = (28, 52, 185, 255); DK = (10, 10, 18, 255); FD = 255
hand = T(985, 232)
dc.line([P(*hand), P(1560, -30)], fill=(215, 225, 240, 255), width=4 * S); dd.line([P(*hand), P(1560, -30)], fill=150, width=4 * S)
cap((785, 520), (860, 615), 52, 40, BLU, FD); cap((860, 615), (805, 730), 40, 30, RED, FD)
cap((770, 520), (700, 605), 52, 40, BLU, FD); cap((700, 605), (635, 700), 40, 28, RED, FD)
tor = [PT(715, 352), PT(825, 372), PT(812, 520), PT(752, 528)]
dc.polygon(tor, fill=RED); dd.polygon(tor, fill=FD)
dc.polygon([PT(745, 430), PT(805, 438), PT(812, 520), PT(752, 528)], fill=BLU)
cap((818, 368), (905, 300), 40, 32, RED, FD); cap((905, 300), (985, 232), 32, 26, BLU, FD)
cap((722, 360), (662, 425), 40, 32, RED, FD); cap((662, 425), (700, 478), 32, 26, BLU, FD)
box = [PT(716, 252), PT(806, 360)]; dc.ellipse(box, fill=RED); dd.ellipse(box, fill=FD)
dc.polygon([PT(727, 308), PT(757, 318), PT(745, 334), PT(724, 326)], fill=(245, 245, 250, 255))
dc.polygon([PT(795, 308), PT(765, 318), PT(777, 334), PT(798, 326)], fill=(245, 245, 250, 255))
lw = max(1, int(2 * F * S))
for a, b in (((760, 262), (760, 360)), ((722, 300), (802, 300)), ((724, 330), (800, 330)), ((742, 255), (730, 355)), ((780, 255), (792, 355))):
    dc.line([PT(*a), PT(*b)], fill=DK, width=lw)
for y in (385, 420, 455, 490):
    dc.line([PT(722, y), PT(818, y + 8)], fill=DK, width=lw)
dc.line([PT(768, 372), PT(780, 520)], fill=DK, width=lw)
cx_, cy_ = T(768, 405); rr = 11 * F
dc.ellipse([(cx_ - rr * 0.8) * S, (cy_ - rr * 1.2) * S, (cx_ + rr * 0.8) * S, (cy_ + rr * 1.2) * S], fill=DK)
for dx, dy in ((-26, -14), (-30, 2), (-26, 18), (26, -14), (30, 2), (26, 18)):
    dc.line([P(cx_, cy_), P(cx_ + dx * F, cy_ + dy * F)], fill=DK, width=lw)
col = col.resize((1600, 900), Image.LANCZOS); dep = dep.resize((1600, 900), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
r, g, b, _ = col.split(); im = Image.merge("RGBA", (r, g, b, dep))
fig = dep.point(lambda v: 255 if v >= 200 else 0)          # teias mais grossas (leem melhor em ASCII); o herói fica intacto
thick = im.filter(ImageFilter.MaxFilter(7)); thick.paste(im, mask=fig); thick.save(OUT)
