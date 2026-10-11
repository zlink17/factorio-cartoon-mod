"""Eau de Nauvis et rives en cartoon : eaux en aplats, berges en aplat cerné, masques à bords nets.

Usage : python cartoon/terrain/water.py <dossier_sortie> [partie[,partie...]|toutes]
        partie = eaux, bruit, effets, rives, bords

Ce que le jeu dessine :
- eaux (`water`, `deepwater`, `water-green`, `deepwater-green`, `water-shallow`, `water-mud`) : planches de
  textures de 1, 2 et 4 cases (8 cellules de 64, 128, 256 px, sans alpha), sur lesquelles le shader « water »
  ajoute reflets et écume animés (effet du prototype `tile-effect`, laissé tel quel). On peint chaque cellule en
  aplat, avec quelques vaguelettes claires qui ne touchent pas le bord : toutes les cellules se raccordent.
- rives (`water-transitions/<sol>.png` et `<sol>-transition.png`) : planche à trois colonnes, « overlay » (x = 0),
  « background » (x = 1088, inutilisé : `background_enabled = false`, gardé d'origine) et masque (x = 2176). Le
  masque (cellules de 64 px, blanc = terre) découpe le sol dessiné sur la case d'eau ; l'overlay est dessiné
  par-dessus, en cellules de 64 x 128 (la case et celle du dessous : `tile_height = 2`, herbe et terres) ou de
  64 x 64 (sable). Bandes : coins intérieurs (y = 0), extérieurs (576), côtés (1152), U (1728), quatre rangées
  d'orientation chacune (masque tous les 64 px, overlay tous les 64 x tile_height) ; O (2304), une rangée de 64. On rend le masque net (comme `masks.py`) et on en tire l'overlay : la berge,
  face de terre sous le bord sud de la terre (vue à 30°, comme les bâtiments), cernée de noir chaud ; un trait
  fin sur les autres bords. Ce qui est sous la cellule est supposé prolonger sa dernière rangée ; on n'y dessine
  que la berge qui y pend (la case du dessous dessine ses propres bords).
- bords des eaux peu profondes (`water-shallow-*.png`, `water-mud-*.png`, cellules de 64) : la texture de l'eau
  peu profonde en fondu sur l'eau voisine ; on y met notre aplat, avec un alpha à bord net et un liseré clair.
Laissés d'origine : écume (`effect-maps`, technique), `water-patch.png` (tache de boue sous les jonctions de
transitions, invisible à cette taille), sols construits (lot 4.5), rives de Space Age (étape 6), `water-wube`.
"""
import math
import os
import sys
import zlib

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from decoratives import FACTORIO_DATA, OUTLINE_BGR, Rng, hx  # noqa: E402

SS = 4
CELL = 64
TERRAIN = os.path.join(FACTORIO_DATA, "base", "graphics", "terrain")

# eau : (fond, vaguelettes, vaguelettes par case)
WATERS = {
    "water": ("#1a6878", "#3f97a6", 1.2),
    "deepwater": ("#16495e", "#2f7088", 0.8),
    "water-green": ("#2c3e10", "#4f6a22", 1.2),
    "deepwater-green": ("#1c2a0c", "#36491a", 0.8),
    "water-shallow": ("#4c6a5c", "#7fa7a3", 1.0),
    "water-mud": ("#3a5c5c", "#679191", 1.0),
}
# taches de fond des eaux peu profondes (sable ou vase vus au travers)
FLATS = {"water-shallow": "#5a7462", "water-mud": "#44605a"}

# rives : planche -> (face de la berge, bas de la berge)
# rives : planche -> (face de la berge, bas de la berge, hauteur de la berge en px du fichier, 64 par case,
# hauteur des cellules d'overlay en cases). Le sable descend en plage sous l'eau (le jeu y dessine le sable en fond) :
# cellules d'une case, berge basse.
SHORES = {
    "grass": ("#6a472a", "#56391f", 9.0, 2),
    "dry-dirt": ("#5e3f25", "#4c321c", 9.0, 2),
    "dark-dirt": ("#4e331d", "#3e2816", 9.0, 2),
    "sand": ("#a98150", "#94703f", 4.0, 1),
}
OUTLINE = 2.0            # contour de la berge (px du fichier)
EDGE = 1.2               # trait sur les bords sans berge
BANDS = [(0, 4), (576, 4), (1152, 4), (1728, 4), (2304, 1)]   # y, rangées (orientations)
MASK_X = 2176
OVERLAY_COLS = 17


def disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


# --- eaux -------------------------------------------------------------------------------------------------------

def ripple(img, rng, x, y, length, color, width):
    """Vaguelette : arc tourné vers le haut (sourire), à SS."""
    pts = []
    for k in range(9):
        t = k / 8
        pts.append((x + (t - 0.5) * length, y + math.sin(t * math.pi) * length * 0.18))
    cv2.polylines(img, [np.round(np.array(pts)).astype(np.int32)], False, color, width, cv2.LINE_AA)


def water_cell(name, side, rng):
    base, light, per_tile = WATERS[name]
    n = side * SS
    img = np.zeros((n, n, 3), np.uint8)
    img[:] = hx(base)
    tiles = (side / CELL) ** 2
    if name in FLATS:                                   # taches de fond, loin du bord
        for _ in range(int(round(tiles * 1.5 + rng.u(0, 1)))):
            r = rng.u(5, 11) * SS
            cx, cy = rng.u(r + 3 * SS, n - r - 3 * SS), rng.u(r + 3 * SS, n - r - 3 * SS)
            pts = [(cx + r * rng.u(0.75, 1.1) * math.cos(a) * 1.3, cy + r * rng.u(0.75, 1.1) * math.sin(a) * 0.8)
                   for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
            cv2.fillPoly(img, [np.round(np.array(pts)).astype(np.int32)], hx(FLATS[name]), cv2.LINE_AA)
    count = int(tiles * per_tile + rng.u(0, 1))
    for _ in range(count):
        length = rng.u(9, 16) * SS
        x, y = rng.u(length / 2 + 3 * SS, n - length / 2 - 3 * SS), rng.u(4 * SS, n - 6 * SS)
        ripple(img, rng, x, y, length, hx(light), int(1.4 * SS))
        if rng.u(0, 1) < 0.5:                           # petite sœur décalée
            ripple(img, rng, x + length * 0.45, y + 3.5 * SS, length * 0.55, hx(light), int(1.2 * SS))
    return cv2.resize(img, (side, side), interpolation=cv2.INTER_AREA)


def waters(out):
    for name in WATERS:
        folder = name if name in ("water", "deepwater", "water-green", "deepwater-green") else name
        for size in (1, 2, 4):
            src = os.path.join(TERRAIN, folder, f"{name}{size}.png")
            h, w = cv2.imread(src, cv2.IMREAD_UNCHANGED).shape[:2]
            side = h
            sheet = np.zeros((h, w, 3), np.uint8)
            for i in range(w // side):
                rng = Rng(zlib.crc32(f"{name}-{size}-{i}".encode()))
                sheet[:, i * side:(i + 1) * side] = water_cell(name, side, rng)
            dst = os.path.join(out, "base", "terrain", folder)
            os.makedirs(dst, exist_ok=True)
            cv2.imwrite(os.path.join(dst, f"{name}{size}.png"), sheet)
        print("OK", name)


# --- bruit du shader ------------------------------------------------------------------------------------------

NOISE_BLUR = 5.0         # px : le grain devient de grandes taches lisses, que les seuils du shader découpent net


def noise(out):
    """Bruit animé du shader « water » (eaux profondes : leur aspect vient surtout de lui), lissé et raccordable."""
    src = cv2.imread(os.path.join(TERRAIN, "effects", "water-noise.png"), cv2.IMREAD_UNCHANGED).astype(np.float32)
    h, w = src.shape[:2]
    tiled = np.tile(src, (3, 3) if src.ndim == 2 else (3, 3, 1))
    smooth = cv2.GaussianBlur(tiled, (0, 0), NOISE_BLUR)[h:2 * h, w:2 * w]
    smooth = (smooth - smooth.mean()) / max(smooth.std(), 1e-6) * src.std() + src.mean()   # mêmes valeurs moyennes
    dst = os.path.join(out, "base", "terrain", "effects")
    os.makedirs(dst, exist_ok=True)
    cv2.imwrite(os.path.join(dst, "water-noise.png"), np.clip(np.round(smooth), 0, 255).astype(np.uint8))
    print("OK water-noise")


# --- cartes d'effet des rives ----------------------------------------------------------------------------------

EFFECT_MAPS = ("water-grass-mask", "water-grass-to-land-mask", "water-dirt-mask", "water-dirt-to-land-mask",
               "water-sand-mask", "water-sand-to-land-mask")
LEVELS = (0, 110, 255)   # paliers de chaque canal (le shader en tire écume et assombrissement près du bord)


def effect_maps(out):
    """Cartes d'effet du shader le long des rives (dégradés rouge et bleu) en paliers à bord net, pour que
    l'écume et l'ombre du bord de l'eau soient des bandes franches plutôt qu'un fondu."""
    dst = os.path.join(out, "base", "terrain", "effect-maps")
    os.makedirs(dst, exist_ok=True)
    cuts = [(a + b) / 2 for a, b in zip(LEVELS, LEVELS[1:])]
    for name in EFFECT_MAPS:
        src = cv2.imread(os.path.join(TERRAIN, "effect-maps", f"{name}.png"), cv2.IMREAD_UNCHANGED)
        h, w = src.shape[:2]
        res = src.copy()
        for c in range(src.shape[2]):
            big = cv2.resize(src[:, :, c].astype(np.float32), (w * 2, h * 2), interpolation=cv2.INTER_LINEAR)
            q = np.full(big.shape, float(LEVELS[0]), np.float32)
            for cut, level in zip(cuts, LEVELS[1:]):
                q[big >= cut] = level
            res[:, :, c] = np.clip(np.round(cv2.resize(q, (w, h), interpolation=cv2.INTER_AREA)), 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(dst, f"{name}.png"), res)
    print("OK cartes d'effet")


# --- rives ------------------------------------------------------------------------------------------------------

def land_big(cell):
    """Cellule de masque (uint8, 64x64) -> terre à SS (bool), bord net (flou léger puis seuil, comme masks.py)."""
    h, w = cell.shape
    big = cv2.resize(cell.astype(np.float32) / 255.0, (w * SS, h * SS), interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), 2.0 * SS, borderType=cv2.BORDER_REPLICATE)
    return big >= 0.5


def shore_cell(land, height, face_col, foot_col, face_px):
    """Overlay (BGRA, 64 x height) tiré de la terre `land` (à SS, 64x64 px du fichier)."""
    n = CELL * SS
    H = height * SS
    pad = 8 * SS                                         # bords prolongés : dilatations sans effet de bord
    ext = np.zeros((H + 2 * pad, n + 2 * pad), np.uint8)
    ext[pad:pad + n, pad:pad + n] = land
    ext[pad + n:, pad:pad + n] = land[-1]                # sous la cellule : la dernière rangée continue
    ext[:pad, pad:pad + n] = land[0]
    ext[:, :pad] = ext[:, pad:pad + 1]
    ext[:, pad + n:] = ext[:, pad + n - 1:pad + n]
    d = int(round(face_px * SS))
    shifted = np.zeros_like(ext)
    shifted[d:] = ext[:-d]
    face = shifted & (1 - ext)                           # face de la berge, sous le bord sud de la terre
    foot_d = int(round(face_px * 0.4 * SS))
    foot = face & (1 - np.vstack([np.zeros((foot_d, ext.shape[1]), np.uint8), ext[:-foot_d]]))   # bas de la face
    solid = ext | face
    outline = cv2.dilate(solid, disk(OUTLINE * SS / 2)) & (1 - cv2.erode(solid, disk(OUTLINE * SS / 2)))
    lip = cv2.dilate(ext, disk(EDGE * SS / 2)) & face   # trait entre le dessus et la face
    # sous la cellule, la case voisine dessine ses propres bords : on n'y garde que la berge qui y pend
    below = np.zeros_like(ext)
    below[pad + n:] = 1
    outline[(below > 0) & (cv2.dilate(face, disk(OUTLINE * SS)) == 0)] = 0
    img = np.zeros(ext.shape + (4,), np.uint8)
    img[face > 0] = (*hx(face_col), 255)
    img[foot > 0] = (*hx(foot_col), 255)
    img[(outline | lip) > 0] = (*OUTLINE_BGR, 255)
    img = img[pad:pad + H, pad:pad + n]
    # réduction en alpha prémultiplié
    a = img[:, :, 3:].astype(np.float32) / 255
    pm = np.concatenate([img[:, :, :3] * a, a * 255], 2)
    small = cv2.resize(pm, (CELL, height), interpolation=cv2.INTER_AREA)
    alpha = small[:, :, 3:]
    rgb = np.where(alpha > 0, small[:, :, :3] / np.maximum(alpha / 255, 1e-6), 0)
    return np.concatenate([np.clip(rgb, 0, 255), np.clip(alpha, 0, 255)], 2).round().astype(np.uint8)


def mask_cells(orig):
    """Cellules de masque d'une planche de rives : (bande, rangée, colonne, y, x)."""
    for b, (y0, rows) in enumerate(BANDS):
        for r in range(rows):
            my = y0 + r * CELL
            for i in range(OVERLAY_COLS):
                mx = MASK_X + i * CELL
                if mx + CELL <= orig.shape[1] and my + CELL <= orig.shape[0] and orig[my:my + CELL, mx:mx + CELL, 3].max():
                    yield b, r, i, my, mx


def crossing(line):
    """Où le bord terre/eau coupe un bord de cellule : (terre au début ?, position) s'il le coupe une seule fois."""
    v = line > 127
    changes = np.nonzero(v[1:] != v[:-1])[0]
    if len(changes) != 1:
        return None
    return bool(v[0]), int(changes[0]) + 1


def edges_of(cell):
    return {"left": crossing(cell[:, 0]), "right": crossing(cell[:, -1]),
            "top": crossing(cell[0, :]), "bottom": crossing(cell[-1, :])}


def canonical(paths):
    """Position type du bord sur chaque côté de cellule, par sens (terre en premier ou non), d'après les côtés.
    Les variantes d'origine ne se raccordent qu'à quelques px près (le fondu le cachait) ; un bord net y fait des
    marches : on ramène chaque coupure à cette position près des bords de la cellule."""
    found = {}
    for path in paths:
        orig = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        for b, _, _, my, mx in mask_cells(orig):
            if b != 2:                                   # les côtés font la référence ; coins et U s'y raccordent
                continue
            for side, c in edges_of(orig[my:my + CELL, mx:mx + CELL, 2]).items():
                if c:
                    found.setdefault((side in ("left", "right"), c[0]), []).append(c[1])
    return {k: float(np.median(v)) for k, v in found.items()}


SNAP = 16                # px : largeur de la bande, le long d'un bord de cellule, où le masque est recalé


def snap(cell, canon):
    """Déforme la cellule de masque pour que le bord terre/eau coupe ses côtés aux positions types."""
    h, w = cell.shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = np.zeros_like(xs), np.zeros_like(ys)
    ramp_l, ramp_r = np.clip(1 - xs / SNAP, 0, 1), np.clip(1 - (w - 1 - xs) / SNAP, 0, 1)
    ramp_t, ramp_b = np.clip(1 - ys / SNAP, 0, 1), np.clip(1 - (h - 1 - ys) / SNAP, 0, 1)
    e = edges_of(cell)
    for side, ramp, vertical in (("left", ramp_l, True), ("right", ramp_r, True), ("top", ramp_t, False),
                                 ("bottom", ramp_b, False)):
        c = e[side]
        if c and (vertical, c[0]) in canon:
            delta = canon[(vertical, c[0])] - c[1]
            if vertical:
                dy += delta * ramp
            else:
                dx += delta * ramp
    return cv2.remap(cell, xs - dx, ys - dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def shore_sheet(path, face_col, foot_col, face_px, tiles, canon):
    orig = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    out = orig.copy()
    out[:, :1088] = 0                                    # overlay refait
    for b, (y0, rows) in enumerate(BANDS):
        height = CELL * (tiles if b < 4 else 1)          # les O n'ont qu'une case
        for r in range(rows):
            my = y0 + r * CELL
            for i in range(OVERLAY_COLS):
                mx = MASK_X + i * CELL
                if mx + CELL > orig.shape[1] or my + CELL > orig.shape[0]:
                    continue
                cell = orig[my:my + CELL, mx:mx + CELL]
                if cell[:, :, 3].max() == 0:
                    continue
                land = land_big(snap(cell[:, :, 2], canon))
                small = cv2.resize(land.astype(np.float32), (CELL, CELL), interpolation=cv2.INTER_AREA)
                v = np.clip(np.round(small * 255), 0, 255).astype(np.uint8)
                out[my:my + CELL, mx:mx + CELL, :3] = v[:, :, None]
                oy = y0 + r * height
                ov = shore_cell(land.astype(np.uint8), height, face_col, foot_col, face_px)
                hh = min(height, out.shape[0] - oy)
                out[oy:oy + hh, i * CELL:(i + 1) * CELL] = ov[:hh]
    return out


def shores(out):
    src = os.path.join(TERRAIN, "water-transitions")
    dst = os.path.join(out, "base", "terrain", "water-transitions")
    os.makedirs(dst, exist_ok=True)
    for name, (face, foot, face_px, tiles) in SHORES.items():
        canon = canonical([os.path.join(src, f"{name}.png")])   # propre à chaque sol : leurs rives diffèrent
        print(name, "positions types des bords :", canon)
        for f in (f"{name}.png", f"{name}-transition.png"):
            cv2.imwrite(os.path.join(dst, f), shore_sheet(os.path.join(src, f), face, foot, face_px, tiles, canon))
            print("OK", f)


# --- bords des eaux peu profondes -------------------------------------------------------------------------------

def edge_sheet(path, name):
    orig = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    h, w = orig.shape[:2]
    out = np.zeros_like(orig)
    base, light, _ = WATERS[name]
    for y in range(0, h, CELL):
        for x in range(0, w, CELL):
            a = orig[y:y + CELL, x:x + CELL, 3]
            ch, cw = a.shape
            big = cv2.resize(a.astype(np.float32) / 255.0, (cw * SS, ch * SS), interpolation=cv2.INTER_LINEAR)
            big = cv2.GaussianBlur(big, (0, 0), 2.0 * SS, borderType=cv2.BORDER_REPLICATE)
            m = (big >= 0.5).astype(np.uint8)
            rim = m & (1 - cv2.erode(m, disk(1.2 * SS), borderType=cv2.BORDER_REPLICATE))
            img = np.zeros((ch * SS, cw * SS, 3), np.uint8)
            img[:] = hx(base)
            img[rim > 0] = hx(light)
            col = cv2.resize(img, (cw, ch), interpolation=cv2.INTER_AREA)
            al = cv2.resize(m.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA)
            out[y:y + ch, x:x + cw, :3] = col
            out[y:y + ch, x:x + cw, 3] = np.clip(np.round(al * 255), 0, 255).astype(np.uint8)
    return out


def edges(out):
    for name in ("water-shallow", "water-mud"):
        dst = os.path.join(out, "base", "terrain", name)
        os.makedirs(dst, exist_ok=True)
        for part in ("inner-corner", "outer-corner", "side", "u", "o"):
            f = f"{name}-{part}.png"
            cv2.imwrite(os.path.join(dst, f), edge_sheet(os.path.join(TERRAIN, name, f), name))
        print("OK bords", name)


PARTS = {"eaux": waters, "bruit": noise, "effets": effect_maps, "rives": shores, "bords": edges}

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "water_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    for p in (PARTS if which in ("toutes", "tous") else which.split(",")):
        PARTS[p](out)
