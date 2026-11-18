#!/usr/bin/env python3
"""Exporta a rice do sistema (~/.config) para este repositório, já limpa de dados pessoais.

Uso: python3 tools/export.py            (a partir da raiz do repositório)
Depois: git add -A && git commit && git push
"""
import os, re, shutil, sys

HOME = os.path.expanduser("~")
CFG = os.path.join(HOME, ".config")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "config")

SKIP = re.compile(r"(\.bak|\.orig|\.fade-quebrado|\.entropy-backup|__pycache__|\.log$|/old/)")
# o que da pasta hypr entra (o resto é de rices antigas)
HYPR_FILES = ["hyprland.conf", "windowshade.conf", "noctalia.conf", "hypridle.conf"]
HYPR_DIRS = ["rice", "shaders"]
# scripts pessoais que não vão
PERSONAL = {"rice/scripts/trevor-notify.py"}


def copy_tree(src, dst, rel_base):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not SKIP.search(os.path.join(root, d) + "/")]
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, rel_base)
            if SKIP.search(full) or rel in PERSONAL:
                continue
            target = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(full, target)


def sanitize_text(path):
    try:
        s = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        return
    s = s.replace(HOME, "@HOME@")
    open(path, "w", encoding="utf-8").write(s)


def patch(path, old, new, count=1):
    s = open(path, encoding="utf-8").read()
    if old not in s:
        print(f"aviso: trecho não encontrado em {os.path.relpath(path, REPO)}: {old[:50]!r}")
        return
    open(path, "w", encoding="utf-8").write(s.replace(old, new, count))


def sanitize_noctalia(path):
    s = open(path, encoding="utf-8").read()
    parts = re.split(r"(?m)^(?=\[)", s)
    keep = [p for p in parts if not re.match(r"\[+[^\]\n]*entropy", p)]
    s = "".join(keep)
    s = re.sub(r', "(lp|hd)_entropy_(agenda|projetos)"', "", s)
    s = re.sub(r'"(entropydash|com\.anthropic\.Claude|chatgpt|org\.kde\.konsole)",?\s*', "", s)
    s = s.replace('pinned = ["entropy-apps", "kitty", "org.gnome.Nautilus", "firefox", "spotify-launcher", ]', 'pinned = ["entropy-apps", "kitty", "org.gnome.Nautilus", "firefox", "spotify-launcher"]')
    s = s.replace("fingerprint = true", "fingerprint = false")
    s = s.replace("purple-waves.png", "entropy-default.png")
    s = s.replace(HOME, "@HOME@")
    open(path, "w", encoding="utf-8").write(s)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    hypr_out = os.path.join(OUT, "hypr")
    os.makedirs(hypr_out)
    for f in HYPR_FILES:
        shutil.copy2(os.path.join(CFG, "hypr", f), os.path.join(hypr_out, f))
    for d in HYPR_DIRS:
        copy_tree(os.path.join(CFG, "hypr", d), hypr_out, os.path.join(CFG, "hypr"))
    # kitty
    k_out = os.path.join(OUT, "kitty")
    os.makedirs(os.path.join(k_out, "themes"))
    shutil.copy2(os.path.join(CFG, "kitty", "kitty.conf"), k_out)
    shutil.copy2(os.path.join(CFG, "kitty", "themes", "noctalia.conf"), os.path.join(k_out, "themes"))
    # noctalia
    n_out = os.path.join(OUT, "noctalia")
    os.makedirs(n_out)
    shutil.copy2(os.path.join(CFG, "noctalia", "config.toml"), n_out)
    sanitize_noctalia(os.path.join(n_out, "config.toml"))

    # limpeza geral de caminhos pessoais
    for root, _d, files in os.walk(hypr_out):
        for f in files:
            sanitize_text(os.path.join(root, f))
    sanitize_text(os.path.join(k_out, "kitty.conf"))

    # ajustes de portabilidade
    h = lambda *p: os.path.join(hypr_out, *p)
    patch(h("hyprland.conf"), "source = ~/.config/hypr/windowshade.conf",
          "# Plugin HyprWindowShade (animação de janelas e papel de parede animado): opcional.\n"
          "# Instale o plugin e descomente a linha abaixo (veja o README).\n"
          "# source = ~/.config/hypr/windowshade.conf")
    patch(h("rice", "scripts", "plugins.sh"), "hyprctl plugin list | grep -q 'HyprWindowShade' ||",
          "[ -f @HOME@/.local/share/hyprland/plugins/HyprWindowShade.so ] && ! hyprctl plugin list | grep -q 'HyprWindowShade' &&")
    # widget pessoal do autor na lista de camadas com vidro
    g = h("rice", "glass.conf")
    gs = open(g, encoding="utf-8").read()
    gs = re.sub(r"noctalia-desktop-widget-dk/entropy:[^,\n]*, ?", "", gs)
    open(g, "w", encoding="utf-8").write(gs)
    # atalho pessoal
    b = h("rice", "binds.conf")
    s = open(b, encoding="utf-8").read()
    s = "\n".join(l for l in s.splitlines() if "entropydash" not in l and ".local/bin/atalhos" not in l) + "\n"
    open(b, "w", encoding="utf-8").write(s)
    # monitores genéricos (o do autor fica como exemplo)
    mon = h("rice", "monitors.conf")
    shutil.copy2(mon, h("rice", "monitors.exemplo-autor.conf"))
    open(mon, "w", encoding="utf-8").write(
        "# Configuração genérica de monitores (ajuste à sua tela: `hyprctl monitors`).\n"
        "# Exemplo de duas telas com escala: veja monitors.exemplo-autor.conf\n"
        "monitor = , preferred, auto, 1\n")
    # wallpapers animados de exemplo (shaders e loop de vídeo)
    lw = os.path.join(REPO, "live-wallpapers")
    shutil.rmtree(lw, ignore_errors=True)
    for nome in ("aurora", "ondas", "loop-fluido"):
        src = os.path.join(HOME, ".local/share/entropy/wallpapers", nome)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(lw, nome), ignore=shutil.ignore_patterns("preview.jpg"))
    print("exportado para", OUT)
    import subprocess
    subprocess.run([sys.executable, os.path.join(REPO, "tools", "gen-archinstall.py")], check=False)


if __name__ == "__main__":
    sys.exit(main())
