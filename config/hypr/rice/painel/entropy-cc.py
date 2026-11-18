#!/usr/bin/env python3
"""Painel de controle Entropy (Super+S): vidro, controles diretos e páginas internas para cada seção."""
import calendar, datetime, json, math, os, platform, re, shutil, signal, subprocess, sys, threading, time
import cairo, hashlib
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell

S = 0.74  # escala do desenho do Figma (860px) para o monitor real
NF = "JetBrainsMono Nerd Font"


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette():
    d = {"primary": "#B79CFF", "secondary": "#7FB2FF", "tertiary": "#F472B6", "surface": "#16102E", "fg": "#FFFFFF"}
    try:
        for line in open(os.path.expanduser("~/.config/hypr/noctalia.conf")):
            m = re.match(r"\$(primary|secondary|tertiary|surface)\s*=\s*rgb\(([0-9a-fA-F]{6})\)", line)
            if m:
                d[m.group(1)] = "#" + m.group(2)
        for line in open(os.path.expanduser("~/.config/kitty/themes/noctalia.conf")):
            m = re.match(r"foreground\s+(#[0-9a-fA-F]{6})", line)
            if m:
                d["fg"] = m.group(1)
    except Exception:
        pass
    r, g_, b = hex2rgb(d["primary"])
    d["on_acc"] = "#10121a" if (0.299 * r + 0.587 * g_ + 0.114 * b) > 140 else "#ffffff"
    return d


PAL = palette()
ACC, ACC2 = PAL["primary"], PAL["secondary"]
STATE = os.path.expanduser("~/.cache/entropy-cc/state.json")
ALPHA = os.path.expanduser("~/.cache/glass-adaptive/alpha")
DATA = os.path.expanduser("~/.local/share/entropy/data.json")
WEATHER = os.path.expanduser("~/.cache/noctalia/weather.json")
WALLS = os.path.expanduser("~/Pictures/Wallpapers")
THUMBS = os.path.expanduser("~/.cache/entropy-cc/thumbs")
CACHE = os.path.expanduser("~/.cache/entropy-cc/last.json")
NOTIFS = os.path.expanduser("~/.local/state/noctalia/notification_history.json")
def _user_name():
    try:
        custom = open(os.path.expanduser("~/.config/entropy-name")).read().strip()
        if custom:
            return custom
    except OSError:
        pass
    try:
        import pwd
        full = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0].strip()
        if full:
            return full.split()[0]
    except Exception:
        pass
    return os.environ.get("USER", "").capitalize() or "você"


USER_NAME = _user_name()
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
PERFIS = {"power-saver": "Economia", "balanced": "Equilibrado", "performance": "Performance"}


def sc(n):
    return max(1, round(n * S))


I = {k: chr(v) for k, v in dict(
    wifi=0xF05A9, w1=0xF091F, w2=0xF0922, w3=0xF0925, w4=0xF0928, bt=0xF00AF, dnd=0xF009B, night=0xF0594,
    coffee=0xF06CA, perf=0xF04C5, vol=0xF057E, mute=0xF0581, mic=0xF036C, micoff=0xF036D, bri=0xF00DF,
    power=0xF0425, play=0xF040A, pause=0xF03E4, prev=0xF04AE, next=0xF04AD, lock=0xF033E, sleep=0xF0904,
    cog=0xF0493, close=0xF0156, bat=0xF0079, home=0xF02DC, music=0xF0386, monitor=0xF0379, system=0xF035B,
    batt=0xF0084, weather=0xF0599, cal=0xF00ED, bell=0xF009A, check=0xF012C, left=0xF0141, right=0xF0142,
    logout=0xF0343, reboot=0xF0709, trash=0xF01B4, sun=0xF0599, pcloud=0xF0595, fog=0xF0591, rain=0xF0597,
    snow=0xF0598, bolt=0xF0593, scan=0xF0450, headset=0xF02CB, speaker=0xF04C3, img=0xF02E9).items()}
TABS = [("home", "home", "Início"), ("music", "media", "Mídia"), ("vol", "audio", "Áudio"), ("monitor", "display", "Display"), ("img", "wallpaper", "Papel de parede"),
        ("system", "system", "Sistema"), ("batt", "power", "Energia"), ("wifi", "network", "Rede"),
        ("bt", "bluetooth", "Bluetooth"), ("weather", "weather", "Clima"), ("cal", "calendar", "Calendário"),
        ("bell", "notifications", "Notificações")]


def sh(*cmd, timeout=4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def fire(*cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def bg(fn, cb=None):
    def run():
        r = fn()
        if cb:
            GLib.idle_add(lambda: (cb(r), False)[1])
    threading.Thread(target=run, daemon=True).start()


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def save_state(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(d, open(STATE, "w"))


def wicon(code):
    if code == 0: return I["sun"], "Limpo"
    if code in (1, 2, 3): return I["pcloud"], "Poucas nuvens" if code < 3 else "Nublado"
    if code in (45, 48): return I["fog"], "Neblina"
    if code in (51, 53, 55, 56, 57): return I["rain"], "Garoa"
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return I["rain"], "Chuva"
    if code in (71, 73, 75, 77, 85, 86): return I["snow"], "Neve"
    if code >= 95: return I["bolt"], "Tempestade"
    return I["pcloud"], "Nuvens"


CSS = f"""
window {{ background: transparent; }}
.panelx {{ background: none; border: none; }}
.panel {{ background-color: rgba(22,16,46,TINT); border: 1px solid rgba(255,255,255,0.20); border-radius: 36px; }}
label {{ color: #fff; }}
.title {{ font-size: 24px; font-weight: 700; }}
.h2 {{ font-size: 20px; font-weight: 700; }}
.big {{ font-size: 54px; font-weight: 700; }}
.sub {{ font-size: 14px; color: rgba(255,255,255,0.62); }}
.small {{ font-size: 12px; color: rgba(255,255,255,0.58); }}
.nf {{ font-family: '{NF}'; }}
.pill {{ background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.16); border-radius: 999px; padding: 8px 14px; }}
.pill label {{ font-size: 13px; font-weight: 600; }}
button {{ background: none; border: none; box-shadow: none; padding: 0; transition: all 160ms ease; }}
.round {{ background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.16); border-radius: 999px; min-width: 36px; min-height: 36px; }}
.round label {{ font-family: '{NF}'; font-size: 18px; }}
.round:hover {{ background-color: rgba(255,255,255,0.22); }}
.nav {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 999px; padding: 4px 10px; }}
.navb {{ border-radius: 999px; min-width: 34px; min-height: 34px; }}
.navb label {{ font-family: '{NF}'; font-size: 18px; color: rgba(255,255,255,0.72); }}
.navb:hover {{ background-color: rgba(183,156,255,0.22); }}
.navb.sel {{ background-color: {ACC}; }}
.navb.sel label {{ color: #1B1034; }}
.tile {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.13); border-radius: 22px; padding: 9px 14px; }}
.tile:hover {{ background-color: rgba(255,255,255,0.13); }}
.tile.on {{ background-image: linear-gradient(135deg, rgba(183,156,255,0.42), rgba(127,178,255,0.26)); border-color: rgba(183,156,255,0.75); box-shadow: 0 8px 24px rgba(183,156,255,0.25); }}
.tile .ico {{ background: rgba(255,255,255,0.10); border-radius: 999px; min-width: 38px; min-height: 38px; }}
.tile .ico label {{ font-family: '{NF}'; font-size: 20px; }}
.tile.on .ico {{ background: {ACC}; }}
.tile.on .ico label {{ color: #1B1034; }}
.tname {{ font-size: 15px; font-weight: 700; }}
.card {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.13); border-radius: 24px; padding: 12px 18px; }}
.row {{ background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.10); border-radius: 16px; padding: 7px 12px; }}
.row:hover {{ background-color: rgba(255,255,255,0.12); }}
.row.on {{ background-image: linear-gradient(135deg, rgba(183,156,255,0.30), rgba(127,178,255,0.18)); border-color: rgba(183,156,255,0.6); }}
.row label.nf {{ font-size: 18px; }}
.chip {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 999px; padding: 5px 12px; }}
.chip label {{ font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.8); }}
.act {{ background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.16); border-radius: 999px; padding: 6px 14px; }}
.act label {{ font-size: 13px; font-weight: 600; }}
.act .nf {{ font-family: '{NF}'; font-size: 15px; }}
.act:hover {{ background-color: rgba(255,255,255,0.20); }}
.act.on {{ background-color: rgba(183,156,255,0.35); border-color: rgba(183,156,255,0.8); }}
.act.warn {{ background-color: rgba(255,90,110,0.30); border-color: rgba(255,120,140,0.7); }}
.bigbtn {{ background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.13); border-radius: 24px; padding: 22px 10px; }}
.bigbtn:hover {{ background-color: rgba(255,255,255,0.15); }}
.bigbtn.warn {{ background-color: rgba(255,90,110,0.30); border-color: rgba(255,120,140,0.7); }}
.bigbtn label.nf {{ font-size: 30px; }}
scale trough {{ min-height: 10px; border-radius: 5px; background: rgba(255,255,255,0.15); }}
scale highlight {{ border-radius: 5px; background-image: linear-gradient(90deg, {ACC}, {ACC2}); }}
scale slider {{ min-width: 24px; min-height: 24px; margin: -8px; border-radius: 999px; background: #fff; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.35); }}
progressbar trough {{ min-height: 10px; border-radius: 5px; background: rgba(255,255,255,0.15); border: none; }}
progressbar progress {{ min-height: 10px; border-radius: 5px; background-image: linear-gradient(90deg, {ACC}, {ACC2}); border: none; }}
.art {{ border-radius: 18px; background-image: linear-gradient(160deg, #F472B6, #7C3AED); min-width: 54px; min-height: 54px; }}
.play {{ background: #fff; border-radius: 999px; min-width: 44px; min-height: 44px; box-shadow: 0 8px 22px rgba(183,156,255,0.45); }}
.play:hover {{ background-color: #eee; }}
.play label {{ font-family: '{NF}'; font-size: 22px; color: #1B1034; }}
.ctl label {{ font-family: '{NF}'; font-size: 20px; }}
.evbar {{ background: {ACC}; border-radius: 2px; min-width: 3px; }}
.thumb {{ border-radius: 14px; border: 2px solid transparent; padding: 0; }}
.thumb:hover {{ border-color: rgba(255,255,255,0.45); }}
.thumb.on {{ border-color: {ACC}; box-shadow: 0 0 0 1px {ACC}; }}
.hl {{ color: {ACC}; font-size: 12px; font-weight: 700; }}
.day {{ font-size: 13px; padding: 7px 0; border-radius: 12px; }}
.day.today {{ background: {ACC}; }}
.day.today label {{ color: #1B1034; font-weight: 700; }}
entry {{ background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.20); border-radius: 14px; padding: 8px 12px; color: #fff; min-height: 20px; }}
"""


def make_css(tint):
    out = CSS.replace("TINT", f"{tint:.2f}")
    fg, pr, se, su, te = (hex2rgb(PAL[k]) for k in ("fg", "primary", "secondary", "surface", "tertiary"))
    out = out.replace("rgba(255,255,255,", f"rgba({fg[0]},{fg[1]},{fg[2]},")
    out = out.replace("rgba(183,156,255,", f"rgba({pr[0]},{pr[1]},{pr[2]},")
    out = out.replace("rgba(127,178,255,", f"rgba({se[0]},{se[1]},{se[2]},")
    out = out.replace("rgba(22,16,46,", f"rgba({su[0]},{su[1]},{su[2]},")
    out = out.replace("#1B1034", PAL["on_acc"]).replace("#eee", PAL["fg"]).replace("#fff", PAL["fg"])
    out = out.replace("#F472B6", PAL["tertiary"]).replace("#7C3AED", PAL["primary"])
    return re.sub(r"(\d+(?:\.\d+)?)px", lambda m: f"{max(1, round(float(m.group(1)) * S))}px", out)


class Panel:
    PF = 30   # abertura lateral do fundo (igual à da ilha)

    def __init__(self, daemon=False):
        self.daemon = daemon
        self.visible = False
        self.want_mon = None
        self.st = load_state()
        self.closing = False
        self.ready = False
        self.loading = {"vol": False, "bri": False, "mic": False}
        self.cpu_prev = None
        self.cur = "home"
        self.cal_off = 0
        self.confirm = {}
        self.build_window()
        self.refresh()
        GLib.timeout_add(2000, self.refresh)
        GLib.timeout_add(1000, self.tick_clock)

    # ---------- janela ----------
    def build_window(self):
        win = self.win = Gtk.Window()
        win.set_app_paintable(True)
        vis = win.get_screen().get_rgba_visual()
        if vis:
            win.set_visual(vis)
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "entropy-cc")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.ON_DEMAND)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        self.pick_monitor()
        self.top_margin = 6
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 0)
        try:
            a = float(open(ALPHA).read().strip())
        except Exception:
            a = 0.38
        tint = min(0.78, 0.30 + (a - 0.38) * 0.9)
        su_ = hex2rgb(PAL["surface"])
        self.morph_rgba = (su_[0] / 255, su_[1] / 255, su_[2] / 255, min(0.80, 0.40 + (a - 0.38) * 0.8))
        self.fg_rgb = tuple(c / 255 for c in hex2rgb(PAL["fg"]))
        prov = Gtk.CssProvider()
        prov.load_from_data(make_css(tint).encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box()
        for side, v in (("start", 0), ("end", 0), ("bottom", 0), ("top", 0)):
            getattr(outer, f"set_margin_{side}")(v)
        self.outer = outer
        self.wstack = Gtk.Stack()
        self.wstack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.anim_area = Gtk.DrawingArea()
        self.anim_area.connect("draw", self.on_anim_draw)
        self.wstack.add_named(outer, "real")
        self.wstack.add_named(self.anim_area, "anim")
        win.add(self.wstack)
        self.snap = None
        self.anim_p = 0.0
        scroll = self.scroll = Gtk.ScrolledWindow()
        self.morph_widget = scroll
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.max_h = max(260, self.mon_h - 56 - 130)
        scroll.set_max_content_height(self.max_h)
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        for side, v in (("start", self.PF + 6), ("end", self.PF + 6), ("top", 0), ("bottom", 6)):
            getattr(scroll, f"set_margin_{side}")(v)
        outer.pack_start(scroll, True, True, 0)
        outer.connect("draw", self.on_bg_draw)
        self.panel_tint = tint
        panel = self.panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.get_style_context().add_class("panelx")
        panel.set_size_request(sc(860), -1)
        pad = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sc(10))
        for side in ("start", "end", "top", "bottom"):
            getattr(pad, f"set_margin_{side}")(sc(20))
        panel.pack_start(pad, True, True, 0)
        scroll.add(panel)

        self.build_header(pad)
        self.build_nav(pad)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(200)
        self.stack.set_hhomogeneous(True)
        self.stack.set_vhomogeneous(False)
        self.stack.set_interpolate_size(True)
        pad.pack_start(self.stack, True, True, 0)
        self.refreshers = {}
        for name, fn in (("home", self.page_home), ("media", self.page_media), ("audio", self.page_audio),
                         ("display", self.page_display), ("wallpaper", self.page_wallpaper), ("system", self.page_system), ("power", self.page_power),
                         ("network", self.page_network), ("bluetooth", self.page_bluetooth), ("weather", self.page_weather),
                         ("calendar", self.page_calendar), ("notifications", self.page_notifs), ("session", self.page_session)):
            self.stack.add_named(fn(), name)

        win.connect("key-press-event", lambda w, e: self.close() if e.keyval == Gdk.KEY_Escape else None)
        win.connect("focus-out-event", self.on_focus_out)
        win.set_opacity(0.0)
        self.wstack.show_all()
        self.pw_row.hide()
        if not self.daemon:
            self.open_panel()

    def write_state(self, on):
        try:
            open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-cc.open"), "w").write("1" if on else "0")
        except OSError:
            pass

    def open_panel(self, monitor=None, page=None):
        if self.visible:
            return
        self.visible = True
        self.closing = False
        self.ready = False
        self.write_state(True)
        self.want_mon = monitor
        self.pick_monitor()
        self.max_h = max(260, self.mon_h - 56 - 130)
        self.scroll.set_max_content_height(self.max_h)
        GtkLayerShell.set_margin(self.win, GtkLayerShell.Edge.TOP, 0)
        self.goto(page or "home")
        self.wstack.set_visible_child_name("real")
        self.win.set_opacity(0.0)
        self.load_cache()
        self.win.show()
        self.pw_row.hide()
        self.tick_clock()
        self.refresh()
        GLib.idle_add(self.fit)
        GLib.timeout_add(70, self.anim_open)

    def after_close(self):
        if self.daemon:
            self.win.hide()
            self.visible = False
            self.closing = False
            self.write_state(False)
        else:
            self.write_state(False)
            Gtk.main_quit()

    def load_cache(self):
        try:
            d = json.load(open(CACHE))
            d["events"] = self.read_events(365)[:2]
            self.apply(d)
        except Exception:
            pass

    def fit(self):
        nat = self.panel.get_preferred_height()[1]
        self.scroll.set_min_content_height(min(nat, self.max_h))
        return False

    def pick_monitor(self):
        disp = Gdk.Display.get_default()
        self.mon_h = 720
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
            want = self.want_mon or os.environ.get("ENTROPY_CC_MONITOR")
            foc = next((m for m in mons if m["name"] == want), None) or next((m for m in mons if m.get("focused")), mons[0])
            self.mon_h = int(foc["height"] / foc["scale"])
            for i in range(disp.get_n_monitors()):
                gm = disp.get_monitor(i).get_geometry()
                if gm.x == int(foc["x"]) and gm.y == int(foc["y"]):
                    GtkLayerShell.set_monitor(self.win, disp.get_monitor(i))
                    return
        except Exception:
            pass

    # ---------- animações (líquido saindo do topo / sugado de volta) ----------
    def snapshot(self):
        w, h = self.outer.get_allocated_width(), self.outer.get_allocated_height()
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        self.outer.draw(cr)
        return surf

    # ----- a ilha se expande até virar o painel (mesma forma, colada no topo) -----
    @staticmethod
    def smoothstep(a, b, x):
        t = max(0.0, min(1.0, (x - a) / (b - a)))
        return t * t * (3 - 2 * t)

    @staticmethod
    def rrect(cr, x, y, w, h, r):
        r = max(0.0, min(r, w / 2.0, h / 2.0))
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def snapshot(self):
        """imagem do conteúdo do painel, sem o fundo (o fundo é desenhado pela forma)"""
        self.snapping = True
        try:
            w, h = self.outer.get_allocated_width(), self.outer.get_allocated_height()
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, w), max(1, h))
            self.outer.draw(cairo.Context(surf))
        finally:
            self.snapping = False
        return surf

    def notch_path(self, cr, cx, hw, D, f, r, close=True):
        """contorno da ilha: colado no topo, com as laterais abrindo em curva côncava até a borda"""
        r = max(0.0, min(r, D / 2.0, hw))
        x0, x1 = cx - hw, cx + hw
        yf = min(0.55 * D, 22.0)
        yb = max(yf, D - r)
        cr.new_path()
        cr.move_to(x0 - f, 0)
        cr.curve_to(x0 - f * 0.45, 0, x0, yf * 0.42, x0, yf)
        cr.line_to(x0, yb)
        cr.arc_negative(x0 + r, D - r, r, math.pi, math.pi / 2)
        cr.line_to(x1 - r, D)
        cr.arc_negative(x1 - r, D - r, r, math.pi / 2, 0)
        cr.line_to(x1, yf)
        cr.curve_to(x1, yf * 0.42, x1 + f * 0.45, 0, x1 + f, 0)
        if close:
            cr.close_path()

    def draw_notch(self, cr, cx, hw, D, f, r, alpha, stroke_a):
        cr.push_group()
        cr.set_source_rgb(*self.morph_rgba[:3])
        self.notch_path(cr, cx, hw, D, f, r, True)
        cr.fill()
        cr.pop_group_to_source()
        cr.paint_with_alpha(alpha)
        self.notch_path(cr, cx, hw, D, f, r, False)
        cr.set_source_rgba(self.fg_rgb[0], self.fg_rgb[1], self.fg_rgb[2], stroke_a)
        cr.set_line_width(1.0)
        cr.stroke()

    def panel_rect(self):
        pt = self.scroll.translate_coordinates(self.outer, 0, 0)
        if pt is None:
            return None
        return pt[0], pt[1], self.scroll.get_allocated_width(), self.scroll.get_allocated_height()

    def on_bg_draw(self, widget, cr):
        if getattr(self, "snapping", False):
            return False
        r = self.panel_rect()
        if r is None or r[2] < 50:
            return False
        x, y, w, h = r
        self.draw_notch(cr, widget.get_allocated_width() / 2.0, w / 2.0, y + h, self.PF, sc(36), self.panel_tint, 0.18)
        return False

    def morph_target(self):
        x, y, w, h = self.panel_rect()
        return {"hw": w / 2.0, "D": y + h, "f": float(self.PF), "r": float(sc(36)), "a": self.panel_tint}

    def morph_origin(self):
        try:
            pw, ph = map(float, open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-island.geom")).read().split())
        except Exception:
            pw, ph = 140.0, 30.0
        return {"hw": pw / 2.0, "D": 3.0 + ph, "f": 30.0, "r": ph / 2.0, "a": self.morph_rgba[3]}

    def on_anim_draw(self, widget, cr):
        if self.snap is None:
            return False
        p = self.anim_p
        o, t = self.origin, self.target
        pc = max(0.0, min(1.0, p))
        hw = o["hw"] + (t["hw"] - o["hw"]) * p
        D = o["D"] + (t["D"] - o["D"]) * p
        f = o["f"] + (t["f"] - o["f"]) * pc
        r = o["r"] + (t["r"] - o["r"]) * pc
        alpha = o["a"] + (t["a"] - o["a"]) * pc
        cx = widget.get_allocated_width() / 2.0
        ca = self.smoothstep(0.30, 0.80, pc)
        self.draw_notch(cr, cx, max(4.0, hw), max(8.0, D), f, r, alpha, 0.16 + 0.02 * ca)
        if ca > 0.01:
            cr.save()
            self.notch_path(cr, cx, max(4.0, hw), max(8.0, D), f, r, True)
            cr.clip()
            cr.set_source_surface(self.snap, 0, 0)
            cr.paint_with_alpha(ca)
            cr.restore()
        return False

    # variante em retângulo arredondado (usada pelo menu de apps, que sai do dock)
    def morph_target_rect(self):
        w = self.morph_widget
        x, y = w.translate_coordinates(self.outer, 0, 0)
        return (x, y, w.get_allocated_width(), w.get_allocated_height(), sc(36))

    def on_anim_draw_rect(self, widget, cr):
        if self.snap is None:
            return False
        p = self.anim_p
        ox, oy, ow, oh, orr = self.origin
        tx, ty, tw, th, tr = self.target
        k = max(0.0, p)
        x, y = ox + (tx - ox) * k, oy + (ty - oy) * k
        w, h = max(2.0, ow + (tw - ow) * k), max(2.0, oh + (th - oh) * k)
        pc = max(0.0, min(1.0, p))
        r = orr + (tr - orr) * pc
        fa = self.morph_rgba[3] * (1.0 - self.smoothstep(0.30, 0.85, pc))
        self.rrect(cr, x, y, w, h, r)
        cr.set_source_rgba(self.morph_rgba[0], self.morph_rgba[1], self.morph_rgba[2], fa)
        cr.fill()
        ca = self.smoothstep(0.22, 0.78, pc)
        if ca > 0.01:
            cr.save()
            self.rrect(cr, x, y, w, h, r)
            cr.clip()
            cr.set_source_surface(self.snap, 0, 0)
            cr.paint_with_alpha(ca)
            cr.restore()
        self.rrect(cr, x, y, w, h, r)
        cr.set_source_rgba(self.fg_rgb[0], self.fg_rgb[1], self.fg_rgb[2], 0.18 * (1.0 - 0.5 * ca))
        cr.set_line_width(1.0)
        cr.stroke()
        return False

    def prepare_morph_rect(self):
        self.snap = self.snapshot()
        self.anim_area.set_size_request(self.snap.get_width(), self.snap.get_height())
        self.target = self.morph_target()
        self.origin = self.morph_origin()

    def run_anim(self, opening, dur, done):
        self.t0 = GLib.get_monotonic_time()
        dur = dur * float(os.environ.get("ENTROPY_ANIM_SLOW", "1"))

        def step():
            r = min(1.0, (GLib.get_monotonic_time() - self.t0) / (dur * 1e6))
            if opening:
                t = r - 1.0
                self.anim_p = 1.0 + 1.7 * t ** 3 + 0.7 * t ** 2
            else:
                self.anim_p = 1.0 - r * r * (3 - 2 * r)
            self.anim_area.queue_draw()
            if r >= 1.0:
                done()
                return False
            return True
        GLib.timeout_add(16, step)

    def prepare_morph(self):
        self.snap = self.snapshot()
        self.anim_area.set_size_request(self.snap.get_width(), self.snap.get_height())
        self.target = self.morph_target()
        self.origin = self.morph_origin()

    def anim_open(self):
        try:
            self.prepare_morph()
            self.anim_p = 0.0
            self.wstack.set_visible_child_name("anim")
            self.win.set_opacity(1.0)

            def done():
                self.wstack.set_visible_child_name("real")
                self.outer.queue_draw()
                self.ready = True
            self.run_anim(True, 0.55, done)
        except Exception as e:
            print("anim_open:", repr(e), flush=True)
            self.win.set_opacity(1.0)
            self.ready = True
        return False

    def close(self):
        if self.closing:
            return
        self.closing = True
        try:
            self.prepare_morph()
            self.anim_p = 1.0
            self.wstack.set_visible_child_name("anim")
            self.run_anim(False, 0.40, self.after_close)
        except Exception:
            self.after_close()

    def on_focus_out(self, *a):
        if os.environ.get("ENTROPY_CC_NOCLOSE"):
            return
        if self.visible and self.ready and not self.closing:
            GLib.timeout_add(220, lambda: (self.close() if not self.win.is_active() else None) or False)

    # ---------- helpers de UI ----------
    def lbl(self, text="", cls=None, xalign=0.0, ell=False, maxc=0):
        l = Gtk.Label(label=text)
        l.set_xalign(xalign)
        if cls:
            for c in cls.split():
                l.get_style_context().add_class(c)
        if ell:
            l.set_ellipsize(3)
        if maxc:
            l.set_max_width_chars(maxc)
        return l

    def vbox(self, sp=14):
        return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=sc(sp))

    def hbox(self, sp=12):
        return Gtk.Box(spacing=sc(sp))

    def card(self, sp=14):
        c = self.vbox(sp)
        c.get_style_context().add_class("card")
        return c

    def icon_btn(self, key, cls, cb, tip=None):
        b = Gtk.Button()
        b.get_style_context().add_class(cls)
        b.add(self.lbl(I[key], xalign=0.5))
        b.set_halign(Gtk.Align.CENTER)
        b.set_valign(Gtk.Align.CENTER)
        b.connect("clicked", lambda *_: cb())
        if tip:
            b.set_tooltip_text(tip)
        return b

    def act_btn(self, key, text, cb, cls="act"):
        b = Gtk.Button()
        b.get_style_context().add_class(cls)
        h = self.hbox(8)
        h.pack_start(self.lbl(I[key], "nf"), False, False, 0)
        h.pack_start(self.lbl(text), False, False, 0)
        b.add(h)
        b.connect("clicked", lambda *_: cb())
        return b

    def clear(self, box):
        for c in box.get_children():
            box.remove(c)

    def page(self, title=None):
        box = self.vbox(10)
        if title:
            box.pack_start(self.lbl(title, "h2"), False, False, 0)
        return box

    def slider_row(self, icon_key, on_icon):
        row = self.hbox(14)
        ic = self.icon_btn(icon_key, "ctl", on_icon)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(False)
        scale.set_hexpand(True)
        val = self.lbl("--%", "small")
        val.set_width_chars(4)
        row.pack_start(ic, False, False, 0)
        row.pack_start(scale, True, True, 0)
        row.pack_start(val, False, False, 0)
        return row, scale, val, ic

    def debounce(self, key, fn):
        src = getattr(self, "_deb_" + key, 0)
        if src:
            GLib.source_remove(src)

        def go():
            setattr(self, "_deb_" + key, 0)
            fn()
            return False
        setattr(self, "_deb_" + key, GLib.timeout_add(90, go))

    def later(self, ms, fn):
        GLib.timeout_add(ms, lambda: (fn(), False)[1])

    def goto(self, name):
        self.cur = name
        self.stack.set_visible_child_name(name)
        for n, b in self.navbtn.items():
            ctx = b.get_style_context()
            (ctx.add_class if n == name else ctx.remove_class)("sel")
        self.later(260, self.fit)
        if name in self.refreshers:
            self.refreshers[name]()

    # ---------- cabeçalho / nav ----------
    def build_header(self, box):
        row = self.hbox(10)
        left = self.vbox(3)
        self.greet = self.lbl("", "title")
        self.sub = self.lbl("", "sub")
        left.pack_start(self.greet, False, False, 0)
        left.pack_start(self.sub, False, False, 0)
        row.pack_start(left, True, True, 0)
        bat = self.hbox(8)
        bat.get_style_context().add_class("pill")
        self.bat = self.lbl("--%")
        bat.pack_start(self.lbl(I["bat"], "nf"), False, False, 0)
        bat.pack_start(self.bat, False, False, 0)
        row.pack_start(bat, False, False, 0)
        row.pack_start(self.icon_btn("cog", "round", lambda: (fire("noctalia", "msg", "settings-open"), self.close()), "Configurações"), False, False, 0)
        row.pack_start(self.icon_btn("power", "round", lambda: self.goto("session"), "Sessão"), False, False, 0)
        row.pack_start(self.icon_btn("close", "round", self.close, "Fechar"), False, False, 0)
        box.pack_start(row, False, False, 0)

    def build_nav(self, box):
        nav = self.hbox(4)
        nav.get_style_context().add_class("nav")
        self.navbtn = {}
        for key, name, tip in TABS:
            b = self.icon_btn(key, "navb", lambda n=name: self.goto(n), tip)
            self.navbtn[name] = b
            nav.pack_start(b, True, True, 0)
        self.navbtn["home"].get_style_context().add_class("sel")
        box.pack_start(nav, False, False, 0)

    # ---------- páginas ----------
    def tile(self, icon, name, action):
        b = Gtk.Button()
        b.get_style_context().add_class("tile")
        row = self.hbox(14)
        ico = Gtk.Box()
        ico.get_style_context().add_class("ico")
        il = self.lbl(I[icon], xalign=0.5)
        il.set_hexpand(True)
        ico.pack_start(il, True, True, 0)
        col = self.vbox(2)
        col.set_valign(Gtk.Align.CENTER)
        s = self.lbl("", "small")
        col.pack_start(self.lbl(name, "tname"), False, False, 0)
        col.pack_start(s, False, False, 0)
        row.pack_start(ico, False, False, 0)
        row.pack_start(col, True, True, 0)
        row.set_halign(Gtk.Align.START)
        b.add(row)
        b.connect("clicked", lambda *_: action())
        b.set_hexpand(True)
        return b, s

    def set_tile(self, key, on, status):
        btn, lab = self.tiles[key]
        ctx = btn.get_style_context()
        (ctx.add_class if on else ctx.remove_class)("on")
        lab.set_text(status)

    def page_home(self):
        box = self.page()
        grid = Gtk.Grid(row_spacing=sc(9), column_spacing=sc(9))
        grid.set_column_homogeneous(True)
        spec = [("wifi", "Wi-Fi", lambda: fire("noctalia", "msg", "wifi-toggle")),
                ("bt", "Bluetooth", lambda: fire("noctalia", "msg", "bluetooth-toggle")),
                ("dnd", "Não perturbe", lambda: fire("noctalia", "msg", "notification-dnd-toggle")),
                ("night", "Luz noturna", self.t_night), ("coffee", "Cafeína", self.t_coffee),
                ("perf", "Energia", lambda: fire("noctalia", "msg", "power-cycle"))]
        self.tiles = {}
        for i, (ic, name, act) in enumerate(spec):
            b, s = self.tile(ic, name, act)
            self.tiles[ic] = (b, s)
            grid.attach(b, i % 3, i // 3, 1, 1)
        box.pack_start(grid, False, False, 0)

        sl = self.card(10)
        r1, self.vol_sc, self.vol_lbl, self.vol_ic = self.slider_row("vol", lambda: fire("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"))
        r2, self.bri_sc, self.bri_lbl, _ = self.slider_row("bri", lambda: None)
        self.vol_sc.connect("value-changed", self.on_vol)
        self.bri_sc.connect("value-changed", self.on_bri)
        sl.pack_start(r1, False, False, 0)
        sl.pack_start(r2, False, False, 0)
        box.pack_start(sl, False, False, 0)

        row = Gtk.Box(spacing=sc(12), homogeneous=True)
        media = self.card(8)
        top = self.hbox(12)
        art = Gtk.Box()
        art.get_style_context().add_class("art")
        mt = self.vbox(3)
        mt.set_valign(Gtk.Align.CENTER)
        self.m_title = self.lbl("Nada tocando", "tname", ell=True, maxc=18)
        self.m_art = self.lbl("Ocioso", "small", ell=True, maxc=20)
        mt.pack_start(self.m_title, False, False, 0)
        mt.pack_start(self.m_art, False, False, 0)
        top.pack_start(art, False, False, 0)
        top.pack_start(mt, True, True, 0)
        media.pack_start(top, False, False, 0)
        media.pack_start(self.controls("play_home"), False, False, 0)
        ag = self.card(8)
        ag.pack_start(self.lbl("AGENDA", "hl"), False, False, 0)
        self.ev_box = self.vbox(12)
        ag.pack_start(self.ev_box, False, False, 0)
        row.pack_start(media, True, True, 0)
        row.pack_start(ag, True, True, 0)
        box.pack_start(row, False, False, 0)

        foot = self.hbox(8)
        self.chips = {}
        for k in ("cpu", "ram", "temp", "up"):
            c = Gtk.Box()
            c.get_style_context().add_class("chip")
            l = self.lbl("--")
            c.pack_start(l, False, False, 0)
            self.chips[k] = l
            foot.pack_start(c, False, False, 0)
        foot.pack_start(Gtk.Box(), True, True, 0)
        foot.pack_start(self.act_btn("lock", "Bloquear", lambda: (fire("noctalia", "msg", "session", "lock"), self.close())), False, False, 0)
        foot.pack_start(self.act_btn("sleep", "Suspender", lambda: (fire("noctalia", "msg", "session", "suspend"), self.close())), False, False, 0)
        box.pack_start(foot, False, False, 0)
        return box

    def controls(self, attr):
        ctl = self.hbox(22)
        ctl.set_halign(Gtk.Align.CENTER)
        ctl.pack_start(self.icon_btn("prev", "ctl", lambda: fire("playerctl", "previous")), False, False, 0)
        pb = self.icon_btn("play", "play", lambda: fire("playerctl", "play-pause"))
        setattr(self, attr, pb)
        ctl.pack_start(pb, False, False, 0)
        ctl.pack_start(self.icon_btn("next", "ctl", lambda: fire("playerctl", "next")), False, False, 0)
        return ctl

    def page_media(self):
        box = self.page("Mídia")
        c = self.card(16)
        top = self.hbox(18)
        art = Gtk.Box()
        art.get_style_context().add_class("art")
        art.set_size_request(sc(110), sc(110))
        mt = self.vbox(5)
        mt.set_valign(Gtk.Align.CENTER)
        self.mp_title = self.lbl("Nada tocando", "h2", ell=True, maxc=26)
        self.mp_artist = self.lbl("", "sub", ell=True, maxc=30)
        self.mp_album = self.lbl("", "small", ell=True, maxc=30)
        for w in (self.mp_title, self.mp_artist, self.mp_album):
            mt.pack_start(w, False, False, 0)
        top.pack_start(art, False, False, 0)
        top.pack_start(mt, True, True, 0)
        c.pack_start(top, False, False, 0)
        c.pack_start(self.controls("play_page"), False, False, 0)
        box.pack_start(c, False, False, 0)
        return box

    def list_row(self, icon, title, sub, on, cb, right=""):
        b = Gtk.Button()
        ctx = b.get_style_context()
        ctx.add_class("row")
        if on:
            ctx.add_class("on")
        h = self.hbox(12)
        h.pack_start(self.lbl(icon, "nf"), False, False, 0)
        col = self.vbox(1)
        col.pack_start(self.lbl(title, "tname", ell=True, maxc=34), False, False, 0)
        if sub:
            col.pack_start(self.lbl(sub, "small", ell=True, maxc=40), False, False, 0)
        h.pack_start(col, True, True, 0)
        if on:
            h.pack_start(self.lbl(I["check"], "nf"), False, False, 0)
        elif right:
            h.pack_start(self.lbl(right, "nf small"), False, False, 0)
        b.add(h)
        b.connect("clicked", lambda *_: cb())
        return b

    def page_audio(self):
        box = self.page("Áudio")
        out = self.card(14)
        out.pack_start(self.lbl("Saída", "tname"), False, False, 0)
        r1, self.a_vol_sc, self.a_vol_lbl, self.a_vol_ic = self.slider_row("vol", lambda: fire("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"))
        self.a_vol_sc.connect("value-changed", self.on_vol)
        out.pack_start(r1, False, False, 0)
        self.sink_box = self.vbox(8)
        out.pack_start(self.sink_box, False, False, 0)
        inp = self.card(14)
        inp.pack_start(self.lbl("Entrada", "tname"), False, False, 0)
        r2, self.mic_sc, self.mic_lbl, self.mic_ic = self.slider_row("mic", lambda: fire("wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"))
        self.mic_sc.connect("value-changed", self.on_mic)
        inp.pack_start(r2, False, False, 0)
        self.src_box = self.vbox(8)
        inp.pack_start(self.src_box, False, False, 0)
        box.pack_start(out, False, False, 0)
        box.pack_start(inp, False, False, 0)

        def load():
            def get(kind):
                try:
                    items = json.loads(sh("pactl", "-f", "json", "list", kind))
                except Exception:
                    items = []
                default = sh("pactl", "get-default-" + kind[:-1])
                return [(x["name"], x.get("description", x["name"]), x["name"] == default) for x in items if ".monitor" not in x["name"]]
            return get("sinks"), get("sources")

        def show(r):
            for bx, items, cmd, ic in ((self.sink_box, r[0], "set-default-sink", I["speaker"]), (self.src_box, r[1], "set-default-source", I["mic"])):
                self.clear(bx)
                for name, desc, cur in items:
                    bx.pack_start(self.list_row(ic, desc, "", cur,
                                                lambda n=name, c=cmd: (fire("pactl", c, n), self.later(400, self.refreshers["audio"]))), False, False, 0)
                bx.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["audio"] = lambda: bg(load, show)
        return box

    def page_display(self):
        box = self.page("Display")
        c = self.card(16)
        r, self.d_bri_sc, self.d_bri_lbl, _ = self.slider_row("bri", lambda: None)
        self.d_bri_sc.connect("value-changed", self.on_bri)
        c.pack_start(self.lbl("Brilho da tela", "tname"), False, False, 0)
        c.pack_start(r, False, False, 0)
        box.pack_start(c, False, False, 0)
        mc = self.card(10)
        mc.pack_start(self.lbl("Monitores", "tname"), False, False, 0)
        self.mon_box = self.vbox(8)
        mc.pack_start(self.mon_box, False, False, 0)
        box.pack_start(mc, False, False, 0)

        def load():
            try:
                return json.loads(sh("hyprctl", "monitors", "-j"))
            except Exception:
                return []

        def show(ms):
            self.clear(self.mon_box)
            for m in ms:
                sub = f"{m['width']}x{m['height']} @ {round(m['refreshRate'])}Hz  ·  escala {m['scale']}"
                self.mon_box.pack_start(self.list_row(I["monitor"], f"{m['name']}  {m.get('description', '')[:28]}", sub, bool(m.get("focused")), lambda: None), False, False, 0)
            self.mon_box.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["display"] = lambda: bg(load, show)
        return box

    def page_wallpaper(self):
        box = self.page("Papel de parede")
        self.wp_target = None
        self.wp_loaded = False
        self.wp_btns = {}
        top = self.hbox(8)
        self.wp_chips = {}
        names = [None]
        try:
            names += [m["name"] for m in json.loads(sh("hyprctl", "monitors", "-j"))]
        except Exception:
            pass
        for n in names:
            b = self.act_btn("monitor", n or "Todos", lambda n=n: self.wp_set_target(n))
            self.wp_chips[n] = b
            top.pack_start(b, False, False, 0)
        top.pack_start(Gtk.Box(), True, True, 0)
        for key, text, cmd in (("prev", "Anterior", "wallpaper-previous"), ("scan", "Aleatório", "wallpaper-random"), ("next", "Próximo", "wallpaper-next")):
            top.pack_start(self.act_btn(key, text, lambda c=cmd: self.wp_cmd(c)), False, False, 0)
        box.pack_start(top, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(sc(330))
        scroll.set_shadow_type(Gtk.ShadowType.NONE)
        self.wp_flow = Gtk.FlowBox()
        self.wp_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wp_flow.set_min_children_per_line(3)
        self.wp_flow.set_max_children_per_line(3)
        self.wp_flow.set_homogeneous(True)
        self.wp_flow.set_row_spacing(sc(10))
        self.wp_flow.set_column_spacing(sc(10))
        scroll.add(self.wp_flow)
        box.pack_start(scroll, True, True, 0)
        self.refreshers["wallpaper"] = self.wp_load
        self.wp_mark_chip()
        return box

    def wp_mark_chip(self):
        for n, b in self.wp_chips.items():
            ctx = b.get_style_context()
            (ctx.add_class if n == self.wp_target else ctx.remove_class)("on")
        self.wp_highlight()

    def wp_set_target(self, n):
        self.wp_target = n
        self.wp_mark_chip()

    def wp_current(self):
        conn = self.wp_target
        if not conn:
            try:
                conn = next(m["name"] for m in json.loads(sh("hyprctl", "monitors", "-j")) if m.get("focused"))
            except Exception:
                conn = ""
        return sh("noctalia", "msg", "wallpaper-get", conn) if conn else sh("noctalia", "msg", "wallpaper-get")

    def wp_highlight(self):
        def get():
            return self.wp_current()

        def show(cur):
            for path, b in self.wp_btns.items():
                ctx = b.get_style_context()
                (ctx.add_class if path == cur else ctx.remove_class)("on")
        bg(get, show)

    def wp_cmd(self, cmd):
        args = ["noctalia", "msg", cmd] + ([self.wp_target] if self.wp_target else [])
        fire(*args)
        self.later(1200, self.wp_highlight)

    def wp_pick(self, path):
        args = ["noctalia", "msg", "wallpaper-set"] + ([self.wp_target] if self.wp_target else []) + [path]
        fire(*args)
        self.later(900, self.wp_highlight)

    def wp_load(self):
        try:
            stamp = os.path.getmtime(WALLS)
        except OSError:
            stamp = 0
        if self.wp_loaded and stamp == getattr(self, "wp_stamp", None):
            self.wp_highlight()
            return
        self.wp_loaded = True
        self.wp_stamp = stamp
        for c in self.wp_flow.get_children():
            self.wp_flow.remove(c)
        self.wp_btns = {}

        def work():
            os.makedirs(THUMBS, exist_ok=True)
            try:
                files = [os.path.join(WALLS, f) for f in os.listdir(WALLS) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
            except Exception:
                files = []
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            for f in files[:90]:
                key = hashlib.md5(f"{f}{os.path.getmtime(f)}".encode()).hexdigest()
                tp = os.path.join(THUMBS, key + ".png")
                try:
                    if not os.path.exists(tp):
                        GdkPixbuf.Pixbuf.new_from_file_at_scale(f, 340, 192, True).savev(tp, "png", [], [])
                    pb = GdkPixbuf.Pixbuf.new_from_file(tp)
                except Exception:
                    continue
                GLib.idle_add(self.wp_add, f, pb)
            GLib.idle_add(self.wp_highlight)
        threading.Thread(target=work, daemon=True).start()

    def wp_add(self, path, pb):
        b = Gtk.Button()
        b.get_style_context().add_class("thumb")
        img = Gtk.Image.new_from_pixbuf(pb.scale_simple(172, 97, GdkPixbuf.InterpType.BILINEAR))
        b.add(img)
        b.connect("clicked", lambda *_: self.wp_pick(path))
        b.set_tooltip_text(os.path.basename(path))
        self.wp_btns[path] = b
        self.wp_flow.add(b)
        b.show_all()
        return False

    def page_system(self):
        box = self.page("Sistema")
        c = self.card(16)
        self.sys_bars = {}
        for key, name in (("cpu", "Processador"), ("ram", "Memória"), ("disk", "Disco (/)"), ("temp", "Temperatura")):
            row = self.vbox(6)
            head = self.hbox(8)
            head.pack_start(self.lbl(name, "tname"), True, True, 0)
            v = self.lbl("--", "small")
            head.pack_start(v, False, False, 0)
            pb = Gtk.ProgressBar()
            row.pack_start(head, False, False, 0)
            row.pack_start(pb, False, False, 0)
            c.pack_start(row, False, False, 0)
            self.sys_bars[key] = (pb, v)
        box.pack_start(c, False, False, 0)
        ic = self.card(8)
        ic.pack_start(self.lbl(f"{os.environ.get('USER', 'dk')}@{platform.node()}", "tname"), False, False, 0)
        ic.pack_start(self.lbl(f"Kernel {platform.release()}  ·  Noctalia v5.4.0", "small"), False, False, 0)
        box.pack_start(ic, False, False, 0)
        return box

    def page_power(self):
        box = self.page("Energia")
        c = self.card(12)
        self.p_pct = self.lbl("--%", "big")
        self.p_state = self.lbl("", "sub")
        self.p_bar = Gtk.ProgressBar()
        c.pack_start(self.p_pct, False, False, 0)
        c.pack_start(self.p_state, False, False, 0)
        c.pack_start(self.p_bar, False, False, 0)
        box.pack_start(c, False, False, 0)
        pc = self.card(10)
        pc.pack_start(self.lbl("Perfil de energia", "tname"), False, False, 0)
        self.prof_rows = {}
        for key, name in PERFIS.items():
            r = self.list_row(I["perf"], name, "", False, lambda k=key: (fire("powerprofilesctl", "set", k), self.later(300, self.refresh)))
            self.prof_rows[key] = r
            pc.pack_start(r, False, False, 0)
        box.pack_start(pc, False, False, 0)
        self.p_state_base = ""

        def load():
            out = sh("upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0")
            m = re.search(r"time to (empty|full):\s+(.+)", out)
            return m.group(2).replace("hours", "h").replace("minutes", "min") if m else ""
        self.refreshers["power"] = lambda: bg(load, lambda t: self.p_state.set_text(self.p_state_base + (f"  ·  {t}" if t else "")))
        return box

    def page_network(self):
        box = self.page("Rede")
        c = self.card(12)
        top = self.hbox(10)
        top.pack_start(self.lbl("Wi-Fi", "tname"), True, True, 0)
        top.pack_start(self.act_btn("wifi", "Ligar/Desligar", lambda: (fire("noctalia", "msg", "wifi-toggle"), self.later(900, self.refreshers["network"]))), False, False, 0)
        c.pack_start(top, False, False, 0)
        self.net_status = self.lbl("", "small")
        c.pack_start(self.net_status, False, False, 0)
        self.net_box = self.vbox(8)
        c.pack_start(self.net_box, False, False, 0)
        self.pw_row = self.hbox(8)
        self.pw_entry = Gtk.Entry()
        self.pw_entry.set_visibility(False)
        self.pw_entry.set_placeholder_text("Senha da rede")
        self.pw_entry.set_hexpand(True)
        self.pw_entry.connect("activate", lambda *_: self.connect_pw())
        self.pw_row.pack_start(self.pw_entry, True, True, 0)
        self.pw_row.pack_start(self.act_btn("check", "Conectar", self.connect_pw), False, False, 0)
        c.pack_start(self.pw_row, False, False, 0)
        box.pack_start(c, False, False, 0)
        self.pw_ssid = None

        def load():
            nets = {}
            for line in sh("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list").splitlines():
                p = line.replace("\\:", "\x00").split(":")
                if len(p) < 4 or not p[1]:
                    continue
                ssid = p[1].replace("\x00", ":")
                cur = {"use": p[0] == "*", "ssid": ssid, "sig": int(p[2] or 0), "sec": p[3]}
                if ssid not in nets or cur["use"] or cur["sig"] > nets[ssid]["sig"]:
                    nets[ssid] = cur
            return sorted(nets.values(), key=lambda n: (not n["use"], -n["sig"]))[:8]

        def show(nets):
            self.clear(self.net_box)
            for n in nets:
                ic = I["w4"] if n["sig"] > 75 else I["w3"] if n["sig"] > 50 else I["w2"] if n["sig"] > 25 else I["w1"]
                self.net_box.pack_start(self.list_row(ic, n["ssid"], ("Protegida" if n["sec"] else "Aberta") + f"  ·  {n['sig']}%", n["use"],
                                                      lambda s=n["ssid"], sec=bool(n["sec"]): self.connect_net(s, sec), I["lock"] if n["sec"] else ""), False, False, 0)
            if not nets:
                self.net_box.pack_start(self.lbl("Nenhuma rede encontrada (Wi-Fi desligado?)", "small"), False, False, 0)
            self.net_box.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["network"] = lambda: bg(load, show)
        return box

    def connect_net(self, ssid, sec):
        self.net_status.set_text(f"Conectando a {ssid}…")
        self.pw_row.hide()

        def run():
            subprocess.run(["nmcli", "-w", "15", "dev", "wifi", "connect", ssid], capture_output=True, text=True)
            return ("yes:" + ssid) in sh("nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi")

        def done(ok):
            if ok:
                self.net_status.set_text(f"Conectado a {ssid}")
                self.refreshers["network"]()
            elif sec:
                self.pw_ssid = ssid
                self.net_status.set_text(f"{ssid}: digite a senha")
                self.pw_row.show_all()
                self.pw_entry.grab_focus()
            else:
                self.net_status.set_text(f"Não foi possível conectar a {ssid}")
        bg(run, done)

    def connect_pw(self):
        ssid, pw = self.pw_ssid, self.pw_entry.get_text()
        if not ssid or not pw:
            return
        self.net_status.set_text(f"Conectando a {ssid}…")

        def run():
            subprocess.run(["nmcli", "-w", "20", "dev", "wifi", "connect", ssid, "password", pw], capture_output=True, text=True)
            return ("yes:" + ssid) in sh("nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi")

        def done(ok):
            self.net_status.set_text(f"Conectado a {ssid}" if ok else "Senha incorreta ou falha na conexão")
            if ok:
                self.pw_entry.set_text("")
                self.pw_row.hide()
                self.refreshers["network"]()
        bg(run, done)

    def page_bluetooth(self):
        box = self.page("Bluetooth")
        c = self.card(12)
        top = self.hbox(10)
        top.pack_start(self.lbl("Dispositivos", "tname"), True, True, 0)
        top.pack_start(self.act_btn("scan", "Procurar", self.bt_scan), False, False, 0)
        top.pack_start(self.act_btn("bt", "Ligar/Desligar", lambda: (fire("noctalia", "msg", "bluetooth-toggle"), self.later(900, self.refreshers["bluetooth"]))), False, False, 0)
        c.pack_start(top, False, False, 0)
        self.bt_status = self.lbl("", "small")
        c.pack_start(self.bt_status, False, False, 0)
        self.bt_box = self.vbox(8)
        c.pack_start(self.bt_box, False, False, 0)
        box.pack_start(c, False, False, 0)

        def load():
            devs = []
            conn = {l.split()[1] for l in sh("bluetoothctl", "devices", "Connected").splitlines() if l.startswith("Device")}
            for l in sh("bluetoothctl", "devices").splitlines():
                p = l.split(" ", 2)
                if len(p) == 3 and p[0] == "Device":
                    devs.append((p[1], p[2], p[1] in conn))
            return sorted(devs, key=lambda d: (not d[2], d[1].lower()))[:9]

        def show(devs):
            self.clear(self.bt_box)
            for mac, name, on in devs:
                self.bt_box.pack_start(self.list_row(I["headset"], name, "Conectado" if on else mac, on,
                                                     lambda m=mac, o=on: self.bt_toggle(m, o)), False, False, 0)
            if not devs:
                self.bt_box.pack_start(self.lbl("Nenhum dispositivo conhecido", "small"), False, False, 0)
            self.bt_box.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["bluetooth"] = lambda: bg(load, show)
        return box

    def bt_toggle(self, mac, on):
        self.bt_status.set_text("Desconectando…" if on else "Conectando…")
        bg(lambda: sh("bluetoothctl", "disconnect" if on else "connect", mac, timeout=15),
           lambda _: (self.bt_status.set_text(""), self.refreshers["bluetooth"]()))

    def bt_scan(self):
        self.bt_status.set_text("Procurando dispositivos por 8s…")
        bg(lambda: sh("bluetoothctl", "--timeout", "8", "scan", "on", timeout=12),
           lambda _: (self.bt_status.set_text(""), self.refreshers["bluetooth"]()))

    def page_weather(self):
        box = self.page("Clima")
        c = self.card(12)
        top = self.hbox(16)
        self.w_icon = self.lbl("", "nf big")
        col = self.vbox(2)
        self.w_temp = self.lbl("--°C", "big")
        self.w_desc = self.lbl("", "sub")
        col.pack_start(self.w_temp, False, False, 0)
        col.pack_start(self.w_desc, False, False, 0)
        top.pack_start(self.w_icon, False, False, 0)
        top.pack_start(col, True, True, 0)
        c.pack_start(top, False, False, 0)
        self.w_extra = self.lbl("", "small")
        c.pack_start(self.w_extra, False, False, 0)
        box.pack_start(c, False, False, 0)
        fc = self.card(8)
        fc.pack_start(self.lbl("Próximos dias", "tname"), False, False, 0)
        self.fc_box = self.vbox(8)
        fc.pack_start(self.fc_box, False, False, 0)
        box.pack_start(fc, False, False, 0)

        def load():
            try:
                return json.load(open(WEATHER))["snapshot"]
            except Exception:
                return None

        def show(s):
            if not s:
                return
            cur = s["current"]
            ic, desc = wicon(cur["weather_code"])
            self.w_icon.set_text(ic)
            self.w_temp.set_text(f"{round(cur['temperature_c'])}°C")
            self.w_desc.set_text(f"{desc}  ·  {s.get('location_name', '')}")
            self.w_extra.set_text(f"Sensação {round(cur['apparent_temperature_c'])}°C   ·   Umidade {cur['relative_humidity_percent']}%   ·   Vento {round(cur['wind_speed_kmh'])} km/h   ·   UV {cur['uv_index']}")
            self.clear(self.fc_box)
            for d in s["forecast_days"][:5]:
                dt = datetime.date.fromisoformat(d["date_iso"])
                wi, wd = wicon(d["weather_code"])
                r = self.hbox(14)
                r.pack_start(self.lbl(DIAS[dt.weekday()][:3].capitalize() + f" {dt.day}", "tname"), False, False, 0)
                r.pack_start(self.lbl(wi, "nf"), False, False, 0)
                r.pack_start(self.lbl(wd, "small"), True, True, 0)
                r.pack_start(self.lbl(f"{round(d['temperature_min_c'])}° / {round(d['temperature_max_c'])}°", "tname"), False, False, 0)
                self.fc_box.pack_start(r, False, False, 0)
            self.fc_box.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["weather"] = lambda: bg(load, show)
        return box

    def page_calendar(self):
        box = self.page()
        c = self.card(12)
        head = self.hbox(10)
        self.cal_title = self.lbl("", "h2")
        head.pack_start(self.cal_title, True, True, 0)
        head.pack_start(self.icon_btn("left", "round", lambda: self.cal_move(-1)), False, False, 0)
        head.pack_start(self.icon_btn("right", "round", lambda: self.cal_move(1)), False, False, 0)
        c.pack_start(head, False, False, 0)
        self.cal_grid = Gtk.Grid(row_spacing=sc(4), column_spacing=sc(4))
        self.cal_grid.set_column_homogeneous(True)
        c.pack_start(self.cal_grid, False, False, 0)
        box.pack_start(c, False, False, 0)
        ec = self.card(10)
        ec.pack_start(self.lbl("AGENDA", "hl"), False, False, 0)
        self.cal_events = self.vbox(10)
        ec.pack_start(self.cal_events, False, False, 0)
        box.pack_start(ec, False, False, 0)
        self.refreshers["calendar"] = self.draw_cal
        return box

    def cal_move(self, d):
        self.cal_off += d
        self.draw_cal()

    def draw_cal(self):
        today = datetime.date.today()
        m0 = today.month - 1 + self.cal_off
        y, m = today.year + m0 // 12, m0 % 12 + 1
        self.cal_title.set_text(f"{MESES[m-1].capitalize()} {y}")
        self.clear(self.cal_grid)
        for i, n in enumerate(("seg", "ter", "qua", "qui", "sex", "sáb", "dom")):
            lb = self.lbl(n, "small", 0.5)
            lb.set_hexpand(True)
            self.cal_grid.attach(lb, i, 0, 1, 1)
        for r, week in enumerate(calendar.Calendar(0).monthdayscalendar(y, m), start=1):
            for i, d in enumerate(week):
                if not d:
                    continue
                b = Gtk.Box()
                b.get_style_context().add_class("day")
                if datetime.date(y, m, d) == today:
                    b.get_style_context().add_class("today")
                lb = self.lbl(str(d), xalign=0.5)
                lb.set_hexpand(True)
                b.pack_start(lb, True, True, 0)
                self.cal_grid.attach(b, i, r, 1, 1)
        self.cal_grid.show_all()
        self.clear(self.cal_events)
        evs = self.read_events(60)
        if not evs:
            self.cal_events.pack_start(self.lbl("Nenhum evento agendado", "small"), False, False, 0)
        for dt, t in evs[:4]:
            self.cal_events.pack_start(self.event_row(dt, t), False, False, 0)
        self.cal_events.show_all()
        GLib.idle_add(self.fit)

    def read_events(self, days):
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            evs = []
            for e in json.load(open(DATA)).get("events", []):
                dt = datetime.datetime.fromisoformat(e["data"].replace("Z", "+00:00"))
                if now - datetime.timedelta(hours=1) <= dt <= now + datetime.timedelta(days=days):
                    evs.append((dt.astimezone(), e.get("titulo", "Evento")))
            return sorted(evs)
        except Exception:
            return []

    def event_row(self, dt, title):
        r = self.hbox(12)
        bar = Gtk.Box()
        bar.get_style_context().add_class("evbar")
        bar.set_size_request(3, sc(34))
        c = self.vbox(2)
        c.pack_start(self.lbl(title, "tname", ell=True, maxc=24), False, False, 0)
        c.pack_start(self.lbl(f"{dt.day} {MESES[dt.month-1][:3]}  ·  {dt:%H:%M}", "small"), False, False, 0)
        r.pack_start(bar, False, False, 0)
        r.pack_start(c, True, True, 0)
        return r

    def page_notifs(self):
        box = self.page()
        c = self.card(12)
        head = self.hbox(10)
        head.pack_start(self.lbl("Notificações", "h2"), True, True, 0)
        self.dnd_btn = self.act_btn("dnd", "Não perturbe", lambda: (fire("noctalia", "msg", "notification-dnd-toggle"), self.later(500, self.refresh)))
        head.pack_start(self.dnd_btn, False, False, 0)
        head.pack_start(self.act_btn("trash", "Limpar", lambda: (fire("noctalia", "msg", "notification-clear-history"), self.later(500, self.refreshers["notifications"]))), False, False, 0)
        c.pack_start(head, False, False, 0)
        self.nt_box = self.vbox(8)
        c.pack_start(self.nt_box, False, False, 0)
        box.pack_start(c, False, False, 0)

        def load():
            try:
                es = json.load(open(NOTIFS)).get("entries", [])
            except Exception:
                es = []
            es = sorted(es, key=lambda e: e["notification"].get("received_wall_ms", 0), reverse=True)
            return [e["notification"] for e in es[:7]]

        def show(ns):
            self.clear(self.nt_box)
            for n in ns:
                r = self.vbox(1)
                r.get_style_context().add_class("row")
                t = datetime.datetime.fromtimestamp(n.get("received_wall_ms", 0) / 1000)
                r.pack_start(self.lbl(n.get("summary") or n.get("app_name") or "Notificação", "tname", ell=True, maxc=44), False, False, 0)
                r.pack_start(self.lbl((n.get("body") or "").replace("\n", " "), "small", ell=True, maxc=54), False, False, 0)
                r.pack_start(self.lbl(f"{t:%d/%m %H:%M}", "small"), False, False, 0)
                self.nt_box.pack_start(r, False, False, 0)
            if not ns:
                self.nt_box.pack_start(self.lbl("Sem notificações", "small"), False, False, 0)
            self.nt_box.show_all()
            GLib.idle_add(self.fit)
        self.refreshers["notifications"] = lambda: bg(load, show)
        return box

    def page_session(self):
        box = self.page("Sessão")
        grid = Gtk.Grid(row_spacing=sc(12), column_spacing=sc(12))
        grid.set_column_homogeneous(True)
        acts = [("lock", "Bloquear", "lock", False), ("sleep", "Suspender", "suspend", False), ("logout", "Sair", "logout", True),
                ("reboot", "Reiniciar", "reboot", True), ("power", "Desligar", "shutdown", True)]
        for i, (ic, text, action, danger) in enumerate(acts):
            b = Gtk.Button()
            b.get_style_context().add_class("bigbtn")
            v = self.vbox(8)
            v.pack_start(self.lbl(I[ic], "nf", 0.5), False, False, 0)
            lb = self.lbl(text, "tname", 0.5)
            v.pack_start(lb, False, False, 0)
            b.add(v)
            b.connect("clicked", lambda _b, a=action, d=danger, l=lb, t=text, btn=b: self.do_session(a, d, l, t, btn))
            grid.attach(b, i % 3, i // 3, 1, 1)
        box.pack_start(grid, False, False, 0)
        return box

    def do_session(self, action, danger, lb, text, btn):
        if danger and self.confirm.get(action, 0) < time.time():
            self.confirm[action] = time.time() + 3
            lb.set_text("Confirmar?")
            btn.get_style_context().add_class("warn")
            self.later(3000, lambda: (lb.set_text(text), btn.get_style_context().remove_class("warn")))
            return
        fire("noctalia", "msg", "session", action)
        self.close()

    # ---------- ações ----------
    def t_night(self):
        self.st["night"] = not self.st.get("night", False)
        save_state(self.st)
        fire("noctalia", "msg", "nightlight-force-toggle")
        self.render_local()

    def t_coffee(self):
        self.st["coffee"] = not self.st.get("coffee", False)
        save_state(self.st)
        fire("noctalia", "msg", "caffeine-toggle")
        self.render_local()

    def on_vol(self, s):
        if self.loading["vol"]:
            return
        n = int(s.get_value())
        for l in (self.vol_lbl, self.a_vol_lbl):
            l.set_text(f"{n}%")
        self.debounce("vol", lambda: fire("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{n/100:.2f}"))

    def on_mic(self, s):
        if self.loading["mic"]:
            return
        n = int(s.get_value())
        self.mic_lbl.set_text(f"{n}%")
        self.debounce("mic", lambda: fire("wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", f"{n/100:.2f}"))

    def on_bri(self, s):
        if self.loading["bri"]:
            return
        n = int(max(1, s.get_value()))
        for l in (self.bri_lbl, self.d_bri_lbl):
            l.set_text(f"{n}%")
        self.debounce("bri", lambda: fire("brightnessctl", "-q", "set", f"{n}%"))

    # ---------- estado ----------
    def tick_clock(self):
        if not self.visible:
            return True
        n = datetime.datetime.now()
        h = n.hour
        gr = "Bom dia" if 5 <= h < 12 else "Boa tarde" if h < 18 else "Boa noite"
        self.greet.set_text(f"{gr}, {USER_NAME}")
        temp = getattr(self, "temp_txt", "")
        self.sub.set_text(f"{DIAS[n.weekday()]}, {n.day} de {MESES[n.month-1]}  ·  {n:%H:%M}" + (f"  ·  {temp}" if temp else ""))
        return True

    def render_local(self):
        self.set_tile("night", self.st.get("night", False), "Ligada" if self.st.get("night") else "Desligada")
        self.set_tile("coffee", self.st.get("coffee", False), "Ativa" if self.st.get("coffee") else "Desativada")

    def refresh(self):
        if self.visible:
            threading.Thread(target=self.gather, daemon=True).start()
        return True

    def gather(self):
        d = {}
        d["vol"] = sh("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@")
        d["mic"] = sh("wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@")
        d["bri"] = sh("brightnessctl", "-m")
        d["wifi"] = sh("noctalia", "msg", "wifi-status")
        d["ssid"] = sh("nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi")
        d["bt"] = sh("noctalia", "msg", "bluetooth-status")
        d["btc"] = sh("bluetoothctl", "devices", "Connected")
        d["dnd"] = sh("noctalia", "msg", "notification-dnd-status")
        d["pp"] = sh("powerprofilesctl", "get")
        d["media"] = sh("playerctl", "metadata", "--format", "{{status}}|{{title}}|{{artist}}|{{album}}")
        try:
            d["bat"] = (open("/sys/class/power_supply/BAT0/capacity").read().strip(), open("/sys/class/power_supply/BAT0/status").read().strip())
        except Exception:
            d["bat"] = None
        try:
            parts = list(map(int, open("/proc/stat").readline().split()[1:8]))
            idle, tot = parts[3] + parts[4], sum(parts)
            if self.cpu_prev:
                di, dt = idle - self.cpu_prev[0], tot - self.cpu_prev[1]
                d["cpu"] = int(100 * (1 - di / dt)) if dt else 0
            self.cpu_prev = (idle, tot)
            mi = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
            d["ram"] = int(100 * (1 - mi["MemAvailable"] / mi["MemTotal"]))
            d["up"] = float(open("/proc/uptime").read().split()[0])
            t = sh("sh", "-c", "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | sort -n | tail -1")
            d["temp"] = int(t) // 1000 if t else None
            du = shutil.disk_usage("/")
            d["disk"] = int(100 * du.used / du.total)
        except Exception:
            pass
        try:
            d["weather"] = f"{round(json.load(open(WEATHER))['snapshot']['current']['temperature_c'])}°C"
        except Exception:
            d["weather"] = ""
        d["events"] = self.read_events(365)[:2]
        GLib.idle_add(self.apply, d)

    def apply(self, d):
        try:
            v = d["vol"]
            if v.startswith("Volume:"):
                n = round(float(v.split()[1]) * 100)
                muted = "MUTED" in v
                self.loading["vol"] = True
                self.vol_sc.set_value(n)
                self.a_vol_sc.set_value(n)
                self.loading["vol"] = False
                self.vol_lbl.set_text(f"{n}%")
                self.a_vol_lbl.set_text(f"{n}%")
                for ic in (self.vol_ic, self.a_vol_ic):
                    ic.get_child().set_text(I["mute" if muted else "vol"])
            mv = d["mic"]
            if mv.startswith("Volume:"):
                n = round(float(mv.split()[1]) * 100)
                self.loading["mic"] = True
                self.mic_sc.set_value(n)
                self.loading["mic"] = False
                self.mic_lbl.set_text(f"{n}%")
                self.mic_ic.get_child().set_text(I["micoff" if "MUTED" in mv else "mic"])
            b = d["bri"].split(",")
            if len(b) > 3:
                n = int(b[3].rstrip("%"))
                self.loading["bri"] = True
                self.bri_sc.set_value(n)
                self.d_bri_sc.set_value(n)
                self.loading["bri"] = False
                self.bri_lbl.set_text(f"{n}%")
                self.d_bri_lbl.set_text(f"{n}%")
            wifi = "on" in d["wifi"].lower() or "enabled" in d["wifi"].lower()
            ssid = next((l.split(":", 1)[1] for l in d["ssid"].splitlines() if l.startswith("yes:")), "")
            bt_on = "on" in d["bt"].lower() or "enabled" in d["bt"].lower() or "powered" in d["bt"].lower()
            nbt = len([l for l in d["btc"].splitlines() if l.strip()])
            self.set_tile("wifi", wifi, (ssid or "Conectado") if wifi else "Desligado")
            self.set_tile("bt", bt_on, (f"{nbt} conectado(s)" if nbt else "Ligado") if bt_on else "Desligado")
            dnd = d["dnd"].strip().lower() in ("on", "true", "enabled", "1")
            self.set_tile("dnd", dnd, "Ativo" if dnd else "Desligado")
            self.set_tile("perf", d["pp"] == "performance", PERFIS.get(d["pp"], d["pp"] or "--"))
            self.render_local()
            for k, r in self.prof_rows.items():
                (r.get_style_context().add_class if d["pp"] == k else r.get_style_context().remove_class)("on")
            if d.get("bat"):
                pct, state = d["bat"]
                self.bat.set_text(f"{pct}%")
                self.p_pct.set_text(f"{pct}%")
                self.p_bar.set_fraction(int(pct) / 100)
                self.p_state_base = {"Charging": "Carregando", "Discharging": "Descarregando", "Full": "Carga completa"}.get(state, state)
                if self.cur != "power":
                    self.p_state.set_text(self.p_state_base)
            self.temp_txt = d.get("weather", "")
            m = d["media"].split("|")
            if len(m) >= 4 and m[1]:
                self.m_title.set_text(m[1])
                self.m_art.set_text(m[2] or "—")
                self.mp_title.set_text(m[1])
                self.mp_artist.set_text(m[2])
                self.mp_album.set_text(m[3])
                gl = I["pause" if m[0] == "Playing" else "play"]
            else:
                self.m_title.set_text("Nada tocando")
                self.m_art.set_text("Ocioso")
                self.mp_title.set_text("Nada tocando")
                self.mp_artist.set_text("")
                self.mp_album.set_text("")
                gl = I["play"]
            for pb in (self.play_home, self.play_page):
                pb.get_child().set_text(gl)
            if "cpu" in d:
                self.chips["cpu"].set_text(f"CPU {d['cpu']}%")
                self.sys_bars["cpu"][0].set_fraction(d["cpu"] / 100)
                self.sys_bars["cpu"][1].set_text(f"{d['cpu']}%")
            if "ram" in d:
                self.chips["ram"].set_text(f"RAM {d['ram']}%")
                self.sys_bars["ram"][0].set_fraction(d["ram"] / 100)
                self.sys_bars["ram"][1].set_text(f"{d['ram']}%")
            if "disk" in d:
                self.sys_bars["disk"][0].set_fraction(d["disk"] / 100)
                self.sys_bars["disk"][1].set_text(f"{d['disk']}%")
            if d.get("temp"):
                self.chips["temp"].set_text(f"{d['temp']}°C")
                self.sys_bars["temp"][0].set_fraction(min(1, d["temp"] / 100))
                self.sys_bars["temp"][1].set_text(f"{d['temp']}°C")
            if "up" in d:
                s = int(d["up"])
                self.chips["up"].set_text(f"ativo {s//86400}d {s%86400//3600}h" if s >= 86400 else f"ativo {s//3600}h {s%3600//60}m")
            self.clear(self.ev_box)
            for dt, title in d["events"]:
                self.ev_box.pack_start(self.event_row(dt, title), False, False, 0)
            if not d["events"]:
                self.ev_box.pack_start(self.lbl("Nenhum evento agendado", "small"), False, False, 0)
            self.ev_box.show_all()
            ctx = self.dnd_btn.get_style_context()
            (ctx.add_class if dnd else ctx.remove_class)("warn")
        except Exception as e:
            print("apply:", repr(e), flush=True)
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            json.dump({k: v for k, v in d.items() if k != "events"}, open(CACHE, "w"))
        except Exception:
            pass
        self.tick_clock()
        return False


def main():
    daemon = "--daemon" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pidf = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-cc.pid")
    monf = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-cc.mon")
    if daemon:
        try:
            os.kill(int(open(pidf).read()), 0)
            sys.exit(0)
        except Exception:
            pass
    open(pidf, "w").write(str(os.getpid()))
    p = Panel(daemon=daemon)

    def mon():
        try:
            return open(monf).read().strip() or None
        except OSError:
            return None

    pagef = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-cc.page")

    def page():
        try:
            return open(pagef).read().strip() or None
        except OSError:
            return None

    def toggle():
        if daemon:
            p.close() if p.visible else p.open_panel(mon(), page())
        else:
            p.close()
        return True
    if args:
        GLib.timeout_add(500, lambda: (p.goto(args[0]), False)[1])
    if daemon and "--open" in sys.argv:
        GLib.idle_add(lambda: (p.open_panel(mon(), page()), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, toggle)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    for f in (pidf,):
        try:
            os.remove(f)
        except OSError:
            pass


if __name__ == "__main__":
    main()
