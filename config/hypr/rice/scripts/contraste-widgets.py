#!/usr/bin/env python3
"""Contraste automático dos widgets de texto do Noctalia.

Mede o brilho do wallpaper atrás de cada widget (relógio, data, música) e
escolhe texto escuro em fundo claro, ou texto claro com sombra em fundo escuro.
Roda pelo hook `wallpaper_changed` do Noctalia (e pode ser rodado à mão).
"""
import json, os, re, subprocess

CFG = os.path.expanduser("~/.config/noctalia/config.toml")
STATE = os.path.expanduser("~/.local/state/noctalia/settings.toml")
TIPOS = ("clock", "media_player")   # widgets sem fundo próprio
LIMIAR = 0.55                         # brilho (0..1) a partir do qual o fundo é "claro"


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def monitores():
    out = {}
    for m in json.loads(run("hyprctl", "monitors", "-j") or "[]"):
        out[m["name"]] = (m["width"] / m["scale"], m["height"] / m["scale"])
    return out


def camadas():
    """posição real (coordenadas lógicas do monitor) de cada widget: {nome: (monitor, cx, cy, w, h)}"""
    out = {}
    try:
        data = json.loads(run("hyprctl", "layers", "-j") or "{}")
        mons = {m["name"]: (m["x"], m["y"]) for m in json.loads(run("hyprctl", "monitors", "-j") or "[]")}
    except Exception:
        return out
    for mon, d in data.items():
        for lv in d.get("levels", {}).values():
            for l in lv:
                ns = l.get("namespace", "")
                if ns.startswith("noctalia-desktop-widget-") and mon in mons:
                    nome = ns.rsplit("-", 1)[-1]
                    mx, my = mons[mon]
                    out[nome] = (mon, l["x"] - mx + l["w"] / 2.0, l["y"] - my + l["h"] / 2.0, max(40.0, l["w"]), max(24.0, l["h"]))
    return out


def tamanho_imagem(path):
    s = run("ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", path)
    w, h = s.split(",")[:2]
    return int(w), int(h)


def brilho(path, ow, oh, cx, cy, bw, bh):
    """Brilho médio da área do widget, considerando o wallpaper em modo 'crop'."""
    iw, ih = tamanho_imagem(path)
    esc = max(ow / iw, oh / ih)                    # imagem escalada para cobrir a tela
    offx, offy = (iw * esc - ow) / 2, (ih * esc - oh) / 2
    x0 = max(0, (cx - bw / 2 + offx) / esc); y0 = max(0, (cy - bh / 2 + offy) / esc)
    w = max(4, min(iw - x0, bw / esc)); h = max(4, min(ih - y0, bh / esc))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf",
         f"crop={int(w)}:{int(h)}:{int(x0)}:{int(y0)},scale=1:1,format=gray",
         "-frames:v", "1", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    return raw[0] / 255 if raw else 0.0


def widgets(texto):
    """Encontra os widgets de área de trabalho (nome, tipo, output, cx, cy, w, h)."""
    achados = []
    for m in re.finditer(r"\[\s*desktop_widgets\.widget\.([a-z0-9_]+)\]\n((?:[ \t]*[a-z_]+ = [^\n]*\n)*)", texto):
        nome, corpo = m.group(1), m.group(2)
        campos = dict(re.findall(r"^\s*([a-z_]+) = (.+)$", corpo, re.M))
        tipo = campos.get("type", "").strip('"')
        if tipo in TIPOS and "output" in campos:
            achados.append((nome, campos["output"].strip('"'), float(campos.get("cx", 0)),
                            float(campos.get("cy", 0)), float(campos.get("box_width", 300)),
                            float(campos.get("box_height", 100))))
    return achados


def aplicar(texto, nome, claro):
    cor, sombra = ('"surface"', "false") if claro else ('"on_surface"', "true")

    def rep(m):
        corpo = m.group(2)
        variante = re.search(r'color = "on_surface_variant"|color = "surface_variant"', corpo)
        c = cor if not variante else ('"surface_variant"' if claro else '"on_surface_variant"')
        for k, v in (("color", c), ("shadow", sombra)):
            if re.search(r"^\s*%s = " % k, corpo, re.M):
                corpo = re.sub(r"^(\s*)%s = .*$" % k, r"\g<1>%s = %s" % (k, v), corpo, count=1, flags=re.M)
            else:
                ind = re.match(r"\s*", corpo).group(0) if corpo else ""
                corpo += f"{ind}{k} = {v}\n"
        return m.group(1) + corpo

    return re.sub(r"(\s*\[desktop_widgets\.widget\.%s\.settings\]\n)((?:[ \t]*[a-z_]+ = [^\n]*\n)*)" % nome, rep, texto)


def main():
    mons = monitores()
    base = open(CFG).read()
    decisoes = {}
    reais = camadas()
    for nome, out, cx, cy, bw, bh in widgets(base):
        if nome in reais:   # usa onde o widget realmente está (o config pode estar desatualizado)
            out, cx, cy, bw, bh = reais[nome]
        if out not in mons:
            continue
        wp = run("noctalia", "msg", "wallpaper-get", out)
        if not wp or not os.path.exists(wp):
            continue
        b = brilho(wp, *mons[out], cx, cy, bw, bh)
        decisoes[nome] = b >= LIMIAR
        print(f"{nome:10s} {out:9s} brilho={b:.2f} -> {'texto escuro' if decisoes[nome] else 'texto claro'}")
    mudou = False
    for arq in (CFG, STATE):
        if not os.path.exists(arq):
            continue
        t = open(arq).read(); novo = t
        for nome, claro in decisoes.items():
            novo = aplicar(novo, nome, claro)
        if novo != t:
            open(arq, "w").write(novo); mudou = True
    if mudou:
        run("noctalia", "msg", "config-reload")


if __name__ == "__main__":
    import fcntl, time
    time.sleep(0.5)  # deixa o Noctalia terminar de aplicar o wallpaper
    with open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "contraste-widgets.lock"), "w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit(0)   # já tem uma execução rodando
        main()
