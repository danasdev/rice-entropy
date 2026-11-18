#!/usr/bin/env python3
"""Menu de apps Entropy (Super+Space): busca, grade/lista, categorias, calculadora, comando, web e clipboard."""
import cairo, math, importlib.util, json, os, re, signal, subprocess, sys, time, unicodedata, urllib.parse
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("entropy_cc", os.path.join(HERE, "entropy-cc.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
sc, PAL, sh, fire, bg = cc.sc, cc.PAL, cc.sh, cc.fire, cc.bg

RT = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PIDF, MONF, OPENF = (os.path.join(RT, n) for n in ("entropy-launcher.pid", "entropy-cc.mon", "entropy-launcher.open"))
RECENT = os.path.expanduser("~/.cache/entropy-cc/launcher_recent.json")
G = {k: chr(v) for k, v in dict(search=0xF0349, grid=0xF0570, list=0xF0572, calc=0xF00EC, term=0xF018D, web=0xF01E7,
                                clip=0xF0147, back=0xF0141, apps=0xF003B).items()}
CATS = [("Network", "Internet", 0xF01E7), ("Development", "Desenvolvimento", 0xF0169), ("AudioVideo", "Mídia", 0xF0386),
        ("Audio", "Mídia", 0xF0386), ("Video", "Mídia", 0xF0386), ("Game", "Jogos", 0xF0297), ("Office", "Escritório", 0xF0219),
        ("Graphics", "Gráficos", 0xF02E9), ("Education", "Educação", 0xF0474), ("Settings", "Sistema", 0xF0493),
        ("System", "Sistema", 0xF0493), ("Utility", "Utilitários", 0xF05B7)]

EXTRA_CSS = f"""
.search {{ background: rgba(255,255,255,0.08); border: 1.5px solid rgba(255,255,255,0.16); border-radius: 20px; padding: 0px 14px 0px 18px; min-height: 58px; }}
.search.focus {{ border-color: {cc.ACC}; box-shadow: 0 0 22px rgba(183,156,255,0.30); background: rgba(255,255,255,0.10); }}
.search label.sg {{ font-family: '{cc.NF}'; font-size: 20px; color: {cc.ACC}; }}
.search label.hint {{ font-family: Inter, sans-serif; font-size: 16px; color: rgba(255,255,255,0.5); }}
.search entry {{ background: none; border: none; box-shadow: none; padding: 4px 8px; font-size: 17px; min-height: 24px; }}
.kbd {{ background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.16); border-radius: 7px; padding: 2px 8px; }}
.kbd label {{ font-family: '{cc.NF}'; font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.62); }}
.tab {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 999px; padding: 6px 16px; }}
.tab label {{ font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.75); }}
.tabx {{ padding: 6px 2px 0px 2px; border-radius: 8px; }}
.tabx label.tl {{ font-size: 15px; font-weight: 500; color: rgba(255,255,255,0.55); }}
.tabx:hover label.tl {{ color: rgba(255,255,255,0.88); }}
.tabx.on label.tl {{ font-weight: 700; color: {PAL['fg']}; }}
.cnt {{ background: rgba(255,255,255,0.08); border-radius: 999px; padding: 1px 7px; }}
.cnt label {{ font-family: '{cc.NF}'; font-size: 11px; color: rgba(255,255,255,0.5); }}
.tabx.on .cnt {{ background: rgba(183,156,255,0.22); }}
.tabx.on .cnt label {{ color: {cc.ACC}; }}
.uline {{ min-height: 3px; border-radius: 2px; background: transparent; }}
.tabx.on .uline {{ background-image: linear-gradient(90deg, {cc.ACC}, {cc.ACC2}); box-shadow: 0 0 10px rgba(183,156,255,0.7); }}
.hair {{ min-height: 1px; background-image: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.16), rgba(255,255,255,0)); }}
.seclbl {{ font-family: '{cc.NF}'; font-size: 11px; font-weight: 600; letter-spacing: 2px; color: {cc.ACC}; }}
.seccnt {{ font-family: '{cc.NF}'; font-size: 11px; color: rgba(255,255,255,0.42); }}
.cell {{ border-radius: 22px; padding: 12px 4px 10px 4px; border: 1px solid transparent; }}
.cell:hover {{ background-color: rgba(255,255,255,0.07); }}
.cell.sel {{ background-image: linear-gradient(180deg, rgba(183,156,255,0.20), rgba(127,178,255,0.06)); border-color: rgba(183,156,255,0.55); box-shadow: 0 10px 28px rgba(183,156,255,0.28); }}
.plate {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.14); border-radius: 19px; min-width: 64px; min-height: 64px; }}
.plate.sm {{ min-width: 44px; min-height: 44px; border-radius: 14px; }}
.cell:hover .plate {{ border-color: rgba(255,255,255,0.32); }}
.cell.sel .plate {{ background-image: linear-gradient(135deg, rgba(183,156,255,0.34), rgba(127,178,255,0.14)); border-color: rgba(183,156,255,0.9); }}
.cell label.cn {{ font-size: 12.5px; font-weight: 500; color: rgba(255,255,255,0.78); }}
.cell.sel label.cn {{ font-weight: 700; color: {PAL['fg']}; }}
.cell label.nfi {{ font-family: '{cc.NF}'; font-size: 28px; color: {cc.ACC}; }}
.fdot {{ background: {cc.ACC}; border-radius: 999px; min-width: 8px; min-height: 8px; box-shadow: 0 0 8px {cc.ACC}; }}
.fname {{ font-size: 14px; font-weight: 700; }}
.fcat {{ background: rgba(255,255,255,0.08); border-radius: 999px; padding: 2px 9px; }}
.fcat label {{ font-family: '{cc.NF}'; font-size: 10px; letter-spacing: 1px; color: rgba(255,255,255,0.7); }}
.fdesc {{ font-size: 13px; color: rgba(255,255,255,0.5); }}
.fhint {{ font-size: 12px; color: rgba(255,255,255,0.55); }}
"""


def make_css(tint):
    out = cc.make_css(tint)
    extra = EXTRA_CSS
    fg, pr, se = (cc.hex2rgb(PAL[k]) for k in ("fg", "primary", "secondary"))
    extra = extra.replace("rgba(255,255,255,", f"rgba({fg[0]},{fg[1]},{fg[2]},")
    extra = extra.replace("rgba(183,156,255,", f"rgba({pr[0]},{pr[1]},{pr[2]},").replace("rgba(127,178,255,", f"rgba({se[0]},{se[1]},{se[2]},")
    extra = re.sub(r"(\d+(?:\.\d+)?)px", lambda m: f"{max(1, round(float(m.group(1)) * cc.S))}px", extra)
    return out + extra


def load_recent():
    try:
        return json.load(open(RECENT))
    except Exception:
        return {}


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def main_cat(app):
    cats = (app.get_categories() or "").split(";")
    for key, label, glyph in CATS:
        if key in cats:
            return label
    return "Outros"


class Launcher:
    RES = 84   # espaço reservado embaixo (dock + respiro); o painel fica logo acima

    snapshot = cc.Panel.snapshot
    on_anim_draw = cc.Panel.on_anim_draw_rect
    def run_anim(self, opening, dur, done):
        t0 = GLib.get_monotonic_time()
        dur = dur * float(os.environ.get("ENTROPY_ANIM_SLOW", "1")) * 1.25

        def step():
            r = min(1.0, (GLib.get_monotonic_time() - t0) / (dur * 1e6))
            if opening:
                sm = r * r * (3 - 2 * r)
                self.anim_p = sm + 0.045 * math.sin(math.pi * max(0.0, (r - 0.55) / 0.45))
            else:
                self.anim_p = 1.0 - r * r * (3 - 2 * r)
            self.anim_area.queue_draw()
            if r >= 1.0:
                done()
                return False
            return True
        GLib.timeout_add(16, step)
    prepare_morph = cc.Panel.prepare_morph_rect
    morph_target = cc.Panel.morph_target_rect
    rrect = staticmethod(cc.Panel.rrect)
    smoothstep = staticmethod(cc.Panel.smoothstep)

    def __init__(self, daemon):
        self.daemon, self.visible, self.closing, self.ready = daemon, False, False, False
        self.view, self.tab, self.cat = "grid", "recent", None
        self.cells, self.items, self.sel = [], [], 0
        self.recent = load_recent()
        self.snap, self.anim_p = None, 0.0
        self.mon_name, self.mon_x, self.mon_y, self.mon_w, self.mon_h = None, 0, 0, 1280, 720
        self.apps = []
        self.clip_cache = []
        self.build()
        if not daemon:
            self.open_launcher()

    # ---------- janela ----------
    def build(self):
        win = self.win = Gtk.Window()
        win.set_app_paintable(True)
        vis = win.get_screen().get_rgba_visual()
        if vis:
            win.set_visual(vis)
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "entropy-launcher")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.BOTTOM, 0)
        try:
            a = float(open(cc.ALPHA).read().strip())
        except Exception:
            a = 0.38
        su_ = cc.hex2rgb(PAL["surface"])
        self.morph_rgba = (su_[0] / 255, su_[1] / 255, su_[2] / 255, min(0.80, 0.40 + (a - 0.38) * 0.8))
        self.fg_rgb = tuple(c / 255 for c in cc.hex2rgb(PAL["fg"]))
        prov = Gtk.CssProvider()
        prov.load_from_data(make_css(min(0.78, 0.30 + (a - 0.38) * 0.9)).encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = self.outer = Gtk.Box()
        for side, v in (("start", 6), ("end", 6), ("top", 6), ("bottom", self.RES)):
            getattr(outer, f"set_margin_{side}")(v)
        self.wstack = Gtk.Stack()
        self.anim_area = Gtk.DrawingArea()
        self.anim_area.connect("draw", self.on_anim_draw)
        self.wstack.add_named(outer, "real")
        self.wstack.add_named(self.anim_area, "anim")
        win.add(self.wstack)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.get_style_context().add_class("panel")
        panel.set_size_request(sc(860), -1)
        outer.pack_start(panel, True, True, 0)
        self.morph_widget = panel
        pad = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sc(11))
        for side in ("start", "end", "top", "bottom"):
            getattr(pad, f"set_margin_{side}")(sc(20))
        panel.pack_start(pad, True, True, 0)

        row = Gtk.Box(spacing=sc(10))
        sbox = Gtk.Box(spacing=sc(8))
        sbox.get_style_context().add_class("search")
        gl = Gtk.Label(label=G["search"])
        gl.get_style_context().add_class("sg")
        sbox.get_style_context().add_class("focus")
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.ph = Gtk.Label(label="Buscar apps, calcular (=), executar (>) ou pesquisar na web…", xalign=0)
        self.ph.get_style_context().add_class("hint")
        self.ph.set_halign(Gtk.Align.START)
        self.ph.set_margin_start(sc(8))
        ov = Gtk.Overlay()
        ov.add(self.entry)
        ov.add_overlay(self.ph)
        ov.set_overlay_pass_through(self.ph, True)
        self.entry.connect("changed", lambda *_: (self.ph.set_visible(not self.entry.get_text()), self.refresh()))
        sbox.pack_start(gl, False, False, 0)
        sbox.pack_start(ov, True, True, 0)
        for kk in ("Tab", "Esc"):
            kb = Gtk.Box()
            kb.get_style_context().add_class("kbd")
            kb.set_valign(Gtk.Align.CENTER)
            kb.pack_start(Gtk.Label(label=kk), False, False, 0)
            sbox.pack_start(kb, False, False, 0)
        row.pack_start(sbox, True, True, 0)
        self.view_btn = self.ibtn("list", self.toggle_view, "Alternar grade/lista")
        row.pack_start(self.view_btn, False, False, 0)
        row.pack_start(self.ibtn("cog", lambda: (fire("noctalia", "msg", "settings-open"), self.close()), "Configurações"), False, False, 0)
        row.pack_start(self.ibtn("power", lambda: (fire(os.path.join(HERE, "entropy-cc-toggle"), "", "session"), self.close()), "Sessão"), False, False, 0)
        pad.pack_start(row, False, False, 0)

        tabs = Gtk.Box(spacing=sc(22))
        self.tab_btns, self.tab_cnt = {}, {}
        for key, text in (("recent", "Recentes"), ("all", "Todos"), ("cats", "Categorias"), ("clip", "Clipboard")):
            b = Gtk.Button()
            b.get_style_context().add_class("tabx")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sc(8))
            h = Gtk.Box(spacing=sc(8))
            tl = Gtk.Label(label=text)
            tl.get_style_context().add_class("tl")
            cnt = Gtk.Box()
            cnt.get_style_context().add_class("cnt")
            cl = Gtk.Label(label="–")
            cnt.pack_start(cl, False, False, 0)
            h.pack_start(tl, False, False, 0)
            h.pack_start(cnt, False, False, 0)
            ul = Gtk.Box()
            ul.get_style_context().add_class("uline")
            v.pack_start(h, False, False, 0)
            v.pack_start(ul, False, False, 0)
            b.add(v)
            b.connect("clicked", lambda _b, k=key: self.set_tab(k))
            self.tab_btns[key] = b
            self.tab_cnt[key] = cl
            tabs.pack_start(b, False, False, 0)
        self.back_btn = Gtk.Button()
        self.back_btn.get_style_context().add_class("tab")
        self.back_btn.add(Gtk.Label(label=G["back"] + "  Categorias"))
        self.back_btn.connect("clicked", lambda *_: self.set_cat(None))
        self.back_btn.set_no_show_all(True)
        tabs.pack_start(self.back_btn, False, False, 0)
        pad.pack_start(tabs, False, False, 0)
        hair = Gtk.Box()
        hair.get_style_context().add_class("hair")
        pad.pack_start(hair, False, False, 0)

        secrow = Gtk.Box(spacing=sc(12))
        self.sec_lbl = Gtk.Label(label="RECENTES")
        self.sec_lbl.get_style_context().add_class("seclbl")
        sh_ = Gtk.Box()
        sh_.get_style_context().add_class("hair")
        sh_.set_valign(Gtk.Align.CENTER)
        self.sec_cnt = Gtk.Label(label="")
        self.sec_cnt.get_style_context().add_class("seccnt")
        secrow.pack_start(self.sec_lbl, False, False, 0)
        secrow.pack_start(sh_, True, True, 0)
        secrow.pack_start(self.sec_cnt, False, False, 0)
        pad.pack_start(secrow, False, False, 0)

        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_shadow_type(Gtk.ShadowType.NONE)
        self.scroll.set_size_request(-1, sc(360))
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_row_spacing(sc(6))
        self.flow.set_column_spacing(sc(6))
        self.flow.set_valign(Gtk.Align.START)
        self.scroll.add(self.flow)
        pad.pack_start(self.scroll, True, True, 0)

        foot = Gtk.Box(spacing=sc(12))
        dot = Gtk.Box()
        dot.get_style_context().add_class("fdot")
        dot.set_valign(Gtk.Align.CENTER)
        self.f_name = Gtk.Label(label="", xalign=0)
        self.f_name.get_style_context().add_class("fname")
        catb = Gtk.Box()
        catb.get_style_context().add_class("fcat")
        catb.set_valign(Gtk.Align.CENTER)
        self.f_cat = Gtk.Label(label="")
        catb.pack_start(self.f_cat, False, False, 0)
        self.f_desc = Gtk.Label(label="", xalign=0)
        self.f_desc.get_style_context().add_class("fdesc")
        self.f_desc.set_ellipsize(3)
        self.f_desc.set_max_width_chars(30)
        foot.pack_start(dot, False, False, 0)
        foot.pack_start(self.f_name, False, False, 0)
        foot.pack_start(catb, False, False, 0)
        foot.pack_start(self.f_desc, True, True, 0)
        for kk, ll in (("↵", "abrir"), ("Tab", "aba"), ("Esc", "fechar")):
            hb = Gtk.Box(spacing=sc(6))
            kb = Gtk.Box()
            kb.get_style_context().add_class("kbd")
            kb.set_valign(Gtk.Align.CENTER)
            kb.pack_start(Gtk.Label(label=kk), False, False, 0)
            lb = Gtk.Label(label=ll)
            lb.get_style_context().add_class("fhint")
            hb.pack_start(kb, False, False, 0)
            hb.pack_start(lb, False, False, 0)
            foot.pack_start(hb, False, False, 0)
        pad.pack_start(foot, False, False, 0)

        win.connect("key-press-event", self.on_key)
        win.set_opacity(0.0)
        self.wstack.show_all()
        self.back_btn.hide()

    def ibtn(self, key, cb, tip):
        b = Gtk.Button()
        b.get_style_context().add_class("round")
        b.add(Gtk.Label(label=G.get(key) or cc.I.get(key, "?")))
        b.set_tooltip_text(tip)
        b.connect("clicked", lambda *_: cb())
        return b

    # ---------- abrir / fechar ----------
    def pick_monitor(self, want):
        disp = Gdk.Display.get_default()
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
            foc = next((m for m in mons if m["name"] == want), None) or next((m for m in mons if m.get("focused")), mons[0])
            self.mon_name, self.mon_x, self.mon_y = foc["name"], int(foc["x"]), int(foc["y"])
            self.mon_w, self.mon_h = int(foc["width"] / foc["scale"]), int(foc["height"] / foc["scale"])
            for i in range(disp.get_n_monitors()):
                gm = disp.get_monitor(i).get_geometry()
                if gm.x == int(foc["x"]) and gm.y == int(foc["y"]):
                    GtkLayerShell.set_monitor(self.win, disp.get_monitor(i))
                    return
        except Exception:
            pass

    def write_state(self, on):
        try:
            open(OPENF, "w").write("1" if on else "0")
        except OSError:
            pass

    def open_launcher(self, monitor=None):
        if self.visible:
            return
        self.visible, self.closing, self.ready = True, False, False
        self.write_state(True)
        self.pick_monitor(monitor)
        self.recent = load_recent()
        self.apps = self.read_apps()
        self.cat = None
        self.entry.set_text(os.environ.get("ENTROPY_LAUNCHER_Q", ""))
        self.tab = "recent" if self.recent else "all"
        self.wstack.set_visible_child_name("real")
        self.win.set_opacity(0.0)
        self.set_tab(self.tab, focus=False)
        self.win.show()
        self.back_btn.hide()
        self.entry.grab_focus()
        GLib.timeout_add(90, self.anim_open)

    def morph_origin(self):
        W, H = self.outer.get_allocated_width(), self.outer.get_allocated_height()
        cx, cy = W / 2.0, H - 34.0
        try:
            layers = json.loads(sh("hyprctl", "layers", "-j"))
            dock = None
            for lv in layers.get(self.mon_name, {}).get("levels", {}).values():
                for l in lv:
                    if (l["namespace"] == "noctalia-dock" and l["h"] > 20
                            and l["y"] + l["h"] <= self.mon_y + self.mon_h + 2 and l["y"] < self.mon_y + self.mon_h - 40):
                        dock = l
            if dock:
                gx, gy = dock["x"] + 77, dock["y"] + dock["h"] - 37
                cx = gx - (self.mon_x + (self.mon_w - W) / 2.0)
                cy = gy - (self.mon_y + self.mon_h - H)
        except Exception:
            pass
        return (cx - 23.0, cy - 23.0, 46.0, 46.0, 15.0)

    def set_input(self, empty=False):
        try:
            if empty:
                reg = cairo.Region()
            else:
                tx, ty, tw, th, _r = self.target
                reg = cairo.Region(cairo.RectangleInt(int(tx), int(ty), int(tw) + 1, int(th) + 1))
            self.win.get_window().input_shape_combine_region(reg, 0, 0)
        except Exception:
            pass

    def anim_open(self):
        try:
            self.prepare_morph()
            self.set_input(empty=True)
            self.anim_p = 0.0
            self.wstack.set_visible_child_name("anim")
            self.win.set_opacity(1.0)

            def done():
                self.wstack.set_visible_child_name("real")
                self.set_input()
                self.entry.grab_focus()
                self.ready = True
            self.run_anim(True, 0.52, done)
        except Exception as e:
            print("anim_open:", repr(e), flush=True)
            self.win.set_opacity(1.0)
            self.ready = True
        return False

    def close(self):
        if self.closing or not self.visible:
            return
        self.closing = True
        try:
            self.prepare_morph()
            self.set_input(empty=True)
            self.anim_p = 1.0
            self.wstack.set_visible_child_name("anim")
            self.run_anim(False, 0.36, self.after_close)
        except Exception:
            self.after_close()

    def after_close(self):
        self.write_state(False)
        if self.daemon:
            self.win.hide()
            self.visible = self.closing = False
        else:
            Gtk.main_quit()

    # ---------- dados ----------
    def read_apps(self):
        out = []
        for a in Gio.AppInfo.get_all():
            if not a.should_show() or a.get_id() == "entropy-apps.desktop":
                continue
            gen = a.get_generic_name() if hasattr(a, "get_generic_name") else ""
            kws = " ".join(a.get_keywords() or []) if hasattr(a, "get_keywords") else ""
            out.append({"kind": "app", "id": a.get_id(), "name": a.get_name() or "", "desc": a.get_description() or gen or "",
                        "icon": a.get_icon(), "app": a, "cat": main_cat(a),
                        "kw": norm(" ".join(filter(None, [gen, kws, a.get_executable() or ""])))})
        out.sort(key=lambda x: norm(x["name"]))
        return out

    def score(self, it, q):
        n = norm(it["name"])
        if n.startswith(q):
            return 100
        if re.search(r"\b" + re.escape(q), n):
            return 80
        if q in n:
            return 60
        if q in it["kw"] or q in norm(it.get("desc")):
            return 35
        i = 0
        for ch in n:
            if i < len(q) and ch == q[i]:
                i += 1
        return 8 if i == len(q) and len(q) >= 3 else 0

    def providers(self, q):
        out = []
        raw = q.strip()
        if raw.startswith(">") or raw.startswith("$"):
            cmd = raw[1:].strip()
            if cmd:
                out.append({"kind": "cmd", "name": f"Executar: {cmd}", "desc": "Abre no terminal", "gl": G["term"], "arg": cmd})
            return out, True
        expr = raw[1:] if raw.startswith("=") else raw
        if re.fullmatch(r"[0-9+\-*/().,%^ x×÷]+", expr) and re.search(r"\d", expr) and re.search(r"[+\-*/%^x×÷]", expr):
            try:
                e = expr.replace(",", ".").replace("^", "**").replace("x", "*").replace("×", "*").replace("÷", "/")
                val = eval(e, {"__builtins__": {}}, {})
                txt = f"{val:.10g}" if isinstance(val, float) else str(val)
                out.append({"kind": "calc", "name": f"= {txt}", "desc": f"{expr.strip()}  ·  clique para copiar", "gl": G["calc"], "arg": txt})
            except Exception:
                pass
        return out, False

    def refresh(self):
        q = norm(self.entry.get_text()).strip()
        self.cat = self.cat if not q else None
        if q:
            extra, only = self.providers(q)
            scored = [] if only else sorted(((self.score(it, q), it) for it in self.apps), key=lambda t: -t[0])
            best = scored[0][0] if scored else 0
            cut = 30 if best >= 30 else 1
            items = extra + [it for s, it in scored if s >= cut][:60]
            if not only and not any(i["kind"] == "app" for i in items):
                items.append({"kind": "web", "name": f"Pesquisar na web: {self.entry.get_text().strip()}", "desc": "Abre no navegador", "gl": G["web"],
                              "arg": "https://www.google.com/search?q=" + urllib.parse.quote(self.entry.get_text().strip())})
            self.show(items, grid=self.view == "grid" and any(i["kind"] == "app" for i in items))
            return
        if self.tab == "recent":
            order = sorted(self.recent.items(), key=lambda kv: -kv[1].get("t", 0))
            byid = {a["id"]: a for a in self.apps}
            items = [byid[k] for k, _ in order if k in byid][:18]
            if not items:
                items = self.apps[:18]
        elif self.tab == "all":
            items = self.apps
        elif self.tab == "cats":
            if self.cat is None:
                counts = {}
                for a in self.apps:
                    counts[a["cat"]] = counts.get(a["cat"], 0) + 1
                gm = {label: glyph for _k, label, glyph in CATS}
                items = [{"kind": "cat", "name": c, "desc": f"{n} apps", "gl": chr(gm.get(c, 0xF003B)), "arg": c} for c, n in sorted(counts.items())]
            else:
                items = [a for a in self.apps if a["cat"] == self.cat]
        else:
            self.show_clip()
            return
        self.show(items, grid=self.view == "grid")

    def show_clip(self):
        def load():
            return sh("cliphist", "list", timeout=4).splitlines()[:40]

        def done(lines):
            if self.tab != "clip":
                return
            items = []
            for ln in lines:
                cid, _, txt = ln.partition("\t")
                if "binary data" in txt:
                    txt = "[imagem]"
                items.append({"kind": "clip", "name": txt.strip()[:90] or "(vazio)", "desc": "clique para copiar de novo", "gl": G["clip"], "arg": cid})
            if not items:
                items = [{"kind": "none", "name": "Histórico vazio", "desc": "", "gl": G["clip"], "arg": ""}]
            self.show(items, grid=False)
        bg(load, done)

    # ---------- exibição ----------
    def show(self, items, grid):
        for c in self.flow.get_children():
            self.flow.remove(c)
        self.items, self.cells, self.sel = items, [], 0
        cols = 6 if grid else 1
        self.flow.set_min_children_per_line(cols)
        self.flow.set_max_children_per_line(cols)
        for it in items:
            b = self.cell(it, grid)
            self.cells.append(b)
            self.flow.add(b)
        names = {"recent": "RECENTES", "all": "TODOS", "cats": "CATEGORIAS", "clip": "CLIPBOARD"}
        q = self.entry.get_text().strip()
        self.sec_lbl.set_text("RESULTADOS" if q else (self.cat.upper() if (self.tab == "cats" and self.cat) else names.get(self.tab, "")))
        self.sec_cnt.set_text(f"{len(items)} {'itens' if self.tab == 'clip' and not q else 'apps'}")
        self.flow.show_all()
        self.cols = cols
        if self.cells:
            self.set_sel(0)

    def cell(self, it, grid):
        b = Gtk.Button()
        b.get_style_context().add_class("cell")
        if it["kind"] == "app" and it.get("icon") is not None:
            img = Gtk.Image.new_from_gicon(it["icon"], Gtk.IconSize.DIALOG)
            img.set_pixel_size(sc(36) if grid else sc(26))
        else:
            img = Gtk.Label(label=it.get("gl", "?"))
            img.get_style_context().add_class("nfi")
        plate = Gtk.Box()
        plate.get_style_context().add_class("plate")
        if not grid:
            plate.get_style_context().add_class("sm")
        plate.set_halign(Gtk.Align.CENTER)
        plate.set_valign(Gtk.Align.CENTER)
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        img.set_hexpand(True)
        plate.pack_start(img, True, True, 0)
        if grid:
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sc(7))
            v.pack_start(plate, False, False, 0)
            lb = Gtk.Label(label=it["name"])
            lb.set_ellipsize(3)
            lb.set_max_width_chars(11)
            lb.get_style_context().add_class("cn")
            v.pack_start(lb, False, False, 0)
            b.add(v)
        else:
            h = Gtk.Box(spacing=sc(14))
            h.set_margin_start(sc(8))
            h.pack_start(plate, False, False, 0)
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            col.set_valign(Gtk.Align.CENTER)
            n = Gtk.Label(label=it["name"], xalign=0)
            n.set_ellipsize(3)
            n.set_max_width_chars(48)
            n.get_style_context().add_class("tname")
            col.pack_start(n, False, False, 0)
            if it.get("desc"):
                d = Gtk.Label(label=it["desc"], xalign=0)
                d.set_ellipsize(3)
                d.set_max_width_chars(60)
                d.get_style_context().add_class("small")
                col.pack_start(d, False, False, 0)
            h.pack_start(col, True, True, 0)
            b.add(h)
        b.connect("clicked", lambda *_: self.activate(it))
        return b

    def set_sel(self, i):
        if not self.cells:
            return
        self.sel = max(0, min(len(self.cells) - 1, i))
        for j, b in enumerate(self.cells):
            ctx = b.get_style_context()
            (ctx.add_class if j == self.sel else ctx.remove_class)("sel")
        b = self.cells[self.sel]
        GLib.idle_add(self.reveal, b)
        it = self.items[self.sel]
        self.f_name.set_text(it["name"][:40])
        kind = {"app": it.get("cat", "APP"), "calc": "CÁLCULO", "cmd": "COMANDO", "web": "WEB", "clip": "CLIPBOARD", "cat": "CATEGORIA"}.get(it["kind"], "")
        self.f_cat.set_text(str(kind).upper())
        self.f_desc.set_text(it.get("desc") or "")

    def reveal(self, b):
        al = b.get_allocation()
        va = self.scroll.get_vadjustment()
        if al.y < va.get_value():
            va.set_value(al.y)
        elif al.y + al.height > va.get_value() + va.get_page_size():
            va.set_value(al.y + al.height - va.get_page_size())
        return False

    def set_tab(self, key, focus=True):
        self.tab = key
        self.cat = None
        for k, b in self.tab_btns.items():
            ctx = b.get_style_context()
            (ctx.add_class if k == key else ctx.remove_class)("on")
        self.back_btn.hide()
        self.entry.set_text("") if focus and self.entry.get_text() else None
        self.refresh()
        if focus:
            self.entry.grab_focus()

    def set_cat(self, cat):
        self.cat = cat
        self.tab = "cats"
        for k, b in self.tab_btns.items():
            ctx = b.get_style_context()
            (ctx.add_class if k == "cats" else ctx.remove_class)("on")
        (self.back_btn.show if cat else self.back_btn.hide)()
        self.refresh()

    def toggle_view(self):
        self.view = "list" if self.view == "grid" else "grid"
        self.view_btn.get_child().set_text(G["list"] if self.view == "grid" else G["grid"])
        self.refresh()
        self.entry.grab_focus()

    # ---------- ações ----------
    def activate(self, it):
        k = it["kind"]
        if k == "cat":
            self.set_cat(it["arg"])
            return
        if k == "none":
            return
        if k == "app":
            rec = self.recent.setdefault(it["id"], {"n": 0, "t": 0})
            rec["n"] += 1
            rec["t"] = time.time()
            try:
                os.makedirs(os.path.dirname(RECENT), exist_ok=True)
                json.dump(self.recent, open(RECENT, "w"))
            except OSError:
                pass
            fn = it["app"].get_filename()
            if fn:
                fire("gio", "launch", fn)
            else:
                it["app"].launch([], None)
        elif k == "cmd":
            fire("kitty", "sh", "-c", it["arg"] + "; echo; read -n1 -p 'Enter para fechar'")
        elif k == "web":
            fire("xdg-open", it["arg"])
        elif k == "calc":
            fire("wl-copy", it["arg"])
        elif k == "clip":
            fire("sh", "-c", f"cliphist decode {it['arg']} | wl-copy")
        self.close()

    def on_key(self, w, e):
        kv = e.keyval
        if kv == Gdk.KEY_Escape:
            self.close()
            return True
        if kv in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.items:
                self.activate(self.items[self.sel])
            return True
        step = {Gdk.KEY_Down: self.cols, Gdk.KEY_Up: -self.cols, Gdk.KEY_Right: 1, Gdk.KEY_Left: -1}.get(kv) if hasattr(self, "cols") else None
        if step is not None and not (kv in (Gdk.KEY_Left, Gdk.KEY_Right) and self.cols == 1):
            self.set_sel(self.sel + step)
            return True
        if kv == Gdk.KEY_Tab:
            order = ["recent", "all", "cats", "clip"]
            self.set_tab(order[(order.index(self.tab) + 1) % 4])
            return True
        return False


def main():
    daemon = "--daemon" in sys.argv
    if daemon:
        try:
            os.kill(int(open(PIDF).read()), 0)
            sys.exit(0)
        except Exception:
            pass
    open(PIDF, "w").write(str(os.getpid()))
    app = Launcher(daemon)

    def mon():
        try:
            return open(MONF).read().strip() or None
        except OSError:
            return None

    def toggle():
        if daemon:
            app.close() if app.visible else app.open_launcher(mon())
        else:
            app.close()
        return True
    if daemon and "--open" in sys.argv:
        GLib.idle_add(lambda: (app.open_launcher(mon()), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, toggle)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    try:
        os.remove(PIDF)
    except OSError:
        pass


if __name__ == "__main__":
    main()
