#!/usr/bin/env python3
"""Gera o tema de ícones 'Entropy': quadrado arredondado em vidro + símbolo de linha simples, nas cores da paleta do Noctalia."""
import importlib.util, math, os, re, shutil, subprocess, sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("entropy_cc", os.path.join(HERE, "entropy-cc.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
PAL = cc.PAL

OUT = os.path.expanduser("~/.local/share/icons/Entropy")
APPS = os.path.join(OUT, "scalable", "apps")

# glifos desenhados em grade 24x24, só traço (linha), pontas redondas
GL = {
    "terminal": '<path d="M4 17l6-5-6-5"/><path d="M12 19h8"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c3 3 3 15 0 18"/><path d="M12 3c-3 3-3 15 0 18"/>',
    "chromium": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M12 8.5h8"/><path d="M7.4 14.2L3.6 7.6"/><path d="M12 20.9l4-6.9"/>',
    "music": '<path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
    "spark": '<path d="M12 3v18"/><path d="M3 12h18"/><path d="M5.6 5.6l12.8 12.8"/><path d="M18.4 5.6L5.6 18.4"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    "hex": '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><path d="M12 8l3.5 2v4L12 16l-3.5-2v-4z"/>',
    "code": '<path d="M8 8l-5 4 5 4"/><path d="M16 8l5 4-5 4"/><path d="M13.5 5l-3 14"/>',
    "cube": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5"/><path d="M12 12L4 7.5"/><path d="M12 12v9"/>',
    "gamepad": '<rect x="3" y="7" width="18" height="11" rx="5.5"/><path d="M8 10.5v4"/><path d="M6 12.5h4"/><path d="M16 11.5h.01"/><path d="M18 13.5h.01"/>',
    "doc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6"/><path d="M9 16h6"/>',
    "sheet": '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16"/><path d="M4 15h16"/><path d="M10 4v16"/>',
    "slides": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M12 16v4"/><path d="M8 20h8"/>',
    "db": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    "sigma": '<path d="M18 5H6l7 7-7 7h12"/>',
    "pen": '<path d="M4 20l4-1 11-11-3-3L5 16z"/><path d="M14 6l3 3"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 18l5-5 4 4 3-3 4 4"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M12 3v3"/><path d="M12 18v3"/><path d="M3 12h3"/><path d="M18 12h3"/><path d="M5.6 5.6l2.1 2.1"/><path d="M16.3 16.3l2.1 2.1"/><path d="M18.4 5.6l-2.1 2.1"/><path d="M7.7 16.3l-2.1 2.1"/>',
    "printer": '<path d="M7 9V4h10v5"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M7 14h10v6H7z"/>',
    "bluetooth": '<path d="M7 7l10 10-5 4V3l5 4L7 17"/>',
    "network": '<circle cx="6" cy="12" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 11l8-4"/><path d="M8 13l8 4"/>',
    "wifi": '<path d="M5 12a10 10 0 0 1 14 0"/><path d="M8.5 15.5a5 5 0 0 1 7 0"/><path d="M12 19h.01"/>',
    "chart": '<path d="M5 20v-6"/><path d="M10 20V6"/><path d="M15 20v-9"/><path d="M20 20V4"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l6 3.5-6 3.5z"/>',
    "camera": '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "volume": '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6"/><path d="M18.5 6.5a8 8 0 0 1 0 11"/>',
    "keyboard": '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01"/><path d="M10 10h.01"/><path d="M14 10h.01"/><path d="M18 10h.01"/><path d="M7 14h10"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3"/><path d="M15 3v3"/><path d="M9 18v3"/><path d="M15 18v3"/><path d="M3 9h3"/><path d="M3 15h3"/><path d="M18 9h3"/><path d="M18 15h3"/>',
    "text": '<path d="M5 6h14"/><path d="M5 11h14"/><path d="M5 16h9"/>',
    "vim": '<path d="M5 5l7 14 7-14"/>',
    "send": '<path d="M21 3L3 11l7 3 3 7z"/><path d="M10 14l11-11"/>',
    "loop": '<path d="M12 12c-2-3-5-4-7-2s-2 6 0 7 5 0 7-3c2 3 5 4 7 3s2-5 0-7-5-1-7 2z"/>',
    "moon": '<path d="M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z"/>',
    "coffee": '<path d="M17 8h1a3 3 0 1 1 0 6h-1"/><path d="M3 8h14v6a5 5 0 0 1-5 5H8a5 5 0 0 1-5-5z"/>',
    "grid": '<circle cx="5" cy="5" r="1.4"/><circle cx="12" cy="5" r="1.4"/><circle cx="19" cy="5" r="1.4"/><circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/><circle cx="5" cy="19" r="1.4"/><circle cx="12" cy="19" r="1.4"/><circle cx="19" cy="19" r="1.4"/>',
    "e": '<path d="M16 5H8v14h8"/><path d="M8 12h6"/>',
    "archive": '<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v10h14V9"/><path d="M10 13h4"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
    "compass": '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 1-1 1.7"/><path d="M12 17h.01"/>',
    "layout": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M9 9v11"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.5 0 2-1 1.5-2.2-.5-1.2.3-2.3 1.6-2.3H17a4 4 0 0 0 4-4c0-5-4-9.5-9-9.5z"/><path d="M7.5 11h.01"/><path d="M10 7.5h.01"/><path d="M14.5 7.5h.01"/>',
    "wrench": '<path d="M14.5 6.5a4 4 0 0 0 5 5l-9 9a2.1 2.1 0 0 1-3-3z"/><path d="M14.5 6.5l3 3"/>',
}

# id do .desktop (sem extensão) -> glifo
BY_ID = {
    "kitty": "terminal", "org.kde.konsole": "terminal", "org.gnome.Nautilus": "folder", "thunar": "folder", "thunar-settings": "gear",
    "thunar-bulk-rename": "text", "firefox": "globe", "chromium": "chromium", "spotify-launcher": "music", "com.anthropic.Claude": "spark",
    "chatgpt": "hex", "code-oss": "code", "vim": "vim", "org.gnome.TextEditor": "text", "entropydash": "e", "entropy-agenda": "calendar",
    "entropy-apps": "grid", "postman": "send", "arduino-ide-v2": "loop", "dev.noctalia.Noctalia": "moon", "steam": "gamepad",
    "Muck": "cube", "Shadow Fight Arena": "gamepad", "Stumble Guys": "gamepad", "tlauncher": "cube", "org.prismlauncher.PrismLauncher": "cube",
    "org.vinegarhq.Sober": "cube", "org.freecad.FreeCAD": "cube", "com.orcaslicer.OrcaSlicer": "cube", "cmake-gui": "gear",
    "libreoffice-writer": "doc", "libreoffice-calc": "sheet", "libreoffice-impress": "slides", "libreoffice-draw": "pen",
    "libreoffice-math": "sigma", "libreoffice-base": "db", "libreoffice-startcenter": "layout", "btop": "chart", "lstopo": "cpu",
    "vlc": "play", "org.gnome.Snapshot": "camera", "org.pulseaudio.pavucontrol": "volume", "atalhos": "keyboard",
    "blueman-manager": "bluetooth", "nm-connection-editor": "network", "com.github.ztefn.haguichi": "network",
    "system-config-printer": "printer", "cups": "printer", "org.gnome.FileRoller": "archive", "rofi": "search",
    "rofi-theme-selector": "palette", "nwg-look": "palette", "qt6ct": "palette", "nwg-panel-config": "gear", "xgps": "compass",
    "xgpsspeed": "compass", "assistant": "help", "linguist": "text", "designer": "layout", "qdbusviewer": "network",
    "qvidcap": "camera", "qv4l2": "camera", "uuctl": "gear", "jconsole-java17-openjdk": "coffee", "jshell-java17-openjdk": "coffee",
    "jconsole-java-openjdk": "coffee", "jshell-java-openjdk": "coffee",
}
BY_CAT = {"Network": "globe", "Development": "code", "AudioVideo": "play", "Audio": "music", "Video": "play", "Game": "gamepad",
          "Office": "doc", "Graphics": "image", "System": "gear", "Settings": "gear", "Utility": "wrench", "Education": "help"}
# glifo -> cor da paleta (variedade sutil e consistente)
COLOR = {"primary": {"terminal", "code", "gear", "wrench", "chart", "cpu", "vim", "text", "grid", "e", "moon", "keyboard", "palette", "search", "loop", "send"},
         "secondary": {"globe", "chromium", "network", "wifi", "bluetooth", "folder", "archive", "doc", "sheet", "slides", "db", "sigma", "layout", "calendar", "compass", "printer"},
         "tertiary": {"music", "play", "camera", "volume", "image", "pen", "spark", "hex", "chat", "gamepad", "cube", "coffee", "help"}}


def mix(a, b, t):
    ra, rb = cc.hex2rgb(a), cc.hex2rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def accent_for(glyph):
    for key, names in COLOR.items():
        if glyph in names:
            return PAL[key]
    return PAL["primary"]



# ---------- estilo "logo": logo real do app, recolorida em 1 tom da paleta ----------
def _lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def _sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _mixc(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _hx(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, v)) for v in c)


def analyze(im):
    """fundo = cor perto das bordas do desenho; é tile se as amostras são opacas e parecidas"""
    sm = im.convert("RGBA").resize((64, 64))
    W = 64
    px = sm.load()
    pts = [(x, y) for y in range(W) for x in range(W) if px[x, y][3] > 200]
    if not pts:
        return (0, 0, 0), False
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    xm, ym = (x0 + x1) // 2, (y0 + y1) // 2
    pos = [(x0 + 0.10 * w, ym), (x1 - 0.10 * w, ym), (xm, y0 + 0.10 * h), (xm, y1 - 0.10 * h),
           (x0 + 0.28 * w, y0 + 0.28 * h), (x1 - 0.28 * w, y0 + 0.28 * h), (x0 + 0.28 * w, y1 - 0.28 * h), (x1 - 0.28 * w, y1 - 0.28 * h)]
    edge = [px[int(x), int(y)][:3] for x, y in pos[:4] if px[int(x), int(y)][3] > 200]
    if len(edge) == 4:
        em = tuple(sum(c[i] for c in edge) // 4 for i in range(3))
        if max(math.dist(c, em) for c in edge) < 80:
            return em, True
    cols = []
    for x, y in pos:
        p = px[int(x), int(y)]
        if p[3] > 200:
            cols.append(p[:3])
    if len(cols) < 4:
        return (0, 0, 0), False
    mean = tuple(sum(c[i] for c in cols) // len(cols) for i in range(3))
    spread = max(math.dist(c, mean) for c in cols)
    if len(cols) < 6:
        # fundo redondo: só as 4 amostras das bordas caem dentro do desenho
        return mean, spread < 70
    return mean, spread < 120


class Mono:
    def __init__(self):
        self.acc = cc.hex2rgb(PAL["primary"])
        self.tile = _mixc(cc.hex2rgb(PAL["surface"]), cc.hex2rgb(PAL["fg"]), 0.10)

    def conv(self, c, bgc, tile):
        if tile:
            return _mixc(self.tile, self.acc, _sstep(0.14, 0.58, math.dist(c, bgc) / 441.0))
        return _mixc(self.tile, self.acc, 0.45 + 0.55 * _sstep(0.15, 0.9, _lum(c)))

    def svg(self, txt, bgc, tile):
        txt = re.sub(r"<filter[\s\S]*?</filter>", "", txt)
        txt = re.sub(r'\sfilter="[^"]*"', "", txt)

        def hexrep(m):
            h = m.group(1)
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            return _hx(self.conv(tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), bgc, tile))
        txt = re.sub(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", hexrep, txt)
        txt = re.sub(r"rgb\(([^)]*)\)", lambda m: _hx(self.conv(tuple(int(float(x)) for x in m.group(1).split(",")[:3]), bgc, tile)), txt)
        named = {"white": (255, 255, 255), "black": (0, 0, 0)}
        return re.sub(r'(fill|stroke|stop-color)="(white|black)"', lambda m: f'{m.group(1)}="{_hx(self.conv(named[m.group(2)], bgc, tile))}"', txt)

    def png(self, path, size=256):
        im = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        bgc, tile = analyze(im)
        px = im.load()
        for y in range(size):
            for x in range(size):
                r, g_, b, a = px[x, y]
                c = self.conv((r, g_, b), bgc, tile)
                px[x, y] = (c[0], c[1], c[2], a)
        return im


def convert_logo(src, name, mono, tmp):
    """devolve ('svg', texto) ou ('png', Image) com a logo recolorida"""
    if src.lower().endswith(".svg"):
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(src, 128, 128)
        pb.savev(tmp, "png", [], [])
        bgc, tile = analyze(Image.open(tmp))
        return "svg", mono.svg(open(src).read(), bgc, tile)
    return "png", mono.png(src)


def svg_glyph(glyph, fg, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<g transform="translate(7 7) scale(2.08)" fill="none" stroke="{accent}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round">{GL[glyph]}</g>
</svg>
'''


def svg_tilegl(glyph, tile, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<rect x="3" y="3" width="58" height="58" rx="18" fill="{tile}"/>
<g transform="translate(16 16) scale(1.33)" fill="none" stroke="{accent}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{GL[glyph]}</g>
</svg>
'''


def svg_flat(glyph, fg, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<rect x="3" y="3" width="58" height="58" rx="20" fill="{fg}" fill-opacity="0.09"/>
<g transform="translate(16 16) scale(1.33)" fill="none" stroke="{accent}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{GL[glyph]}</g>
</svg>
'''


def svg(glyph, tile_hi, tile_lo, fg, accent):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{tile_hi}"/><stop offset="1" stop-color="{tile_lo}"/></linearGradient>
<radialGradient id="r" cx="0.22" cy="0.12" r="0.95"><stop offset="0" stop-color="{accent}" stop-opacity="0.30"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
</defs>
<rect x="2" y="2" width="60" height="60" rx="16" fill="url(#g)"/>
<rect x="2" y="2" width="60" height="60" rx="16" fill="url(#r)"/>
<rect x="2.5" y="2.5" width="59" height="59" rx="15.5" fill="none" stroke="{fg}" stroke-opacity="0.16"/>
<g transform="translate(14 14) scale(1.5)" fill="none" stroke="{accent}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{GL[glyph]}</g>
</svg>
'''


def main(style=None, out=None):
    global OUT, APPS
    style = style or os.environ.get("ENTROPY_ICON_STYLE", "glossy")
    if out:
        OUT = out
        APPS = os.path.join(OUT, "scalable", "apps")
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(APPS)
    sur, fg = PAL["surface"], PAL["fg"]
    light = (0.299 * cc.hex2rgb(sur)[0] + 0.587 * cc.hex2rgb(sur)[1] + 0.114 * cc.hex2rgb(sur)[2]) > 150
    tile_hi = mix(sur, fg, 0.10 if not light else 0.0)
    tile_lo = mix(sur, "#000000", 0.30 if not light else 0.10)
    done = {}
    for a in Gio.AppInfo.get_all():
        if not a.should_show():
            continue
        ic = a.get_icon()
        if isinstance(ic, Gio.ThemedIcon):
            name = ic.get_names()[0]
        elif isinstance(ic, Gio.FileIcon):
            name = os.path.splitext(os.path.basename(a.get_id()))[0]
        else:
            continue
        aid = a.get_id().replace(".desktop", "")
        cat = (a.get_categories() or "").split(";")
        glyph = BY_ID.get(aid) or next((BY_CAT[c] for c in cat if c in BY_CAT), "cube")
        done[name] = glyph
    # nomes extras usados por janelas/dock
    for name, glyph in (("claude-desktop", "spark"), ("claude", "spark"), ("kitty", "terminal"), ("entropydash", "e"), ("entropy-apps", "grid")):
        done[name] = glyph
    mono = None
    th = None
    if style == "logo":
        mono = Mono()
        th = Gtk.IconTheme()
        th.set_custom_theme("Papirus-Dark")
        png_dir = os.path.join(OUT, "256x256", "apps")
        os.makedirs(png_dir, exist_ok=True)
    tmp = os.path.join(OUT, "_t.png")
    for name, glyph in done.items():
        acc = accent_for(glyph)
        if style == "logo":
            info = th.lookup_icon(name, 128, Gtk.IconLookupFlags.FORCE_SVG)
            if info and info.get_filename():
                try:
                    kind, data = convert_logo(info.get_filename(), name, mono, tmp)
                    if kind == "svg":
                        open(os.path.join(APPS, name + ".svg"), "w").write(data)
                    else:
                        data.save(os.path.join(png_dir, name + ".png"))
                    continue
                except Exception as e:
                    print("falha", name, e)
            open(os.path.join(APPS, name + ".svg"), "w").write(svg_tilegl(glyph, _hx(mono.tile), acc))
            continue
        body = svg_glyph(glyph, fg, acc) if style == "glyph" else svg_flat(glyph, fg, acc) if style == "flat" else svg(glyph, tile_hi, tile_lo, fg, acc)
        open(os.path.join(APPS, name + ".svg"), "w").write(body)
    open(os.path.join(OUT, "index.theme"), "w").write(
        "[Icon Theme]\nName=Entropy\nComment=Icones simples em vidro, nas cores do wallpaper\nInherits=Papirus-Dark,Adwaita,hicolor\n"
        "Directories=scalable/apps,256x256/apps\n\n[scalable/apps]\nSize=64\nMinSize=8\nMaxSize=512\nType=Scalable\nContext=Applications\n\n[256x256/apps]\nSize=256\nType=Fixed\nContext=Applications\n")
    subprocess.run(["gtk-update-icon-cache", "-f", "-t", OUT], capture_output=True)
    print(f"{len(done)} ícones gerados em {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None, sys.argv[2] if len(sys.argv) > 2 else None)
