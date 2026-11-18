#!/usr/bin/env python3
"""Ilha Entropy: pílula minúscula (hora + bateria) no topo. Aparece na área de trabalho vazia ou ao passar o mouse no topo; clique abre o painel."""
import importlib.util, json, math, os, re, signal, socket, subprocess, sys, threading
import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("entropy_cc", os.path.join(HERE, "entropy-cc.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
PAL, hex2rgb, NF, sh = cc.PAL, cc.hex2rgb, cc.NF, cc.sh

APP = None
PIDF = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-island.pid")
CCPID = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-cc.pid")
TOGGLE = os.path.join(HERE, "entropy-cc-toggle")
BATT = [0xF007A, 0xF007B, 0xF007C, 0xF007D, 0xF007E, 0xF007F, 0xF0080, 0xF0081, 0xF0082, 0xF0079]
EDGE = 3
EXTRA = 34   # espaço abaixo da pílula para o balanço elástico


def css():
    fg, su = hex2rgb(PAL["fg"]), hex2rgb(PAL["surface"])
    try:
        a = float(open(cc.ALPHA).read().strip())
    except Exception:
        a = 0.38
    tint = min(0.80, 0.40 + (a - 0.38) * 0.8)
    return f"""
window {{ background: transparent; }}
.isl {{ background-color: rgba({su[0]},{su[1]},{su[2]},{tint:.2f}); border: 1px solid rgba({fg[0]},{fg[1]},{fg[2]},0.14); border-radius: 999px; padding: 2px 11px; transition: all 140ms ease; }}
._isl_unused {{ background-color: rgba({su[0]},{su[1]},{su[2]},{min(0.92, tint + 0.14):.2f}); }}
.isl label {{ color: {PAL['fg']}; font-size: 12px; font-weight: 600; }}
.isl .nf {{ font-family: '{NF}'; font-size: 13px; color: {PAL['primary']}; }}
.isl.plain {{ background-color: transparent; border-color: transparent; }}
.dot {{ background: rgba({fg[0]},{fg[1]},{fg[2]},0.35); border-radius: 999px; min-width: 3px; min-height: 3px; }}
"""


def battery():
    try:
        pct = int(open("/sys/class/power_supply/BAT0/capacity").read())
        st = open("/sys/class/power_supply/BAT0/status").read().strip()
    except Exception:
        return None
    glyph = 0xF0084 if st == "Charging" else BATT[min(9, pct // 10)]
    return chr(glyph), pct


def panel_open():
    for name in ("entropy-cc.open", "entropy-launcher.open"):
        try:
            if open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), name)).read().strip() == "1":
                return True
        except Exception:
            pass
    return False


class Island:
    FLARE = 30   # abertura lateral (curva côncava até a borda do topo)
    WAVE = 170   # de quão longe, de cada lado, a onda começa

    def __init__(self, gmon, name):
        self.name, self.shown, self.token = name, False, 0
        self.hover_isl = self.hover_zone = False
        self.leave_t = 0
        self.snap, self.hov, self.fa = None, 0.0, 1.0
        self.hw, self.D, self.f, self.ca = 65.0, 31.0, 30.0, 1.0
        su, fg = cc.hex2rgb(PAL["surface"]), cc.hex2rgb(PAL["fg"])
        try:
            a = float(open(cc.ALPHA).read().strip())
        except Exception:
            a = 0.38
        self.tint = (su[0] / 255, su[1] / 255, su[2] / 255, min(0.80, 0.40 + (a - 0.38) * 0.8))
        self.fgc = (fg[0] / 255, fg[1] / 255, fg[2] / 255)
        win = self.win = Gtk.Window()
        win.set_app_paintable(True)
        vis = win.get_screen().get_rgba_visual()
        if vis:
            win.set_visual(vis)
        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "entropy-island")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_exclusive_zone(win, -1)
        GtkLayerShell.set_monitor(win, gmon)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 0)
        box = self.box = Gtk.Box(spacing=8)
        box.get_style_context().add_class("isl")
        box.get_style_context().add_class("plain")
        self.clock = Gtk.Label(label="--:--")
        dot = Gtk.Box()
        dot.get_style_context().add_class("dot")
        dot.set_valign(Gtk.Align.CENTER)
        self.bat_ic = Gtk.Label(label="")
        self.bat_ic.get_style_context().add_class("nf")
        self.bat = Gtk.Label(label="")
        for w in (self.clock, dot, self.bat_ic, self.bat):
            box.pack_start(w, False, False, 0)
        eb = self.eb = Gtk.EventBox()
        eb.set_visible_window(False)
        eb.add(box)
        eb.set_halign(Gtk.Align.CENTER)
        eb.set_valign(Gtk.Align.START)
        eb.set_margin_top(EDGE)
        evmask = Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
        area = self.area = Gtk.DrawingArea()
        win.add_events(evmask)
        win.connect("button-press-event", lambda *_: (self.open(), True)[1])
        win.connect("enter-notify-event", lambda w, e: self.set_isl(True))
        win.connect("leave-notify-event", lambda w, e: (None if e.detail == Gdk.NotifyType.INFERIOR else self.set_isl(False)))
        self.hov_t = 0.0
        self.rip = (0.0, 0.0)
        area.connect("draw", self.on_draw)
        ov = Gtk.Overlay()
        ov.add(area)
        ov.add_overlay(eb)
        win.add(ov)
        self.update()
        self.pw, self.ph = 130, 28
        self.W, self.H = 130 + 2 * (170 + 30 + 12), EDGE + 28 + EXTRA
        area.set_size_request(self.W, self.H)
        eb.set_opacity(0.0)
        win.set_opacity(0.0)
        # zona de revelar no topo (fina e transparente)
        hz = self.hz = Gtk.Window()
        hz.set_app_paintable(True)
        if vis:
            hz.set_visual(vis)
        GtkLayerShell.init_for_window(hz)
        GtkLayerShell.set_namespace(hz, "entropy-island-hz")
        GtkLayerShell.set_layer(hz, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(hz, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_exclusive_zone(hz, -1)
        GtkLayerShell.set_monitor(hz, gmon)
        hz.set_size_request(260, 3)
        hz.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        hz.connect("enter-notify-event", lambda *_: self.set_zone(True))
        hz.connect("leave-notify-event", lambda *_: self.set_zone(False))
        hz.show_all()

    def set_isl(self, v):
        self.hover_isl = v
        self.leave_t = GLib.get_monotonic_time()
        self.hov_t = 1.0 if v else 0.0
        if not getattr(self, "hov_run", False):
            self.hov_run = True
            GLib.timeout_add(16, self.hov_step)
        self.poke(v)

    def hov_step(self):
        d = self.hov_t - self.hov
        if abs(d) < 0.02:
            self.hov = self.hov_t
            self.hov_run = False
            self.area.queue_draw()
            return False
        self.hov += d * 0.28
        self.area.queue_draw()
        return True

    def set_zone(self, v):
        self.hover_zone = v
        self.leave_t = GLib.get_monotonic_time()
        self.poke(v)

    def poke(self, entering):
        if entering:
            if not panel_open():
                self.set_shown(True)
        else:
            GLib.timeout_add(430, lambda: (APP.tick(), False)[1])

    def hovering(self):
        if self.hover_isl or self.hover_zone:
            return True
        return (GLib.get_monotonic_time() - self.leave_t) < 400000

    def open(self):
        self.hide_instant()
        subprocess.Popen([TOGGLE, self.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def update(self):
        self.clock.set_text(__import__("datetime").datetime.now().strftime("%H:%M"))
        b = battery()
        if b:
            self.bat_ic.set_text(b[0])
            self.bat.set_text(f"{b[1]}%")

    # ---------- forma líquida permanente ----------
    def smooth(self, a, b, x):
        t = max(0.0, min(1.0, (x - a) / (b - a)))
        return t * t * (3 - 2 * t)

    @staticmethod
    def back(t, k=1.0):
        t -= 1.0
        return 1.0 + (k + 1.0) * t ** 3 + k * t ** 2

    def snapshot(self):
        w, h = self.box.get_allocated_width(), self.box.get_allocated_height()
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, w), max(1, h))
        self.box.draw(cairo.Context(surf))
        return surf

    def params(self, u, opening):
        """uma só forma: lente larga que se contrai das laterais ao centro, ondulando, e assenta em pílula"""
        pw, ph = self.pw, self.ph
        Df = EDGE + ph
        if opening:
            e = self.smooth(0.0, 0.82, u)
            hw = (pw / 2 + self.WAVE) + (pw / 2 - (pw / 2 + self.WAVE)) * self.back(e, 1.0)
            v = self.smooth(0.10, 1.0, u)
            D = Df * (1.0 - math.exp(-5.5 * v) * math.cos(8.0 * v)) if v > 0 else 0.0
            f = self.FLARE * self.smooth(0.25, 1.0, u)
            ca = self.smooth(0.66, 0.97, u)
            fa = self.smooth(0.0, 0.14, u)
            g = self.smooth(0.30, 1.0, u)
            amp = 6.0 * self.smooth(0.04, 0.25, u) * (1.0 - self.smooth(0.35, 1.0, u))
            ph_ = 16.0 * u
        else:
            hw = pw / 2 + self.WAVE * self.smooth(0.15, 1.0, u)
            D = Df * (1.0 - self.smooth(0.0, 0.85, u))
            f = self.FLARE * (1.0 - self.smooth(0.0, 0.5, u))
            ca = 1.0 - self.smooth(0.0, 0.35, u)
            fa = 1.0 - self.smooth(0.80, 1.0, u)
            g = 1.0 - self.smooth(0.0, 0.7, u)
            amp = 4.0 * self.smooth(0.05, 0.3, u) * (1.0 - self.smooth(0.5, 1.0, u))
            ph_ = -10.0 * u
        self.g, self.rip = g, (amp, ph_)
        return hw, max(D, 0.0), f, ca, fa

    def on_draw(self, w, cr):
        cx = w.get_allocated_width() / 2.0
        hw, D, f, ca = self.hw, self.D, self.f, self.ca
        h = self.hov
        settled = self.fa >= 0.99 and self.ca >= 0.99
        if settled:
            hw, D = hw + 5.0 * h, D + 2.5 * h
        if D < 0.6:
            return False
        g = getattr(self, "g", 1.0) if not settled else 1.0
        r = self.ph / 2.0
        rx = max(2.0, min(hw, r + (hw - r) * (1.0 - g)))
        ry = max(1.0, min(D, r + (D - r) * (1.0 - g)))
        x0, x1 = cx - hw, cx + hw
        yb = D - ry
        yf = min(0.55 * D, 22.0, max(1.0, yb))
        amp, pphase = self.rip
        k = 2 * math.pi / 70.0

        def rip(x):
            if amp < 0.05:
                return 0.0
            return amp * math.sin(k * (hw - abs(x - cx)) * 1.0 - pphase) * min(1.0, D / 14.0)

        def outline(close):
            cr.new_path()
            cr.move_to(x0 - f, 0)
            cr.curve_to(x0 - f * 0.45, 0, x0, yf * 0.42, x0, yf)
            cr.line_to(x0, yb)
            n = 14
            for i in range(1, n + 1):
                a = math.pi - (math.pi / 2) * i / n
                x, y = x0 + rx + rx * math.cos(a), yb + ry * math.sin(a)
                cr.line_to(x, y + rip(x) * (i / n))
            m = max(2, int((x1 - rx - (x0 + rx)) / 8))
            for i in range(1, m):
                x = x0 + rx + (x1 - rx - x0 - rx) * i / m
                cr.line_to(x, D + rip(x))
            for i in range(0, n + 1):
                a = (math.pi / 2) - (math.pi / 2) * i / n
                x, y = x1 - rx + rx * math.cos(a), yb + ry * math.sin(a)
                cr.line_to(x, y + rip(x) * (1 - i / n))
            cr.line_to(x1, yf)
            cr.curve_to(x1, yf * 0.42, x1 + f * 0.45, 0, x1 + f, 0)
            if close:
                cr.close_path()

        alpha = (self.tint[3] + 0.14 * h) * self.fa
        cr.push_group()
        cr.set_source_rgb(*self.tint[:3])
        outline(True)
        cr.fill()
        cr.pop_group_to_source()
        cr.paint_with_alpha(alpha)
        outline(False)
        cr.set_source_rgba(self.fgc[0], self.fgc[1], self.fgc[2], (0.14 + 0.16 * h) * self.fa * min(1.0, ca + 0.4))
        cr.set_line_width(1.0)
        cr.stroke()
        if self.snap is not None and ca > 0.01 and self.eb.get_opacity() < 0.5:
            cr.set_source_surface(self.snap, cx - self.pw / 2.0, EDGE)
            cr.paint_with_alpha(ca)
        return False

    def set_input(self, empty=False):
        try:
            if empty:
                reg = cairo.Region()
            else:
                cx = self.W / 2.0
                wt = self.pw + 2 * self.FLARE + 16
                reg = cairo.Region(cairo.RectangleInt(int(cx - wt / 2), 0, int(wt) + 1, int(EDGE + self.ph) + 6))
            self.win.get_window().input_shape_combine_region(reg, 0, 0)
        except Exception:
            pass

    def hide_instant(self):
        if not self.shown:
            return
        self.shown = False
        self.token += 1
        self.win.hide()

    def show_instant(self):
        if self.shown:
            return
        self.shown = True
        self.token += 1
        self.update()
        self.win.show_all()
        self.measure()
        self.hw, self.D, self.f, self.ca, self.fa = self.pw / 2, EDGE + self.ph, self.FLARE, 1.0, 1.0
        self.eb.set_opacity(1.0)
        self.win.set_opacity(1.0)
        self.area.queue_draw()
        self.set_input()

    def set_shown(self, v, instant=False):
        if v == self.shown:
            return
        if v and instant:
            self.show_instant()
            return
        self.shown = v
        self.token += 1
        tk = self.token
        if v:
            self.update()
            self.win.set_opacity(0.0)
            self.eb.set_opacity(0.0)
            self.hw, self.D, self.f, self.ca, self.fa = self.pw / 2 + self.WAVE, 0.0, 0.0, 0.0, 0.0
            self.win.show_all()
            GLib.timeout_add(50, lambda: (self.start_open(tk), False)[1])
        else:
            self.start_close(tk)

    def measure(self):
        pw, ph = self.box.get_preferred_width()[1], self.box.get_preferred_height()[1]
        if pw > 20 and (pw != self.pw or ph != self.ph):
            self.pw, self.ph = pw, ph
            self.W, self.H = pw + 2 * (self.WAVE + self.FLARE + 12), EDGE + ph + EXTRA
            self.area.set_size_request(self.W, self.H)
            try:
                open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "entropy-island.geom"), "w").write(f"{pw} {ph}")
            except OSError:
                pass

    def start_open(self, tk):
        if tk != self.token:
            return
        self.measure()
        GLib.timeout_add(60, lambda: (self.start_open2(tk), False)[1])

    def start_open2(self, tk):
        if tk != self.token:
            return
        self.snap = self.snapshot()
        self.set_input(empty=True)
        self.win.set_opacity(1.0)
        t0 = GLib.get_monotonic_time()

        def step():
            if tk != self.token:
                return False
            u = min(1.0, (GLib.get_monotonic_time() - t0) / 950000.0)
            self.hw, self.D, self.f, self.ca, self.fa = self.params(u, True)
            self.area.queue_draw()
            if u >= 1.0:
                self.hw, self.D, self.f, self.ca, self.fa = self.pw / 2, EDGE + self.ph, self.FLARE, 1.0, 1.0
                self.g, self.rip = 1.0, (0.0, 0.0)
                self.eb.set_opacity(1.0)
                self.area.queue_draw()
                self.set_input()
                return False
            return True
        GLib.timeout_add(16, step)

    def start_close(self, tk):
        try:
            self.snap = self.snapshot()
        except Exception:
            self.win.hide()
            return
        self.eb.set_opacity(0.0)
        self.set_input(empty=True)
        t0 = GLib.get_monotonic_time()

        def step():
            if tk != self.token:
                return False
            r = min(1.0, (GLib.get_monotonic_time() - t0) / 520000.0)
            self.hw, self.D, self.f, self.ca, self.fa = self.params(r, False)
            self.area.queue_draw()
            if r >= 1.0:
                self.win.hide()
                return False
            return True
        GLib.timeout_add(16, step)


class App:
    def __init__(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(css().encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.islands = {}
        disp = Gdk.Display.get_default()
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
        except Exception:
            mons = []
        for i in range(disp.get_n_monitors()):
            gm = disp.get_monitor(i).get_geometry()
            for m in mons:
                if gm.x == int(m["x"]) and gm.y == int(m["y"]):
                    self.islands[m["name"]] = Island(disp.get_monitor(i), m["name"])
        self.pending = False
        self.was_busy = False
        GLib.timeout_add(110, self.check_busy)
        GLib.timeout_add(1500, self.tick)
        GLib.timeout_add(15000, self.tick_slow)
        threading.Thread(target=self.listen, daemon=True).start()
        self.tick()

    def schedule(self):
        if not self.pending:
            self.pending = True
            GLib.timeout_add(25, lambda: (setattr(self, "pending", False), self.tick(), False)[2])

    def listen(self):
        try:
            path = f"{os.environ['XDG_RUNTIME_DIR']}/hypr/{os.environ['HYPRLAND_INSTANCE_SIGNATURE']}/.socket2.sock"
            sk = socket.socket(socket.AF_UNIX)
            sk.connect(path)
            buf = b""
            while True:
                data = sk.recv(4096)
                if not data:
                    break
                buf += data
                *lines, buf = buf.split(b"\n")
                for ln in lines:
                    ev = ln.split(b">>", 1)[0]
                    if ev in (b"openwindow", b"closewindow", b"movewindow", b"movewindowv2", b"workspace", b"workspacev2",
                              b"focusedmon", b"focusedmonv2", b"monitoradded", b"monitorremoved", b"fullscreen"):
                        GLib.idle_add(self.schedule)
        except Exception as e:
            print("listen:", repr(e), flush=True)

    def check_busy(self):
        b = panel_open()
        if b != self.was_busy:
            self.was_busy = b
            if b:
                for isl in self.islands.values():
                    isl.hide_instant()
            else:
                self.tick(instant=True)
        return True

    def tick_slow(self):
        for isl in self.islands.values():
            isl.update()
        return True

    def tick(self, instant=False):
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
            clients = json.loads(sh("hyprctl", "clients", "-j"))
        except Exception:
            return True
        busy = panel_open()
        for m in mons:
            isl = self.islands.get(m["name"])
            if not isl:
                continue
            wsid = m["activeWorkspace"]["id"]
            n = sum(1 for c in clients if c["workspace"]["id"] == wsid and c.get("mapped") and not c.get("hidden"))
            want = (n == 0 or isl.hovering() or bool(os.environ.get("ENTROPY_ISLAND_FORCE"))) and not busy
            if busy:
                isl.hide_instant()
            else:
                isl.set_shown(want, instant)
        return True


def main():
    if os.path.exists(PIDF):
        try:
            os.kill(int(open(PIDF).read()), 0)
            sys.exit(0)
        except Exception:
            pass
    open(PIDF, "w").write(str(os.getpid()))
    global APP
    APP = App()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    try:
        os.remove(PIDF)
    except OSError:
        pass


if __name__ == "__main__":
    main()
