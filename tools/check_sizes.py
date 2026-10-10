#!/usr/bin/env python3
"""Vérifie que chaque sprite d'un mod a les mêmes dimensions que l'original du jeu.

Usage : python tools/check_sizes.py [cartoon] [dossier data de Factorio]

Signale aussi les ombres (fichiers « shadow ») entièrement vides, qui ne produisent aucune ombre en jeu.

Un sprite de taille différente est refusé par Factorio quand le prototype en découpe une partie
(« sprite rectangle is outside the actual sprite size ») : le jeu ne démarre pas.
Ne convient pas au mod pixel, dont les sprites sont agrandis et recadrés côté Lua.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data"


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def empty_ok(png):
    """Faux (et affiche un avertissement) si une image d'ombre est entièrement transparente."""
    try:
        import cv2
    except ImportError:                               # sans OpenCV : on ne contrôle que les tailles
        return True
    im = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    if im is not None and im.ndim == 3 and im.shape[2] == 4 and im[:, :, 3].max() == 0:
        print(f"OMBRE VIDE : {png.name}")
        return False
    return True


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else "cartoon"
    data = Path(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DATA)
    overrides = ROOT / mod / "mod" / "graphics" / "overrides"
    bad = missing = ok = 0
    for png in sorted(overrides.rglob("*.png")):
        rel = png.relative_to(overrides).as_posix()          # base/entity/.../x.png
        game, _, rest = rel.partition("/")
        orig = data / game / "graphics" / rest
        if not orig.exists():
            print(f"ABSENT de l'original : {rel}")
            missing += 1
        elif png_size(png) != png_size(orig):
            print(f"TAILLE {png_size(png)} au lieu de {png_size(orig)} : {rel}")
            bad += 1
        else:
            ok += 1
            if "shadow" in png.name and not empty_ok(png):
                continue
    print(f"{ok} sprites conformes, {bad} de mauvaise taille, {missing} sans original.")
    sys.exit(1 if bad or missing else 0)


if __name__ == "__main__":
    main()
