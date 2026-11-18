#!/usr/bin/env python3
"""Dock Entropy: ilha embaixo (espelho da ilha de cima). Sai de baixo da tela como onda quando a área de trabalho está vazia
ou ao passar o mouse na borda; o ícone de apps expande a própria ilha no menu de apps."""
import importlib.util, json, math, os, re, signal, socket, subprocess, sys, threading
import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("entropy_cc", os.path.join(HERE, "entropy-cc.py"))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)
PAL, hex2rgb, sh = cc.PAL, cc.hex2rgb, cc.sh

RT = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
APP = None
PIDF = os.path.join(RT, "entropy-dock.pid")
GEOM = os.path.join(RT, "entropy-dock.geom")
SNAPF = os.path.join(RT, "entropy-dock.png")
LAUNCH = os.path.join(HERE, "entropy-launcher-toggle")
EDGE = 3
EXTRA = 34
ICON = 30


def css():
    fg, su = hex2rgb(PAL["fg"]), hex2rgb(PAL["surface"])
    return f"""
window {{ background: transparent; }}
.dk {{ padding: 6px 12px 6px 12px; }}
button.dkb {{ background: none; border: none; box-shadow: none; padding: 5px 6px 2px 6px; border-radius: 14px; min-height: 0; min-width: 0; }}
button.dkb:hover {{ background-color: rgba({fg[0]},{fg[1]},{fg[2]},0.10); }}
.rdot {{ background: transparent; border-radius: 999px; min-width: 4px; min-height: 4px; }}
.rdot.on {{ background: {PAL['primary']}; }}
"""


def panel_open():
    for name in ("entropy-cc.open", "entropy-launcher.open"):
        try:
            if open(os.path.join(RT, name)).read().strip() == "1":
                return True
        except Exception:
            pass
    return False


def pinned_ids():
    ids = None
    for path in (os.path.expanduser("~/.local/state/noctalia/settings.toml"), os.path.expanduser("~/.config/noctalia/config.toml")):
        try:
            txt = open(path).read()
            m = re.search(r"\[dock\][\s\S]*?\npinned\s*=\s*\[([\s\S]*?)\]", txt)
            if m:
                ids = re.findall(r'"([^"]+)"', m.group(1))
                break
        except OSError:
            pass
    return ids or ["entropy-apps", "kitty", "org.gnome.Nautilus", "firefox"]


class Item:
    def __init__(self, ident, app, classes):
        self.id, self.app, self.classes, self.running = ident, app, classes, 0


def build_items(clients):
    items = []
    seen = set()
    for ident in pinned_ids():
        app = Gio.DesktopAppInfo.new(ident + ".desktop")
        if app is None:
            continue
        wm = (app.get_startup_wm_class() or "").lower()
        cls = {ident.lower(), ident.split(".")[-1].lower(), wm} - {""}
        items.append(Item(ident, app, cls))
        seen.add(ident)
    for c in clients:
        k = (c.get("class") or "").lower()
        if not k or not c.get("mapped", True):
            continue
        hit = next((it for it in items if k in it.classes), None)
        if hit:
            hit.running += 1
        elif ("x:" + k) not in seen:
            seen.add("x:" + k)
            app = None
            for a in Gio.AppInfo.get_all():
                if (a.get_startup_wm_class() or "").lower() == k or a.get_id().lower().replace(".desktop", "") == k:
                    app = a
                    break
            if app is not None:
                it = Item(k, app, {k})
                it.running = 1
                items.append(it)
    return items


class Dock:
    FLARE = 30
    WAVE = 170

    def __init__(self, gmon, name):
        self.name, self.shown, self.token = name, False, 0
        self.hover_isl = self.hover_zone = False
        self.leave_t = 0
        self.snap, self.hov, self.hov_t, self.fa = None, 0.0, 0.0, 1.0
        self.hov_run = False
        self.hw, self.D, self.f, self.ca, self.g = 140.0, 40.0, 30.0, 1.0, 1.0
        self.rip = (0.0, 0.0)
        self.key = None
        su, fg = hex2rgb(PAL["surface"]), hex2rgb(PAL["fg"])
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
        GtkLayerShell.set_namespace(win, "entropy-dock")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_exclusive_zone(win, -1)
        GtkLayerShell.set_monitor(win, gmon)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.BOTTOM, 0)
        box = self.box = Gtk.Box(spacing=4)
        box.get_style_context().add_class("dk")
        eb = self.eb = Gtk.EventBox()
        eb.set_visible_window(False)
        eb.add(box)
        eb.set_halign(Gtk.Align.CENTER)
        eb.set_valign(Gtk.Align.END)
        eb.set_margin_bottom(EDGE)
        win.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        win.connect("enter-notify-event", lambda w, e: self.set_isl(True))
        win.connect("leave-notify-event", lambda w, e: (None if e.detail == Gdk.NotifyType.INFERIOR else self.set_isl(False)))
        area = self.area = Gtk.DrawingArea()
        area.connect("draw", self.on_draw)
        ov = Gtk.Overlay()
        ov.add(area)
        ov.add_overlay(eb)
        win.add(ov)
        self.pw, self.ph = 300, 56
        self.W, self.H = self.pw + 2 * (self.WAVE + self.FLARE + 12), EDGE + self.ph + EXTRA
        area.set_size_request(self.W, self.H)
        eb.set_opacity(0.0)
        win.set_opacity(0.0)
        hz = self.hz = Gtk.Window()
        hz.set_app_paintable(True)
        if vis:
            hz.set_visual(vis)
        GtkLayerShell.init_for_window(hz)
        GtkLayerShell.set_namespace(hz, "entropy-dock-hz")
        GtkLayerShell.set_layer(hz, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(hz, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_exclusive_zone(hz, -1)
        GtkLayerShell.set_monitor(hz, gmon)
        hz.set_size_request(320, 3)
        hz.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        hz.connect("enter-notify-event", lambda *_: self.set_zone(True))
        hz.connect("leave-notify-event", lambda *_: self.set_zone(False))
        hz.show_all()

    # ---------- itens ----------
    def rebuild(self, items):
        key = tuple((it.id, bool(it.running)) for it in items)
        if key == self.key:
            return False
        self.key = key
        for c in self.box.get_children():
            self.box.remove(c)
        for it in items:
            b = Gtk.Button()
            b.get_style_context().add_class("dkb")
            b.set_relief(Gtk.ReliefStyle.NONE)
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            if it.id == "entropy-apps":
                img = Gtk.Image.new_from_icon_name("entropy-apps", Gtk.IconSize.DIALOG)
            else:
                ic = it.app.get_icon()
                img = Gtk.Image.new_from_gicon(ic, Gtk.IconSize.DIALOG) if ic else Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DIALOG)
            img.set_pixel_size(ICON)
            dot = Gtk.Box()
            dot.set_halign(Gtk.Align.CENTER)
            dot.get_style_context().add_class("rdot")
            if it.running:
                dot.get_style_context().add_class("on")
            v.pack_start(img, False, False, 0)
            v.pack_start(dot, False, False, 0)
            b.add(v)
            b.set_tooltip_text(it.app.get_name())
            b.connect("clicked", lambda _b, it=it: self.activate(it))
            self.box.pack_start(b, False, False, 0)
        self.box.show_all()
        return True

    def activate(self, it):
        if it.id == "entropy-apps":
            self.hide_instant()
            subprocess.Popen([LAUNCH, self.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return
        if it.running:
            cls = next(iter(it.classes - {""}), "")
            try:
                clients = json.loads(sh("hyprctl", "clients", "-j"))
                for c in clients:
                    if (c.get("class") or "").lower() in it.classes:
                        subprocess.Popen(["hyprctl", "dispatch", "focuswindow", f"address:{c['address']}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return
            except Exception:
                pass
        try:
            it.app.launch([], None)
        except Exception:
            pass

    # ---------- hover ----------
    def set_isl(self, v):
        self.hover_isl = v
        self.leave_t = GLib.get_monotonic_time()
        self.hov_t = 1.0 if v else 0.0
        if not self.hov_run:
            self.hov_run = True
            GLib.timeout_add(16, self.hov_step)
        self.poke(v)

    def hov_step(self):
        d = self.hov_t - self.hov
        if abs(d) < 0.02:
            self.hov, self.hov_run = self.hov_t, False
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
                APP.tick()
        else:
            GLib.timeout_add(430, lambda: (APP.tick(), False)[1])

    def hovering(self):
        if self.hover_isl or self.hover_zone:
            return True
        return (GLib.get_monotonic_time() - self.leave_t) < 400000

    # ---------- forma ----------
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

    def save_snap(self):
        try:
            if self.shown and self.win.get_mapped() and self.win.get_opacity() > 0.9 and self.box.get_allocated_width() > 20:
                self.snapshot().write_to_png(SNAPF)
        except Exception:
            pass

    def params(self, u, opening):
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
        Hh = float(w.get_allocated_height())
        hw, D, f, ca = self.hw, self.D, self.f, self.ca
        h = self.hov
        settled = self.fa >= 0.99 and self.ca >= 0.99
        if settled:
            hw, D = hw + 5.0 * h, D + 2.5 * h
        if D < 0.6:
            return False
        g = self.g if not settled else 1.0
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
            return amp * math.sin(k * (hw - abs(x - cx)) - pphase) * min(1.0, D / 14.0)

        def outline(close):
            m0 = cr.get_matrix()
            cr.translate(0, Hh)
            cr.scale(1, -1)
            cr.new_path()
            cr.move_to(x0 - f, 0)
            cr.curve_to(x0 - f * 0.45, 0, x0, yf * 0.42, x0, yf)
            cr.line_to(x0, yb)
            n = 14
            for i in range(1, n + 1):
                a = math.pi - (math.pi / 2) * i / n
                x, y = x0 + rx + rx * math.cos(a), yb + ry * math.sin(a)
                cr.line_to(x, y + rip(x) * (i / n))
            mm = max(2, int((x1 - rx - (x0 + rx)) / 8))
            for i in range(1, mm):
                x = x0 + rx + (x1 - rx - x0 - rx) * i / mm
                cr.line_to(x, D + rip(x))
            for i in range(0, n + 1):
                a = (math.pi / 2) - (math.pi / 2) * i / n
                x, y = x1 - rx + rx * math.cos(a), yb + ry * math.sin(a)
                cr.line_to(x, y + rip(x) * (1 - i / n))
            cr.line_to(x1, yf)
            cr.curve_to(x1, yf * 0.42, x1 + f * 0.45, 0, x1 + f, 0)
            if close:
                cr.close_path()
            cr.set_matrix(m0)

        alpha = (self.tint[3] + 0.10 * h) * self.fa
        cr.push_group()
        cr.set_source_rgb(*self.tint[:3])
        outline(True)
        cr.fill()
        cr.pop_group_to_source()
        cr.paint_with_alpha(alpha)
        # aro de vidro (aberração cromática)
        sa = self.fa * min(1.0, ca + 0.4)
        for dx, dy, col in ((-1.0, 0.6, (1.0, 0.35, 0.45, 0.28)), (1.0, -0.6, (0.35, 0.65, 1.0, 0.28))):
            cr.save()
            cr.translate(dx, dy)
            outline(False)
            cr.set_source_rgba(col[0], col[1], col[2], col[3] * sa)
            cr.set_line_width(1.3)
            cr.stroke()
            cr.restore()
        outline(False)
        cr.set_source_rgba(self.fgc[0], self.fgc[1], self.fgc[2], (0.18 + 0.14 * h) * sa)
        cr.set_line_width(1.0)
        cr.stroke()
        if self.snap is not None and ca > 0.01 and self.eb.get_opacity() < 0.5:
            cr.set_source_surface(self.snap, cx - self.pw / 2.0, Hh - EDGE - self.snap.get_height())
            cr.paint_with_alpha(ca)
        return False

    def set_input(self, empty=False):
        try:
            if empty:
                reg = cairo.Region()
            else:
                cx = self.W / 2.0
                wt = self.pw + 2 * self.FLARE + 16
                hh = int(EDGE + self.ph) + 6
                reg = cairo.Region(cairo.RectangleInt(int(cx - wt / 2), int(self.H - hh), int(wt) + 1, hh))
            self.win.get_window().input_shape_combine_region(reg, 0, 0)
        except Exception:
            pass

    # ---------- visibilidade ----------
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
        self.win.show_all()
        self.measure()
        self.hw, self.D, self.f, self.ca, self.fa, self.g = self.pw / 2, EDGE + self.ph, self.FLARE, 1.0, 1.0, 1.0
        self.rip = (0.0, 0.0)
        self.eb.set_opacity(1.0)
        self.win.set_opacity(1.0)
        self.area.queue_draw()
        self.set_input()
        GLib.timeout_add(120, lambda: (self.save_snap(), False)[1])

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
            open(GEOM, "w").write(f"{self.pw} {self.ph}")
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
                GLib.timeout_add(80, lambda: (self.save_snap(), False)[1])
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
        self.docks = {}
        disp = Gdk.Display.get_default()
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
        except Exception:
            mons = []
        for i in range(disp.get_n_monitors()):
            gm = disp.get_monitor(i).get_geometry()
            for m in mons:
                if gm.x == int(m["x"]) and gm.y == int(m["y"]):
                    self.docks[m["name"]] = Dock(disp.get_monitor(i), m["name"])
        self.pending = False
        self.was_busy = False
        GLib.timeout_add(60, self.check_busy)
        GLib.timeout_add(2500, self.tick)
        threading.Thread(target=self.listen, daemon=True).start()
        self.tick()

    def schedule(self):
        if not self.pending:
            self.pending = True
            GLib.timeout_add(25, lambda: (setattr(self, "pending", False), self.tick(), False)[2])

    def listen(self):
        try:
            path = f"{RT}/hypr/{os.environ['HYPRLAND_INSTANCE_SIGNATURE']}/.socket2.sock"
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
                for d in self.docks.values():
                    d.hide_instant()
            else:
                self.tick(instant=True)
        return True

    def tick(self, instant=False):
        try:
            mons = json.loads(sh("hyprctl", "monitors", "-j"))
            clients = json.loads(sh("hyprctl", "clients", "-j"))
        except Exception:
            return True
        busy = panel_open()
        items = build_items([c for c in clients if c.get("mapped") and not c.get("hidden")])
        for m in mons:
            d = self.docks.get(m["name"])
            if not d:
                continue
            changed = d.rebuild(items)
            if changed and d.shown:
                d.measure()
                d.hw, d.D = d.pw / 2, EDGE + d.ph
                d.area.queue_draw()
                d.set_input()
            wsid = m["activeWorkspace"]["id"]
            n = sum(1 for c in clients if c["workspace"]["id"] == wsid and c.get("mapped") and not c.get("hidden"))
            want = (n == 0 or d.hovering() or bool(os.environ.get("ENTROPY_DOCK_FORCE"))) and not busy
            if busy:
                d.hide_instant()
            else:
                d.set_shown(want, instant)
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
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR2, lambda: (APP.tick(True), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    try:
        os.remove(PIDF)
    except OSError:
        pass


if __name__ == "__main__":
    main()
