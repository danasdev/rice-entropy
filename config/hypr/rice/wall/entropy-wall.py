#!/usr/bin/env python3
"""Entropy Wall: engine de wallpaper animado (shaders GLSL, loops de vídeo, parallax interativo).

Roda em uma camada BACKGROUND (acima do wallpaper do Noctalia, abaixo dos widgets e das janelas).
Cada wallpaper é uma pasta em ~/.local/share/entropy/wallpapers/<nome>/ com um manifest.json:

  {"type": "shader", "shader": "arquivo.frag", "channels": ["imagem.jpg"], "parallax": 0.0}
  {"type": "video",  "file": "loop.mp4", "parallax": 0.03, "fps": 30}
  {"type": "image",  "file": "foto.jpg", "parallax": 0.04}
  {"type": "layers", "layers": [{"file": "fundo.png", "depth": 0.3}, {"file": "frente.png", "depth": 1.0}], "parallax": 0.05}

Shaders usam o formato do Shadertoy: void mainImage(out vec4 fragColor, in vec2 fragCoord), com
iResolution, iTime, iMouse (px; xy = cursor), iParallax (-1..1, suave, segue o mouse), iChannel0/1.
Controle: entropy-wall-ctl set <nome> | off | list | random
"""
import ctypes, json, math, os, random, signal, socket, subprocess, sys, threading, time
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, GtkLayerShell

HOME = os.path.expanduser("~")
LIB = os.path.join(HOME, ".local/share/entropy/wallpapers")
STATE = os.path.join(HOME, ".config/entropy-wall.json")
RT = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PIDF = os.path.join(RT, "entropy-wall.pid")

# ---------------------------------------------------------------- GL (GLES 3 via ctypes)
GLX = ctypes.CDLL("libGLESv2.so.2")
c_i, c_u, c_f, c_p, c_s = ctypes.c_int, ctypes.c_uint, ctypes.c_float, ctypes.c_void_p, ctypes.c_char_p


def _fn(name, res, *args):
    f = getattr(GLX, name)
    f.restype, f.argtypes = res, list(args)
    return f


glCreateShader = _fn("glCreateShader", c_u, c_u)
glShaderSource = _fn("glShaderSource", None, c_u, c_i, ctypes.POINTER(c_s), c_p)
glCompileShader = _fn("glCompileShader", None, c_u)
glGetShaderiv = _fn("glGetShaderiv", None, c_u, c_u, ctypes.POINTER(c_i))
glGetShaderInfoLog = _fn("glGetShaderInfoLog", None, c_u, c_i, c_p, ctypes.c_char_p)
glCreateProgram = _fn("glCreateProgram", c_u)
glAttachShader = _fn("glAttachShader", None, c_u, c_u)
glLinkProgram = _fn("glLinkProgram", None, c_u)
glGetProgramiv = _fn("glGetProgramiv", None, c_u, c_u, ctypes.POINTER(c_i))
glGetProgramInfoLog = _fn("glGetProgramInfoLog", None, c_u, c_i, c_p, ctypes.c_char_p)
glUseProgram = _fn("glUseProgram", None, c_u)
glGetUniformLocation = _fn("glGetUniformLocation", c_i, c_u, c_s)
glUniform1f = _fn("glUniform1f", None, c_i, c_f)
glUniform1i = _fn("glUniform1i", None, c_i, c_i)
glUniform2f = _fn("glUniform2f", None, c_i, c_f, c_f)
glUniform3f = _fn("glUniform3f", None, c_i, c_f, c_f, c_f)
glUniform4f = _fn("glUniform4f", None, c_i, c_f, c_f, c_f, c_f)
glUniform4fv = _fn("glUniform4fv", None, c_i, c_i, c_p)
glGenTextures = _fn("glGenTextures", None, c_i, ctypes.POINTER(c_u))
glBindTexture = _fn("glBindTexture", None, c_u, c_u)
glActiveTexture = _fn("glActiveTexture", None, c_u)
glTexImage2D = _fn("glTexImage2D", None, c_u, c_i, c_i, c_i, c_i, c_i, c_u, c_u, c_p)
glTexSubImage2D = _fn("glTexSubImage2D", None, c_u, c_i, c_i, c_i, c_i, c_i, c_u, c_u, c_p)
glTexParameteri = _fn("glTexParameteri", None, c_u, c_u, c_i)
glPixelStorei = _fn("glPixelStorei", None, c_u, c_i)
glDrawArrays = _fn("glDrawArrays", None, c_u, c_i, c_i)
glViewport = _fn("glViewport", None, c_i, c_i, c_i, c_i)
glReadPixels = _fn("glReadPixels", None, c_i, c_i, c_i, c_i, c_u, c_u, c_p)
glClearColor = _fn("glClearColor", None, c_f, c_f, c_f, c_f)
glClear = _fn("glClear", None, c_u)
glEnable = _fn("glEnable", None, c_u)
glDisable = _fn("glDisable", None, c_u)
glBlendFunc = _fn("glBlendFunc", None, c_u, c_u)
glGenVertexArrays = _fn("glGenVertexArrays", None, c_i, ctypes.POINTER(c_u))
glBindVertexArray = _fn("glBindVertexArray", None, c_u)

GL_FRAGMENT_SHADER, GL_VERTEX_SHADER = 0x8B30, 0x8B31
GL_COMPILE_STATUS, GL_LINK_STATUS, GL_INFO_LOG_LENGTH = 0x8B81, 0x8B82, 0x8B84
GL_TEXTURE_2D, GL_TEXTURE0 = 0x0DE1, 0x84C0
GL_TEXTURE_MIN, GL_TEXTURE_MAG, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T = 0x2801, 0x2800, 0x2802, 0x2803
GL_LINEAR, GL_CLAMP_TO_EDGE, GL_REPEAT = 0x2601, 0x812F, 0x2901
GL_RGBA, GL_RGB, GL_UNSIGNED_BYTE, GL_UNPACK_ALIGNMENT = 0x1908, 0x1907, 0x1401, 0x0CF5
GL_TRIANGLES, GL_COLOR_BUFFER_BIT, GL_BLEND = 0x0004, 0x4000, 0x0BE2
GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA = 0x0302, 0x0303

VERT = """#version 300 es
void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

HEAD = """#version 300 es
precision highp float;
precision highp int;
uniform vec3 iResolution;
uniform float iTime;
uniform vec4 iMouse;
uniform vec2 iParallax;
uniform float iEnergy;
uniform vec4 iDrops[32];   // gotas do mouse: xy = posição (px), z = idade (s), w = força
uniform sampler2D iChannel0;
uniform sampler2D iChannel1;
uniform sampler2D iChannel2;
uniform sampler2D iAtlas;      // atlas de glifos (manifest "atlas")
uniform vec3 iChannelRes0;
uniform vec3 iChannelRes1;
uniform vec3 iChannelRes2;
uniform vec3 iAtlasRes;
uniform vec4 iP0;              // manifest "params": até 4 números livres
out vec4 outColor;
"""

TOY_MAIN = """
void main() {
    vec4 c = vec4(0.0, 0.0, 0.0, 1.0);
    mainImage(c, gl_FragCoord.xy);
    outColor = vec4(c.rgb, 1.0);
}
"""

# camada com parallax: cobre a tela (modo "cover") e desloca ao contrário do mouse
LAYER_FRAG = HEAD + """
uniform float uDepth;
uniform float uPar;
uniform vec2 uTex;
void main() {
    vec2 res = iResolution.xy;
    float k = max(res.x / uTex.x, res.y / uTex.y);
    vec2 shown = res / (uTex * k);                       // fração visível da imagem (cover)
    float zoom = 1.0 + 2.2 * uPar * uDepth;              // folga para o deslocamento
    vec2 uv = (gl_FragCoord.xy / res - 0.5) * shown / zoom + 0.5;
    uv += vec2(iParallax.x, -iParallax.y) * uPar * uDepth * shown;   // o conteúdo anda ao contrário do mouse
    uv.y = 1.0 - uv.y;
    outColor = texture(iChannel0, uv);
}
"""


class Decoder:
    """Decodifica um vídeo em loop com o ffmpeg (RGB24) e guarda o quadro mais recente."""

    def __init__(self, path, fps=30, width=1280):
        self.path, self.fps = path, fps
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                              "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
        sw, sh = int(out[0]), int(out[1])
        self.w = min(width, sw) // 2 * 2
        self.h = max(2, int(round(sh * self.w / sw)) // 2 * 2)
        self.frame, self.serial, self.alive = None, 0, True
        self.lock = threading.Lock()
        self.proc = None
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        size = self.w * self.h * 3
        cmd = ["ffmpeg", "-v", "error", "-hwaccel", "auto", "-stream_loop", "-1", "-re", "-i", self.path, "-an",
               "-vf", f"fps={self.fps},scale={self.w}:{self.h}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while self.alive:
            buf = self.proc.stdout.read(size)
            if len(buf) < size:
                break
            with self.lock:
                self.frame = buf
                self.serial += 1

    def stop(self):
        self.alive = False
        try:
            self.proc.kill()
        except Exception:
            pass


def compile_shader(kind, src):
    sh = glCreateShader(kind)
    arr = (c_s * 1)(src.encode())
    glShaderSource(sh, 1, arr, None)
    glCompileShader(sh)
    ok = c_i(0)
    glGetShaderiv(sh, GL_COMPILE_STATUS, ctypes.byref(ok))
    if not ok.value:
        buf = ctypes.create_string_buffer(4096)
        glGetShaderInfoLog(sh, 4096, None, buf)
        raise RuntimeError(buf.value.decode(errors="replace"))
    return sh


def make_program(frag):
    prog = glCreateProgram()
    glAttachShader(prog, compile_shader(GL_VERTEX_SHADER, VERT))
    glAttachShader(prog, compile_shader(GL_FRAGMENT_SHADER, frag))
    glLinkProgram(prog)
    ok = c_i(0)
    glGetProgramiv(prog, GL_LINK_STATUS, ctypes.byref(ok))
    if not ok.value:
        buf = ctypes.create_string_buffer(4096)
        glGetProgramInfoLog(prog, 4096, None, buf)
        raise RuntimeError(buf.value.decode(errors="replace"))
    return prog


def new_texture(w, h, rgba=True, data=None, repeat=False):
    t = c_u(0)
    glGenTextures(1, ctypes.byref(t))
    glBindTexture(GL_TEXTURE_2D, t.value)
    for k, v in ((GL_TEXTURE_MIN, GL_LINEAR), (GL_TEXTURE_MAG, GL_LINEAR),
                 (GL_TEXTURE_WRAP_S, GL_REPEAT if repeat else GL_CLAMP_TO_EDGE),
                 (GL_TEXTURE_WRAP_T, GL_REPEAT if repeat else GL_CLAMP_TO_EDGE)):
        glTexParameteri(GL_TEXTURE_2D, k, v)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    fmt = GL_RGBA if rgba else GL_RGB
    glTexImage2D(GL_TEXTURE_2D, 0, fmt, w, h, 0, fmt, GL_UNSIGNED_BYTE, data)
    return t.value


def glyph_atlas(cfg):
    """faixa horizontal com os caracteres da rampa (do mais vazio ao mais cheio); o alfa é o glifo"""
    from PIL import Image, ImageDraw, ImageFont
    chars = cfg.get("chars", " .:-=+*#%@")
    ch = int(cfg.get("cell", 32))
    cw = ch // 2
    font_path = subprocess.run(["fc-match", "-f", "%{file}", cfg.get("font", "JetBrainsMono Nerd Font Mono:style=Bold")],
                               capture_output=True, text=True).stdout
    font = ImageFont.truetype(font_path, int(ch * 0.82))
    im = Image.new("RGBA", (cw * len(chars), ch), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(chars):
        if c == " ":
            continue
        bb = d.textbbox((0, 0), c, font=font)
        x = i * cw + (cw - (bb[2] - bb[0])) // 2 - bb[0]
        y = (ch - (bb[3] - bb[1])) // 2 - bb[1]
        d.text((x, y), c, font=font, fill=(255, 255, 255, 255))
    return im.width, im.height, im.tobytes()


def load_image(path):
    pb = GdkPixbuf.Pixbuf.new_from_file(path)
    if not pb.get_has_alpha():
        pb = pb.add_alpha(False, 0, 0, 0)
    w, h, rs = pb.get_width(), pb.get_height(), pb.get_rowstride()
    px = pb.get_pixels()
    if rs != w * 4:   # remove o preenchimento das linhas
        px = b"".join(px[y * rs: y * rs + w * 4] for y in range(h))
    return w, h, bytes(px)


class Cursor:
    """Posição do cursor direto do socket do Hyprland (leve, sem criar processos)."""

    def __init__(self):
        self.path = f"{RT}/hypr/{os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', '')}/.socket.sock"

    def get(self):
        try:
            s = socket.socket(socket.AF_UNIX)
            s.settimeout(0.05)
            s.connect(self.path)
            s.sendall(b"j/cursorpos")
            data = b""
            while True:
                b = s.recv(256)
                if not b:
                    break
                data += b
            s.close()
            d = json.loads(data)
            return float(d["x"]), float(d["y"])
        except Exception:
            return None


class Surface:
    """Uma janela (um monitor) desenhando o wallpaper atual."""

    def __init__(self, engine, gmon, mon):
        self.eng, self.mon = engine, mon
        self.mx, self.my = mon["x"], mon["y"]
        self.mw, self.mh = mon["width"] / mon["scale"], mon["height"] / mon["scale"]
        self.ready, self.manifest, self.res = False, None, {}
        self.win = Gtk.Window()
        self.win.set_app_paintable(True)
        GtkLayerShell.init_for_window(self.win)
        GtkLayerShell.set_namespace(self.win, "entropy-wall")
        GtkLayerShell.set_layer(self.win, GtkLayerShell.Layer.BACKGROUND)
        GtkLayerShell.set_monitor(self.win, gmon)
        for e in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.win, e, True)
        GtkLayerShell.set_exclusive_zone(self.win, -1)
        self.area = Gtk.GLArea()
        self.area.set_use_es(True)
        self.area.set_required_version(3, 0)
        self.area.set_has_alpha(False)
        self.area.connect("realize", self.on_realize)
        self.area.connect("render", self.on_render)
        self.win.add(self.area)
        self.win.connect("realize", lambda w: self.win.get_window().input_shape_combine_region(__import__("cairo").Region(), 0, 0))

    def show(self):
        self.win.show_all()

    def on_realize(self, area):
        area.make_current()
        if area.get_error():
            print("GL:", area.get_error(), flush=True)
            return
        vao = c_u(0)
        glGenVertexArrays(1, ctypes.byref(vao))
        glBindVertexArray(vao.value)
        self.ready = True
        self.load(self.eng.manifest, self.eng.dir)

    # ---- carga do wallpaper ----
    def load(self, manifest, base):
        self.manifest, self.base = manifest, base
        if not self.ready:
            return
        self.area.make_current()
        self.res = {"prog": None, "tex": [], "layers": [], "video_tex": None, "vserial": -1}
        if manifest is None:
            return
        kind = manifest.get("type", "shader")
        try:
            if kind == "shader":
                src = open(os.path.join(base, manifest["shader"])).read()
                self.res["prog"] = make_program(HEAD + src + TOY_MAIN)
                chans = list(manifest.get("channels", [])[:3])
                for i, ch in enumerate(chans):
                    path = os.path.join(base, ch)
                    if path.endswith((".mp4", ".webm", ".mkv", ".gif")):
                        self.res["tex"].append(("video", None))
                    else:
                        w, h, px = load_image(path)
                        self.res["tex"].append((new_texture(w, h, True, px), (w, h)))
                if manifest.get("atlas"):
                    w, h, px = glyph_atlas(manifest["atlas"])
                    self.res["atlas"] = (new_texture(w, h, True, px), (w, h))
            else:
                self.res["prog"] = make_program(LAYER_FRAG)
                if kind == "image":
                    files = [{"file": manifest["file"], "depth": 1.0}]
                elif kind == "layers":
                    files = manifest["layers"]
                else:
                    files = []
                for ly in files:
                    w, h, px = load_image(os.path.join(base, ly["file"]))
                    self.res["layers"].append((new_texture(w, h, True, px), (w, h), float(ly.get("depth", 1.0))))
                if kind == "video":
                    d = self.eng.decoder
                    self.res["video_tex"] = new_texture(d.w, d.h, False, None)
                    self.res["vsize"] = (d.w, d.h)
        except Exception as e:
            print("erro carregando wallpaper:", e, flush=True)
            self.res["prog"] = None
            try:
                open(os.path.join(RT, "entropy-wall.err"), "w").write(str(e)[:1500])
            except OSError:
                pass

    def uni(self, prog, name):
        return glGetUniformLocation(prog, name.encode())

    def on_render(self, area, ctx):
        r = self.res
        scale = area.get_scale_factor()
        W, H = area.get_allocated_width() * scale, area.get_allocated_height() * scale
        glViewport(0, 0, W, H)
        if not r.get("prog"):
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
            return True
        eng = self.eng
        prog = r["prog"]
        glUseProgram(prog)
        glUniform3f(self.uni(prog, "iResolution"), W, H, 1.0)
        glUniform1f(self.uni(prog, "iTime"), eng.time())
        glUniform1f(self.uni(prog, "iEnergy"), eng.energy)
        glUniform4fv(self.uni(prog, "iDrops"), 32, eng.drops_for(self, W, H))
        px, py = eng.pointer_for(self)
        glUniform4f(self.uni(prog, "iMouse"), (px * 0.5 + 0.5) * W, (0.5 - py * 0.5) * H, 0.0, 0.0)
        glUniform2f(self.uni(prog, "iParallax"), eng.par[0], eng.par[1])
        kind = self.manifest.get("type", "shader")
        par = float(self.manifest.get("parallax", 0.0))
        if kind == "shader":
            for i in range(3):
                glActiveTexture(GL_TEXTURE0 + i)
                if i < len(r["tex"]):
                    tex, size = r["tex"][i]
                    if tex == "video":
                        tex, size = self.video_tex()
                    glBindTexture(GL_TEXTURE_2D, tex)
                    glUniform3f(self.uni(prog, f"iChannelRes{i}"), size[0], size[1], 1.0)
                else:
                    glUniform3f(self.uni(prog, f"iChannelRes{i}"), 0.0, 0.0, 1.0)
                glUniform1i(self.uni(prog, f"iChannel{i}"), i)
            glActiveTexture(GL_TEXTURE0 + 3)
            if r.get("atlas"):
                glBindTexture(GL_TEXTURE_2D, r["atlas"][0])
                glUniform3f(self.uni(prog, "iAtlasRes"), r["atlas"][1][0], r["atlas"][1][1], 1.0)
            glUniform1i(self.uni(prog, "iAtlas"), 3)
            pr = (list(self.manifest.get("params", [])) + [0, 0, 0, 0])[:4]
            glUniform4f(self.uni(prog, "iP0"), *[float(v) for v in pr])
            glDrawArrays(GL_TRIANGLES, 0, 3)
            self.maybe_preview(W, H)
        else:
            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glUniform1f(self.uni(prog, "uPar"), par)
            glUniform1i(self.uni(prog, "iChannel0"), 0)
            layers = list(r["layers"])
            if kind == "video":
                tex, size = self.video_tex()
                layers = [(tex, size, 1.0)]
            for tex, size, depth in layers:
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, tex)
                glUniform1f(self.uni(prog, "uDepth"), depth)
                glUniform2f(self.uni(prog, "uTex"), size[0], size[1])
                glDrawArrays(GL_TRIANGLES, 0, 3)
            glDisable(GL_BLEND)
        return True

    def maybe_preview(self, W, H):
        eng = self.eng
        if not eng.preview_path or self is not eng.surfaces[0]:
            return
        eng.preview_frames += 1
        if eng.preview_frames < 90:      # deixa o shader "aquecer" ~1,5 s
            return
        path, eng.preview_path = eng.preview_path, None
        try:
            buf = ctypes.create_string_buffer(W * H * 4)
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glReadPixels(0, 0, W, H, GL_RGBA, GL_UNSIGNED_BYTE, buf)
            from PIL import Image
            im = Image.frombuffer("RGBA", (W, H), bytes(buf), "raw", "RGBA", 0, -1).convert("RGB")
            im.save(path, quality=92)
            GLib.idle_add(eng.apply_preview, path)
        except Exception as e:
            print("preview:", e, flush=True)

    def video_tex(self):
        d = self.eng.decoder
        r = self.res
        if r.get("video_tex") is None:
            r["video_tex"] = new_texture(d.w, d.h, False, None)
            r["vsize"] = (d.w, d.h)
        with d.lock:
            fr, ser = d.frame, d.serial
        if fr is not None and ser != r["vserial"]:
            glBindTexture(GL_TEXTURE_2D, r["video_tex"])
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, d.w, d.h, GL_RGB, GL_UNSIGNED_BYTE, fr)
            r["vserial"] = ser
        return r["video_tex"], r["vsize"]


class Engine:
    def __init__(self):
        self.surfaces, self.manifest, self.dir, self.decoder = [], None, None, None
        self.cursor = Cursor()
        self.par, self.vel = [0.0, 0.0], [0.0, 0.0]
        self.target = (0.0, 0.0)
        self.raw = None
        self.t0 = time.monotonic()
        self.speed = 1.0
        self.energy, self.rtime, self.reactive, self.prev = 0.0, 0.0, False, None
        self.drops, self.last_drop = [], None
        self.preview_path, self.preview_frames, self.fps, self.skip = None, 0, 60, 0
        disp = Gdk.Display.get_default()
        try:
            mons = json.loads(subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True).stdout)
        except Exception:
            mons = []
        for i in range(disp.get_n_monitors()):
            gm = disp.get_monitor(i).get_geometry()
            for m in mons:
                if gm.x == int(m["x"]) and gm.y == int(m["y"]):
                    self.surfaces.append(Surface(self, disp.get_monitor(i), m))
        self.read_state()
        for s in self.surfaces:
            s.show()
        GLib.timeout_add(16, self.tick)

    def drops_for(self, surf, W, H):
        now = time.monotonic()
        arr = (ctypes.c_float * 128)()
        for i, (gx, gy, t, st) in enumerate(self.drops[-32:]):
            arr[i * 4 + 0] = (gx - surf.mx) / surf.mw * W
            arr[i * 4 + 1] = (1.0 - (gy - surf.my) / surf.mh) * H
            arr[i * 4 + 2] = now - t
            arr[i * 4 + 3] = st
        for i in range(len(self.drops[-32:]), 32):
            arr[i * 4 + 2] = 999.0
        return ctypes.cast(arr, c_p)

    def time(self):
        # reactive: o tempo só anda quando o mouse se mexe (energia suavizada), senão o fundo fica parado
        return self.rtime if self.reactive else (time.monotonic() - self.t0) * self.speed

    def pointer_for(self, surf):
        if self.raw is None:
            return 0.0, 0.0
        x, y = self.raw
        nx = max(-1.0, min(1.0, (x - surf.mx) / surf.mw * 2 - 1))
        ny = max(-1.0, min(1.0, (y - surf.my) / surf.mh * 2 - 1))
        return nx, ny

    def tick(self):
        c = self.cursor.get()
        if c:
            if self.prev is not None:
                sp = math.hypot(c[0] - self.prev[0], c[1] - self.prev[1])
                tgt = max(0.0, min(1.0, sp / 5.0))
                self.energy += (tgt - self.energy) * (0.35 if tgt > self.energy else 0.025)   # sobe rápido, desce devagar
            # gotas: cada trecho percorrido pelo mouse vira uma frente de onda que se espalha
            now = time.monotonic()
            if self.last_drop is None or math.hypot(c[0] - self.last_drop[0], c[1] - self.last_drop[1]) > 14:
                sp = math.hypot(c[0] - self.prev[0], c[1] - self.prev[1]) if self.prev else 0.0
                if self.last_drop is not None:
                    self.drops.append((c[0], c[1], now, max(0.25, min(1.0, sp / 12.0))))
                    self.drops = [d for d in self.drops if now - d[2] < 6.0][-32:]
                self.last_drop = c
            self.prev = c
            self.raw = c
        self.rtime += 0.016 * self.energy * self.speed
        if self.raw and self.surfaces:
            s = self.surfaces[0]
            for sf in self.surfaces:
                if sf.mx <= self.raw[0] < sf.mx + sf.mw and sf.my <= self.raw[1] < sf.my + sf.mh:
                    s = sf
            tx, ty = self.pointer_for(s)
            self.target = (tx, ty)
        if os.environ.get("ENTROPY_WALL_PAR"):   # teste: força o parallax (x,y)
            px_, py_ = os.environ["ENTROPY_WALL_PAR"].split(",")
            self.target = (float(px_), float(py_))
        # mola suave (levemente amortecida): o fundo "segue" o mouse com inércia
        for i in range(2):
            a = (self.target[i] - self.par[i]) * 90.0 - self.vel[i] * 14.0
            self.vel[i] += a * 0.016
            self.par[i] += self.vel[i] * 0.016
        self.skip += 1
        if self.fps < 50 and self.skip % 2:
            return True
        for s in self.surfaces:
            if s.ready and self.manifest is not None:
                s.area.queue_render()
        return True

    def apply_preview(self, path):
        """o preview vira o wallpaper estático do Noctalia: paleta, widgets e painéis seguem as cores"""
        if not self.manifest:
            return False
        subprocess.Popen(["noctalia", "msg", "wallpaper-set", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False

    def make_preview(self):
        m, base = self.manifest, self.dir
        kind = m.get("type")
        if kind == "image":
            self.apply_preview(os.path.join(base, m["file"]))
        elif kind == "layers":
            self.apply_preview(os.path.join(base, m["layers"][0]["file"]))
        else:
            out = os.path.join(base, "preview.jpg")
            if os.path.exists(out):
                self.apply_preview(out)
            elif kind == "video":
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", os.path.join(base, m["file"]), "-frames:v", "1", out])
                self.apply_preview(out)
            else:
                self.preview_path, self.preview_frames = out, 0

    def read_state(self):
        try:
            name = json.load(open(STATE)).get("current")
        except Exception:
            name = None
        self.set_wall(name)

    def set_wall(self, name):
        if self.decoder:
            self.decoder.stop()
            self.decoder = None
        self.manifest, self.dir = None, None
        try:
            os.remove(os.path.join(RT, "entropy-wall.err"))
        except OSError:
            pass
        if name:
            base = os.path.join(LIB, name)
            try:
                self.manifest = json.load(open(os.path.join(base, "manifest.json")))
                self.dir = base
                if self.manifest.get("type") == "video":
                    self.decoder = Decoder(os.path.join(base, self.manifest["file"]), int(self.manifest.get("fps", 30)))
                else:
                    for ch in self.manifest.get("channels", []):
                        if ch.endswith((".mp4", ".webm", ".mkv", ".gif")):
                            self.decoder = Decoder(os.path.join(base, ch), int(self.manifest.get("fps", 30)))
                            break
                self.speed = float(self.manifest.get("speed", 1.0))
                self.fps = int(self.manifest.get("fps", 60))
                self.reactive = bool(self.manifest.get("reactive", False))
            except Exception as e:
                print("manifest inválido:", e, flush=True)
                self.manifest = None
        for s in self.surfaces:
            if self.manifest is None:
                s.win.hide()
            else:
                s.win.show_all()
                s.load(self.manifest, self.dir)
        if self.manifest is not None and self.surfaces:
            GLib.timeout_add(400, lambda: (self.make_preview(), False)[1])


def main():
    if os.path.exists(PIDF):
        try:
            os.kill(int(open(PIDF).read()), 0)
            sys.exit(0)
        except Exception:
            pass
    open(PIDF, "w").write(str(os.getpid()))
    eng = Engine()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, lambda: (eng.read_state(), True)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    try:
        os.remove(PIDF)
    except OSError:
        pass


if __name__ == "__main__":
    main()
