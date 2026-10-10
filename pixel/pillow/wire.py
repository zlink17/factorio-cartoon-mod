"""Câbles électriques en pixel art : cuivre, vert et rouge, avec leur ombre.

Le jeu étire une texture de 448 x 92 px (échelle 0,5) entre deux points d'attache : la courbe du câble (une chaînette)
y est dessinée de bout en bout. On reprend exactement la courbe de l'original, colonne par colonne, mais sans
anti-aliasing et avec des couleurs de la palette : un trait de 4 px (2 px de jeu) fait de deux tons, clair dessus et
foncé dessous. Les images « highlight » (câble sélectionné) restent celles du jeu.

Usage : python pixel/pillow/wire.py <dossier_sortie>
"""
import os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, hx

CORE = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data/core/graphics/"
WIRES = {
    "copper-wire": (hx("f0a458"), hx("b0603a")),
    "green-wire": (hx("86d65c"), hx("3d8a4a")),
    "red-wire": (hx("e8766a"), hx("8e3a48")),
}


def center_curve():
    """Hauteur du centre du trait pour chaque colonne de la texture d'origine."""
    src = Image.open(CORE + "copper-wire.png").convert("RGBA")
    ys = []
    for x in range(src.width):
        col = [(y, src.getpixel((x, y))[3]) for y in range(src.height) if src.getpixel((x, y))[3] > 0]
        tot = sum(a for _, a in col)
        ys.append(sum(y * a for y, a in col) / tot if tot else None)
    return ys


def wire(light, dark, curve):
    img = Image.new("RGBA", (448, 92), (0, 0, 0, 0))
    for x, yc in enumerate(curve):
        if yc is None:
            continue
        # courbe quantifiée par pas de 4 px (1 px d'art) pour garder des paliers nets
        y0 = int(round(yc / 4.0)) * 4 - 2
        xb = x // 4
        for dy in range(4):
            c = light if dy < 2 else dark
            if 0 <= y0 + dy < 92:
                img.putpixel((x, y0 + dy), c)
    return img


def shadow(curve):
    img = Image.new("RGBA", (448, 92), (0, 0, 0, 0))
    for x, yc in enumerate(curve):
        if yc is None:
            continue
        y0 = int(round(yc / 4.0)) * 4 - 2
        for dy in range(4):
            if 0 <= y0 + dy < 92:
                img.putpixel((x, y0 + dy), (0, 0, 0, 255))
    return img


def build():
    curve = center_curve()
    out = {name: wire(l, d, curve) for name, (l, d) in WIRES.items()}
    out["wire-shadow"] = shadow(curve)
    return out


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    for name, img in build().items():
        img.save(f"{o}/{name}.png")
