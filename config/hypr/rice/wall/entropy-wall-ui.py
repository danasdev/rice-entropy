#!/usr/bin/env python3
"""Entropy Wall UI: biblioteca de wallpapers animados. Clique no cartão para ligar; "Adicionar" importa vídeo, imagem ou shader."""
import importlib.util, json, os, re, shutil, subprocess, sys
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("entropy_cc", os.path.join(HERE, "..", "painel", "entropy-cc.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
PAL = cc.PAL

LIB = os.path.expanduser("~/.local/share/entropy/wallpapers")
STATE = os.path.expanduser("~/.config/entropy-wall.json")
CTL = os.path.join(HERE, "entropy-wall-ctl")
VIDEO = (".mp4", ".webm", ".mkv", ".mov", ".gif")
IMAGE = (".png", ".jpg", ".jpeg", ".webp")
SHADER = (".frag", ".glsl")
CARD_W, CARD_H = 230, 140


def hexa(c, a):
    r, g, b = cc.hex2rgb(c)
    return f"rgba({r},{g},{b},{a})"


CSS = f"""
window {{ background-color: {PAL['surface']}; color: {PAL['fg']}; }}
.title {{ font-size: 20px; font-weight: 700; }}
.sub {{ font-size: 12px; color: {hexa(PAL['fg'], 0.55)}; }}
button.card {{ background: {hexa(PAL['fg'], 0.05)}; border: 1px solid {hexa(PAL['fg'], 0.10)}; border-radius: 18px; padding: 0; }}
button.card:hover {{ background: {hexa(PAL['fg'], 0.09)}; }}
button.card.on {{ border-color: {PAL['primary']}; background: {hexa(PAL['primary'], 0.16)}; }}
.cname {{ font-size: 13px; font-weight: 600; }}
.ctype {{ font-size: 11px; color: {hexa(PAL['fg'], 0.5)}; }}
button.act {{ background: {hexa(PAL['fg'], 0.08)}; border: none; border-radius: 12px; padding: 8px 16px; }}
button.act:hover {{ background: {hexa(PAL['fg'], 0.14)}; }}
button.main {{ background: {PAL['primary']}; color: {PAL['on_acc']}; border-radius: 12px; padding: 8px 18px; font-weight: 700; }}
button.danger {{ background: {hexa('#ff6b6b', 0.18)}; border: none; border-radius: 12px; padding: 8px 16px; }}
.panelbar {{ background: {hexa(PAL['fg'], 0.05)}; border-radius: 16px; padding: 10px 14px; }}
scale highlight {{ background-color: {PAL['primary']}; }}
"""


def run(*cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def manifest(name):
    try:
        return json.load(open(os.path.join(LIB, name, "manifest.json")))
    except Exception:
        return {}


def save_manifest(name, m):
    json.dump(m, open(os.path.join(LIB, name, "manifest.json"), "w"), indent=1)


def current():
    try:
        return json.load(open(STATE)).get("current")
    except Exception:
        return None


def thumb_path(name):
    m, base = manifest(name), os.path.join(LIB, name)
    for cand in (os.path.join(base, "preview.jpg"),):
        if os.path.exists(cand):
            return cand
    if m.get("type") == "image":
        return os.path.join(base, m.get("file", ""))
    if m.get("type") == "layers" and m.get("layers"):
        return os.path.join(base, m["layers"][0]["file"])
    if m.get("type") == "video":
        out = os.path.join(base, "preview.jpg")
        run("ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", os.path.join(base, m["file"]), "-frames:v", "1", "-vf", "scale=480:-2", out)
        return out if os.path.exists(out) else None
    return None


def slug(txt):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return s or "wallpaper"


class UI:
    def __init__(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = self.win = Gtk.Window(title="Entropy Wall")
        win.set_default_size(820, 620)
        win.connect("destroy", Gtk.main_quit)
        win.connect("key-press-event", lambda w, e: Gtk.main_quit() if e.keyval == Gdk.KEY_Escape else None)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("start", "end", "top", "bottom"):
            getattr(root, f"set_margin_{side}")(20)
        win.add(root)

        head = Gtk.Box(spacing=10)
        tv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        t = Gtk.Label(label="Wallpapers animados", xalign=0)
        t.get_style_context().add_class("title")
        self.sub = Gtk.Label(label="", xalign=0)
        self.sub.get_style_context().add_class("sub")
        tv.pack_start(t, False, False, 0)
        tv.pack_start(self.sub, False, False, 0)
        head.pack_start(tv, True, True, 0)
        for text, cb, cls in (("Desligar", self.turn_off, "act"), ("Adicionar", self.add, "main")):
            b = Gtk.Button(label=text)
            b.get_style_context().add_class(cls)
            b.connect("clicked", lambda _b, cb=cb: cb())
            head.pack_start(b, False, False, 0)
        root.pack_start(head, False, False, 0)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(4)
        self.flow.set_min_children_per_line(2)
        self.flow.set_row_spacing(14)
        self.flow.set_column_spacing(14)
        self.flow.set_valign(Gtk.Align.START)
        for m in ("start", "end", "top", "bottom"):
            getattr(self.flow, f"set_margin_{m}")(4)
        sc.add(self.flow)
        root.pack_start(sc, True, True, 0)

        bar = self.bar = Gtk.Box(spacing=14)
        bar.get_style_context().add_class("panelbar")
        self.sel_lbl = Gtk.Label(label="", xalign=0)
        self.sel_lbl.get_style_context().add_class("cname")
        self.par = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 0.12, 0.005)
        self.par.set_size_request(180, -1)
        self.par.set_draw_value(False)
        self.par.connect("value-changed", self.on_par)
        self.par_lbl = Gtk.Label(label="Parallax")
        self.par_lbl.get_style_context().add_class("sub")
        self.fps = Gtk.ComboBoxText()
        for f in ("60", "30", "24"):
            self.fps.append_text(f)
        self.fps.connect("changed", self.on_fps)
        self.react = Gtk.CheckButton(label="Só anima com o mouse")
        self.react.connect("toggled", self.on_react)
        rm = Gtk.Button(label="Remover")
        rm.get_style_context().add_class("danger")
        rm.connect("clicked", lambda *_: self.remove())
        bar.pack_start(self.sel_lbl, True, True, 0)
        bar.pack_start(self.par_lbl, False, False, 0)
        bar.pack_start(self.par, False, False, 0)
        bar.pack_start(Gtk.Label(label="FPS"), False, False, 0)
        bar.pack_start(self.fps, False, False, 0)
        bar.pack_start(self.react, False, False, 0)
        bar.pack_start(rm, False, False, 0)
        root.pack_start(bar, False, False, 0)
        self.selected, self.loading = None, False
        self.refresh()
        win.show_all()
        self.bar.hide()

    # ---------- lista ----------
    def refresh(self):
        for c in self.flow.get_children():
            self.flow.remove(c)
        names = sorted(n for n in os.listdir(LIB) if os.path.isfile(os.path.join(LIB, n, "manifest.json"))) if os.path.isdir(LIB) else []
        cur = current()
        self.sub.set_text(f"{len(names)} wallpapers" + (f"  ·  ligado: {cur}" if cur else "  ·  engine desligado"))
        for n in names:
            self.flow.add(self.card(n, n == cur))
        self.flow.show_all()

    def card(self, name, on):
        m = manifest(name)
        b = Gtk.Button()
        b.get_style_context().add_class("card")
        if on:
            b.get_style_context().add_class("on")
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        img = Gtk.Image()
        p = thumb_path(name)
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(p, CARD_W, CARD_H, False) if p else None
            if pb is not None:
                w, h = pb.get_width(), pb.get_height()
                k = max(CARD_W / w, CARD_H / h)
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(p, int(w * k) + 1, int(h * k) + 1, True)
                pb = pb.new_subpixbuf(max(0, (pb.get_width() - CARD_W) // 2), max(0, (pb.get_height() - CARD_H) // 2),
                                      min(CARD_W, pb.get_width()), min(CARD_H, pb.get_height()))
                img.set_from_pixbuf(pb)
        except Exception:
            pass
        img.set_size_request(CARD_W, CARD_H)
        v.pack_start(img, False, False, 0)
        l = Gtk.Label(label=name, xalign=0)
        l.get_style_context().add_class("cname")
        l.set_margin_start(12)
        kind = {"shader": "shader", "video": "vídeo em loop", "image": "imagem com parallax", "layers": "camadas com parallax"}.get(m.get("type"), "?")
        t = Gtk.Label(label=kind + ("  ·  ligado" if on else ""), xalign=0)
        t.get_style_context().add_class("ctype")
        t.set_margin_start(12)
        t.set_margin_bottom(10)
        v.pack_start(l, False, False, 0)
        v.pack_start(t, False, False, 0)
        b.add(v)
        b.connect("clicked", lambda *_: self.activate(name))
        return b

    def activate(self, name):
        run(CTL, "set", name)
        self.selected = name
        self.show_bar(name)
        GLib.timeout_add(500, lambda: (self.refresh(), False)[1])
        GLib.timeout_add(1500, self.check_err)

    def check_err(self):
        f = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-wall.err")
        if os.path.exists(f):
            msg = open(f).read()
            os.remove(f)
            d = Gtk.MessageDialog(transient_for=self.win, modal=True, message_type=Gtk.MessageType.ERROR,
                                  buttons=Gtk.ButtonsType.OK, text="O shader não compilou")
            d.format_secondary_text(msg)
            d.run()
            d.destroy()
        return False

    def show_bar(self, name):
        m = manifest(name)
        self.loading = True
        self.sel_lbl.set_text(name)
        is_par = m.get("type") in ("image", "layers", "video")
        self.par.set_visible(is_par)
        self.par_lbl.set_visible(is_par)
        self.par.set_value(float(m.get("parallax", 0.0)))
        self.fps.set_active({"60": 0, "30": 1, "24": 2}.get(str(m.get("fps", 60)), 0))
        self.react.set_active(bool(m.get("reactive", False)))
        self.react.set_visible(m.get("type") == "shader")
        self.bar.show()
        self.loading = False

    def save_field(self, key, val):
        if self.loading or not self.selected:
            return
        m = manifest(self.selected)
        m[key] = val
        save_manifest(self.selected, m)
        if current() == self.selected:
            GLib.timeout_add(300, lambda: (run(CTL, "set", self.selected), False)[1])

    def on_par(self, s):
        self.save_field("parallax", round(s.get_value(), 3))

    def on_fps(self, c):
        t = c.get_active_text()
        if t:
            self.save_field("fps", int(t))

    def on_react(self, c):
        self.save_field("reactive", c.get_active())

    def turn_off(self):
        run(CTL, "off")
        GLib.timeout_add(300, lambda: (self.refresh(), False)[1])

    def remove(self):
        if not self.selected:
            return
        d = Gtk.MessageDialog(transient_for=self.win, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.YES_NO, text=f"Remover \"{self.selected}\"?")
        d.format_secondary_text("A pasta do wallpaper será apagada da biblioteca (os arquivos originais que você importou não são tocados).")
        if d.run() == Gtk.ResponseType.YES:
            if current() == self.selected:
                run(CTL, "off")
            shutil.rmtree(os.path.join(LIB, self.selected), ignore_errors=True)
            self.selected = None
            self.bar.hide()
            self.refresh()
        d.destroy()

    # ---------- importar ----------
    def add(self):
        dlg = Gtk.FileChooserDialog(title="Adicionar wallpaper", transient_for=self.win, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Adicionar", Gtk.ResponseType.OK)
        flt = Gtk.FileFilter()
        flt.set_name("Vídeo, imagem ou shader")
        for ext in VIDEO + IMAGE + SHADER:
            flt.add_pattern("*" + ext)
            flt.add_pattern("*" + ext.upper())
        dlg.add_filter(flt)
        dlg.set_select_multiple(True)
        dlg.set_current_folder(os.path.expanduser("~/Vídeos") if os.path.isdir(os.path.expanduser("~/Vídeos")) else os.path.expanduser("~"))
        if dlg.run() == Gtk.ResponseType.OK:
            msgs = [self.import_file(f) for f in dlg.get_filenames()]
            bad = [m for m in msgs if m]
            dlg.destroy()
            self.refresh()
            if bad:
                d = Gtk.MessageDialog(transient_for=self.win, modal=True, message_type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK, text="Nem tudo foi importado")
                d.format_secondary_text("\n".join(bad))
                d.run()
                d.destroy()
        else:
            dlg.destroy()

    def import_file(self, path):
        stem, ext = os.path.splitext(os.path.basename(path))
        ext = ext.lower()
        name = slug(stem)
        base = os.path.join(LIB, name)
        k = 2
        while os.path.exists(base):
            base, k = os.path.join(LIB, f"{name}-{k}"), k + 1
        os.makedirs(base)
        fname = os.path.basename(path)
        if ext in VIDEO:
            shutil.copy2(path, os.path.join(base, fname))
            m = {"type": "video", "file": fname, "parallax": 0.03, "fps": 30}
        elif ext in IMAGE:
            shutil.copy2(path, os.path.join(base, fname))
            m = {"type": "image", "file": fname, "parallax": 0.04}
        elif ext in SHADER:
            src = open(path, errors="replace").read()
            if "mainImage" not in src:
                shutil.rmtree(base)
                return f"{os.path.basename(path)}: o shader precisa ter void mainImage(out vec4 fragColor, in vec2 fragCoord) (formato Shadertoy)."
            shutil.copy2(path, os.path.join(base, fname))
            m = {"type": "shader", "shader": fname, "speed": 1.0}
        else:
            shutil.rmtree(base)
            return f"{os.path.basename(path)}: formato não suportado."
        save_manifest(os.path.basename(base), m)
        return None


if __name__ == "__main__":
    GLib.set_prgname("entropy-wall-ui")
    os.makedirs(LIB, exist_ok=True)
    UI()
    Gtk.main()
