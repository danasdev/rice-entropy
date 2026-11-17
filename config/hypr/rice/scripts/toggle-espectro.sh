#!/usr/bin/env python3
# Liga/desliga o espectro de áudio da área de trabalho (widgets hd_viz e lp_viz do Noctalia).
import os, re, subprocess
files = [os.path.expanduser("~/.config/noctalia/config.toml"),
         os.path.expanduser("~/.local/state/noctalia/settings.toml")]
cfg = open(files[0]).read()
m = re.search(r"\[desktop_widgets\.widget\.hd_viz\][^\[]*?enabled = (true|false)", cfg)
novo = "false" if (m and m.group(1) == "true") else "true"
for f in files:
    if not os.path.exists(f):
        continue
    t = open(f).read()
    for w in ("hd_viz", "lp_viz"):
        # cobre o formato do config.toml e o formato indentado do settings.toml
        t = re.sub(r"(\[desktop_widgets\.widget\.%s\][^\[]*?enabled = )(true|false)" % w, r"\g<1>" + novo, t)
    open(f, "w").write(t)
subprocess.run(["noctalia", "msg", "config-reload"], capture_output=True)
subprocess.run(["notify-send", "-a", "Rice", "Espectro de áudio", "ligado" if novo == "true" else "desligado"], capture_output=True)
