"""Terrain de Nauvis en pixel art : herbe, terre, sable, désert rouge (textures des tuiles terrestres).

Planche d'une tuile de Factorio : 4096 px de large (64 px par tuile) et trois bandes de variantes, séparées par du vide :
  y   0 -  64 : tuiles de 1 x 1 case (64 px)      y 128 - 256 : 2 x 2 cases (128 px)      y 320 - 576 : 4 x 4 cases (256 px)
  y 640 - 1664 (sable 1 seulement) : 8 x 8 cases (512 px), 8 par rangée.
En pixels d'art (1 px d'art = 4 px de planche, 2 px de jeu) : 16, 32, 64 et 128 px. Chaque variante est un morceau
homogène (même densité de détails partout, rien de particulier au bord) : le jeu les pose côte à côte au hasard.

Usage : python pixel/pillow/terrain.py <dossier_sortie>   (aperçu)
"""
import math, os, random, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import hx

# (base, ombre, lumière, détail) par sol ; "kind" règle le type de détails
TERRAINS = {
    "grass-1": dict(kind="grass", base="6aa84a", dark="4e9040", light="86c45a", flowers=0.10),
    "grass-2": dict(kind="grass", base="62a048", dark="488a3e", light="7fbc58", flowers=0.06),
    "grass-3": dict(kind="grass", base="7aa84a", dark="5c9040", light="96c25a", flowers=0.04),
    "grass-4": dict(kind="grass", base="8aa44a", dark="6c8c3e", light="a6be5a", flowers=0.0),
    "dry-dirt": dict(kind="dirt", base="b08c5c", dark="8e6e46", light="c8a876", stone="d6c4a0"),
    "dirt-1": dict(kind="dirt", base="9c7a50", dark="7e5e3c", light="b49468", stone="c8b090"),
    "dirt-2": dict(kind="dirt", base="92704a", dark="745636", light="aa8a60", stone="c0a888"),
    "dirt-3": dict(kind="dirt", base="886744", dark="6c4e30", light="a08258", stone="b8a080"),
    "dirt-4": dict(kind="dirt", base="7e5e3c", dark="634628", light="967850", stone="b09878"),
    "dirt-5": dict(kind="dirt", base="745636", dark="5a3f24", light="8c6e48", stone="a89070"),
    "dirt-6": dict(kind="dirt", base="6a4e30", dark="523820", light="826440", stone="a08868"),
    "dirt-7": dict(kind="dirt", base="604628", dark="4a321c", light="785a38", stone="988060"),
    "sand-1": dict(kind="sand", base="d8bc78", dark="b89c5c", light="ecd696"),
    "sand-2": dict(kind="sand", base="d0b070", dark="b09254", light="e4cc8c"),
    "sand-3": dict(kind="sand", base="c8a868", dark="a88c4e", light="dcc280"),
    "red-desert-0": dict(kind="desert", base="c8844c", dark="a46438", light="dc9c64", stone="e0b080"),
    "red-desert-1": dict(kind="desert", base="c07c46", dark="9c5e34", light="d4945e", stone="d8a878"),
    "red-desert-2": dict(kind="desert", base="b87440", dark="94582e", light="cc8c58", stone="d0a070"),
    "red-desert-3": dict(kind="desert", base="b06c3a", dark="8c5028", light="c48452", stone="c89868"),
}
BANDS = {1: (0, 64, 16), 2: (128, 256, 32), 4: (320, 576, 64), 8: (640, 1664, 128)}   # début, fin (planche), taille d'art


def spots(rng, w, h, per100):
    """Positions aléatoires : `per100` détails pour 100 px d'art carrés (arrondi aléatoire, en laissant 1 px de marge)."""
    n = per100 * w * h / 100.0
    n = int(n) + (1 if rng.random() < n - int(n) else 0)
    return [(rng.randint(1, w - 3), rng.randint(1, h - 3)) for _ in range(n)]


def tile(name, size, seed):
    t = TERRAINS[name]
    base, dark, light = hx(t["base"]), hx(t["dark"]), hx(t["light"])
    rng = random.Random(f"{name}-{size}-{seed}")
    w = h = size
    img = Image.new("RGBA", (w, h), base)
    put = lambda x, y, c: img.putpixel((x, y), c) if 0 <= x < w and 0 <= y < h else None
    # grandes plaques légèrement plus claires ou plus sombres (pour les grandes variantes)
    if size >= 32:
        for _ in range({32: 2, 64: 6, 128: 22}[size]):
            r = rng.uniform(3, 7) if size == 32 else rng.uniform(4, 11)
            cx, cy = rng.uniform(r + 5, w - r - 5), rng.uniform(r + 5, h - r - 5)
            tone = dark if rng.random() < 0.5 else light
            mixed = tuple(int(base[i] * 0.7 + tone[i] * 0.3) for i in range(3)) + (255,)
            for y in range(int(cy - r) - 1, int(cy + r) + 2):
                for x in range(int(cx - r * 1.4) - 1, int(cx + r * 1.4) + 2):
                    d = ((x - cx) / 1.4) ** 2 + (y - cy) ** 2
                    if d < r * r * (0.85 + 0.3 * rng.random()):
                        put(x, y, mixed)
    kind = t["kind"]
    if kind == "grass":
        for x, y in spots(rng, w, h, 1.1):                      # touffes en V sombre
            put(x, y, dark); put(x + 2, y, dark); put(x + 1, y + 1, dark)
        for x, y in spots(rng, w, h, 1.2):                      # brins clairs
            put(x, y, light); put(x, y - 1, light)
        for x, y in spots(rng, w, h, 0.5):                      # points sombres
            put(x, y, dark)
        for x, y in spots(rng, w, h, t["flowers"]):             # fleurs blanches à cœur jaune
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                put(x + dx, y + dy, hx("eef3f6"))
            put(x, y, hx("f7c06a"))
    elif kind in ("dirt", "desert"):
        stone = hx(t["stone"])
        for x, y in spots(rng, w, h, 1.6):                      # éclats sombres
            put(x, y, dark)
            if rng.random() < 0.4:
                put(x + 1, y, dark)
        for x, y in spots(rng, w, h, 1.2):
            put(x, y, light)
        for x, y in spots(rng, w, h, 0.45 if kind == "dirt" else 0.35):    # petits cailloux
            put(x, y, stone); put(x + 1, y, stone); put(x, y + 1, dark); put(x + 1, y + 1, dark)
        if kind == "desert":
            for x, y in spots(rng, w, h, 0.18):                 # gros rochers
                for dx in range(3):
                    put(x + dx, y, stone)
                for dx in range(3):
                    put(x + dx, y + 1, dark)
    else:  # sand : rides
        for x, y in spots(rng, w, h, 0.9):
            L = rng.randint(3, 5)
            for dx in range(L):
                put(x + dx, y, light)
            for dx in range(1, L + 1):
                put(x + dx, y + 1, dark)
        for x, y in spots(rng, w, h, 1.0):
            put(x, y, light)
    return img


def sheet(name):
    """Planche complète (en pixels d'art) ; l'export la agrandit x4."""
    tall = 1664 if name == "sand-1" else 576
    out = Image.new("RGBA", (1024, tall // 4), (0, 0, 0, 0))
    for size, (y0, y1, s) in BANDS.items():
        if y1 > tall:
            continue
        per_row = 1024 // s
        rows = max(1, (y1 - y0) // 4 // s)
        for r in range(rows):
            for c in range(per_row):
                out.alpha_composite(tile(name, s, r * per_row + c), (c * s, y0 // 4 + r * s))
    return out


def quantize_mask(img):
    """Masque de transition : seuil et blocs de 4 x 4 px (1 px d'art), pour des bords nets sur la grille de pixels."""
    import numpy as np
    a = np.array(img.convert("L"), dtype=np.float32)
    h, w = a.shape
    h4, w4 = h - h % 4, w - w % 4
    blocks = a[:h4, :w4].reshape(h4 // 4, 4, w4 // 4, 4).mean(axis=(1, 3))
    q = (blocks >= 110).astype(np.uint8) * 255
    out = np.kron(q, np.ones((4, 4), dtype=np.uint8))
    full = np.zeros((h, w), dtype=np.uint8)
    full[:h4, :w4] = out
    return Image.fromarray(full, "L")


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    names = list(TERRAINS)
    cell = 16 * 5
    prev = Image.new("RGBA", (cell * 12, cell * 4 * ((len(names) + 3) // 4)), (0, 0, 0, 255))
    for i, n in enumerate(names):
        img = Image.new("RGBA", (16 * 6, 16 * 4))
        for gy in range(4):
            for gx in range(6):
                img.alpha_composite(tile(n, 16, gy * 6 + gx), (gx * 16, gy * 16))
        prev.alpha_composite(img.resize((img.width * 2, img.height * 2), Image.NEAREST), ((i % 4) * 16 * 6 * 2 + 0, (i // 4) * 16 * 4 * 2))
    prev.save(f"{o}/terrain_preview.png")
