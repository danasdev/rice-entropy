#!/usr/bin/env python3
"""Gera archinstall.json (só com a lista de pacotes) a partir de packages/pacman.txt."""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pkgs = []
    for line in open(os.path.join(REPO, "packages", "pacman.txt"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            pkgs.append(line)
    out = os.path.join(REPO, "archinstall.json")
    json.dump({"packages": pkgs}, open(out, "w", encoding="utf-8"), indent=2)
    open(out, "a").write("\n")
    print(f"{len(pkgs)} pacotes -> archinstall.json")


if __name__ == "__main__":
    main()
