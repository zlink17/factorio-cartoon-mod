"""Sols de Nauvis en cartoon : herbe, terre, sable et désert rouge, redessinés en aplats.

Usage : python cartoon/terrain/ground.py <dossier_sortie> [tuile|toutes]

Factorio compose le sol avec des planches de textures de 64 px par case (« variantes » de 1, 2 et 4 cases,
et de 8 cases pour certains sables) ; les transitions entre deux sols sont des masques qui reprennent la
texture de la tuile. On remplace donc seulement les planches, avec les dimensions et la disposition de
l'original, et on garde les masques. Chaque variante est une cellule carrée dont les bords restent unis
(rien ne dépasse de la cellule) : n'importe quelles cellules voisines se raccordent sans couture.
Disposition d'une planche (px) : taille 1 en y = 0 (cellules de 64), taille 2 en y = 128 (128), taille 4 en
y = 320 (256), 16 cellules par ligne ; taille 8 en y = 640 (512), 8 par ligne, 2 lignes.
"""
import math, os, sys, zlib
import cv2
import numpy as np

SS = 4                                     # dessin à 4x puis réduction
CELLS = 16                                 # variantes par taille
LAYOUT = {1: (0, 64, 16), 2: (128, 128, 16), 4: (320, 256, 16), 8: (640, 512, 8)}   # taille : (y, côté, par ligne)


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (4, 2, 0))        # BGR pour OpenCV


# base, ombre (plus sombre), lumière (plus clair), touche (détails), type de motif
TILES = {
    "grass-1": ("#5d7d34", "#4d6a2b", "#6f9140", "#3f5a24", "grass"),
    "grass-2": ("#66823a", "#547030", "#7a9a47", "#46602a", "grass"),
    "grass-3": ("#70823a", "#5d6f31", "#85994a", "#4d5d29", "grass"),
    "grass-4": ("#7a843e", "#667034", "#8f9a4f", "#555d2c", "grass"),
    "dirt-1": ("#b3834d", "#9a6f3f", "#c79761", "#7d5530", "dirt"),
    "dirt-2": ("#a77a49", "#8f663a", "#bb8d59", "#74502d", "dirt"),
    "dirt-3": ("#97693d", "#815a33", "#ab7c4d", "#684828", "dirt"),
    "dirt-4": ("#7d5530", "#6a472a", "#916446", "#58391f", "dirt"),
    "dirt-5": ("#785230", "#654428", "#8c6340", "#553720", "dirt"),
    "dirt-6": ("#704c2c", "#5e3f25", "#835a3a", "#4e331d", "dirt"),
    "dirt-7": ("#6c4829", "#5a3c23", "#7f5636", "#4a301b", "dirt"),
    "dry-dirt": ("#7e5532", "#6a4528", "#946a42", "#583a20", "dirt"),
    "sand-1": ("#bf9358", "#aa8049", "#d1a76d", "#92693a", "sand"),
    "sand-2": ("#b08650", "#9b7443", "#c29a63", "#82602f", "sand"),
    "sand-3": ("#b78c55", "#a27a48", "#c9a068", "#8a6535", "sand"),
    "red-desert-0": ("#7e5530", "#6b4527", "#946947", "#593a1e", "desert"),
    "red-desert-1": ("#996633", "#835629", "#ae7a48", "#6c461f", "desert"),
    "red-desert-2": ("#9d6a37", "#875a2d", "#b3804c", "#704b22", "desert"),
    "red-desert-3": ("#a56f3b", "#8f5f31", "#bb8651", "#774f26", "desert"),
}
SIZES = {"sand-1": (1, 2, 4, 8), "sand-2": (1, 2, 4, 8)}          # les autres planches n'ont que 1, 2 et 4


def blob(canvas, rng, cx, cy, r, color):
    """Tache aplatie à contour irrégulier (le centre est choisi pour qu'elle reste dans la cellule)."""
    n = 14
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * rng.uniform(0.7, 1.15)
        pts.append((cx + rr * math.cos(a) * 1.25, cy + rr * math.sin(a)))
    cv2.fillPoly(canvas, [np.array(pts, np.int32)], color, cv2.LINE_AA)


def tuft(canvas, rng, x, y, size, dark, light):
    """Touffe d'herbe : trois lames en pointe."""
    for k, dx in enumerate((-1, 0, 1)):
        h = size * rng.uniform(0.7, 1.15) * (1.15 if dx == 0 else 1.0)
        lean = dx * size * 0.22 + rng.uniform(-0.12, 0.12) * size
        w = size * 0.2
        base_l, base_r, tip = (x + dx * size * 0.2 - w, y), (x + dx * size * 0.2 + w, y), (x + dx * size * 0.2 + lean, y - h)
        cv2.fillPoly(canvas, [np.array([base_l, base_r, tip], np.int32)], light if k == 1 else dark, cv2.LINE_AA)


def pebble(canvas, rng, x, y, r, dark, light, base):
    cv2.ellipse(canvas, (int(x), int(y + r * 0.25)), (int(r * 1.15), int(r * 0.8)), 0, 0, 360, dark, -1, cv2.LINE_AA)
    cv2.ellipse(canvas, (int(x), int(y)), (int(r * 1.1), int(r * 0.75)), 0, 0, 360, light, -1, cv2.LINE_AA)


def crack(canvas, rng, x, y, length, color, width):
    pts = [(x, y)]
    a = rng.uniform(0, 2 * math.pi)
    for _ in range(4):
        a += rng.uniform(-0.8, 0.8)
        x, y = x + length / 4 * math.cos(a), y + length / 4 * math.sin(a) * 0.6
        pts.append((x, y))
    cv2.polylines(canvas, [np.array(pts, np.int32)], False, color, width, cv2.LINE_AA)


def make_cell(size, spec, rng):
    """Une cellule de `size` cases, dessinée à SS fois la taille puis réduite."""
    base, shade, light, accent, kind = [hx(c) if c.startswith("#") else c for c in spec]
    px = 64 * size * SS
    img = np.full((px, px, 3), base, np.uint8)
    margin = 7 * SS                                      # rien ne touche le bord : les cellules se raccordent
    area = size * size
    u = lambda v: int(v * SS)
    inside = lambda: (rng.integers(margin, px - margin), rng.integers(margin, px - margin))
    # grandes taches ton sur ton, très douces (moitié du chemin vers l'ombre ou la lumière)
    soft = lambda c: tuple(int(round((a + b) / 2)) for a, b in zip(base, c))
    for _ in range(int(2.5 * area)):
        r = rng.uniform(6, 13 if size == 1 else 18) * SS
        lo, hi = int(r * 1.35 + margin), int(px - r * 1.35 - margin)
        x, y = rng.integers(lo, hi), rng.integers(lo, hi)
        blob(img, rng, x, y, r, soft(shade) if rng.random() < 0.5 else soft(light))
    if kind == "grass":
        for _ in range(int(11 * area)):
            x, y = inside()
            tuft(img, rng, x, y, u(rng.uniform(5, 8.5)), shade if rng.random() < 0.65 else accent, light)
    elif kind == "dirt":
        for _ in range(int(10 * area)):
            x, y = inside()
            pebble(img, rng, x, y, u(rng.uniform(1.8, 3.6)), shade, light, base)
        for _ in range(int(1.2 * area)):
            x, y = inside()
            crack(img, rng, x, y, u(rng.uniform(6, 11)), shade, u(1.2))
    elif kind == "sand":
        for _ in range(int(3 * area)):                   # ondulations : arcs clairs avec un ombrage dessous
            x, y = inside()
            w, h = u(rng.uniform(12, 22)), u(rng.uniform(3, 6))
            cv2.ellipse(img, (x, y + u(1.5)), (w, h), 0, 200, 340, shade, u(1.6), cv2.LINE_AA)
            cv2.ellipse(img, (x, y), (w, h), 0, 200, 340, light, u(1.6), cv2.LINE_AA)
        for _ in range(int(6 * area)):
            x, y = inside()
            cv2.circle(img, (x, y), u(rng.uniform(0.8, 1.4)), accent, -1, cv2.LINE_AA)
    else:                                                # désert : cailloux et fissures
        for _ in range(int(9 * area)):
            x, y = inside()
            pebble(img, rng, x, y, u(rng.uniform(2.0, 4.2)), shade, light, base)
        for _ in range(int(1.5 * area)):
            x, y = inside()
            crack(img, rng, x, y, u(rng.uniform(7, 13)), shade, u(1.3))
    return cv2.resize(img, (64 * size, 64 * size), interpolation=cv2.INTER_AREA)


def make_sheet(name, seed=0):
    spec = TILES[name]
    rng = np.random.default_rng(zlib.crc32(name.encode()) if seed == 0 else seed)
    sizes = SIZES.get(name, (1, 2, 4))
    h = 1664 if 8 in sizes else 576
    sheet = np.zeros((h, 4096, 4), np.uint8)
    for size in sizes:
        y0, side, per_row = LAYOUT[size]
        for i in range(CELLS):
            r, c = divmod(i, per_row)
            cell = make_cell(size, spec, rng)
            x, y = c * side, y0 + r * side
            sheet[y:y + side, x:x + side, :3] = cell
            sheet[y:y + side, x:x + side, 3] = 255
    return sheet


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ground_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    os.makedirs(out, exist_ok=True)
    for name in (TILES if which == "toutes" else [which]):
        cv2.imwrite(os.path.join(out, f"{name}.png"), make_sheet(name))
        print("OK", name, flush=True)
