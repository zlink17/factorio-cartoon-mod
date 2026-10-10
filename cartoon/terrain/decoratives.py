"""Décorations de Nauvis (touffes d'herbe, buissons, rameaux...) redessinées en aplats.

Usage : python cartoon/terrain/decoratives.py <dossier_sortie> [famille[,famille...]|toutes] [--contour noir|teinte]
                                             [--garde PART] [--taches OPACITÉ]

Chaque fichier garde la taille et le cadrage de l'original. On lit le sprite d'origine pour savoir *où* dessiner :
son canal alpha, privé de l'ombre intégrée (pixels presque noirs), est découpé en amas ; chaque amas devient un
élément cartoon de la famille (brins, rameaux, feuilles en épée, boule de feuillage), de même emprise, posé au même
endroit. L'ombre est redessinée à plat : la silhouette de l'élément, aplatie au sol et portée vers la droite
(soleil en haut à gauche, comme les bâtiments).
Écrit base/decorative/<famille>/<fichier>.png.
"""
import math, os, sys, zlib
import cv2
import numpy as np

FACTORIO_DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data"
SS = 4                                     # dessin à 4x puis réduction
OUTLINE_BGR = (8, 8, 13)                   # noir chaud (style.OUTLINE_COLOR, en sRGB)
OUTLINE_PX = 1.2                           # épaisseur du contour dans le fichier (px), comme les icônes
SHADOW_ALPHA = 0.42
DECAL_ALPHA = 0.6                          # opacité des taches au sol : le sol transparaît [VALIDÉ]
KEEP = 0.2                                 # part des emplacements gardés dans les familles pavées (touffes) :
                                           # l'original en couvre la carte ; en aplats, une sur cinq suffit [VALIDÉ]
SHADOW_SHEAR = 0.55                        # décalage de l'ombre vers la droite, par px de hauteur
SHADOW_FLAT = 0.35                         # écrasement vertical de l'ombre


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (4, 2, 0))        # BGR


# teintes : (ombre, base, lumière) ; un peu plus claires et plus saturées que les sols, pour se détacher
GREEN = ("#46682a", "#69913a", "#8fb24f")
YELLOW_GREEN = ("#5f6c2a", "#86933a", "#aab452")
BROWN = ("#644a2c", "#8a6a40", "#ad8a58")
RED = ("#6e3226", "#9a4434", "#c0644a")
WHITE = ("#8a8572", "#bdb69d", "#ddd6bd")
RUST = ("#5c2f1f", "#84452b", "#a9643f")          # buisson roux
DRY_PINK = ("#7a5a4c", "#a5806a", "#c8a68c")      # buisson sec rosé
PALE = ("#8c8074", "#c4b5a6", "#e6dacb")          # buisson blanc du désert
STRAW = ("#8f6a38", "#c0924f", "#e0b876")         # paille
TRUNK = ("#5e3d1f", "#86592e", "#ad7d45")         # tronc des petits palmiers
DRY_FROND = ("#7a4a22", "#a8682f", "#cf8a45")     # palmes sèches, orangées
ROCK = ("#6b5d4c", "#8f7d66", "#b3a084")
SAND_ROCK = ("#9a7c52", "#bf9c68", "#dcbd88")
STUMP = ("#55391f", "#7a5332", "#a7784c")

# taille d'un élément (px du fichier, 64 px par case) : un amas plus grand est pavé de plusieurs éléments ;
# None = un seul élément par amas, à sa taille
UNIT = {"clump": None, "palm": None, "straw": None, "tuft": 24, "bush": None, "rock": None, "stump": None, "decal": None, "blade": None, "twig": None, "puff": None, "leaf": None}

# présence minimale du corps de l'original dans une case pour y poser un élément (familles clairsemées : plus haut)
DENSITY = {"green-carpet-grass": 0.4, "brown-carpet-grass": 0.4}

# famille : (type d'élément, teintes)
FAMILIES = {
    "green-hairy-grass": ("tuft", GREEN),
    "green-carpet-grass": ("tuft", GREEN),
    "green-small-grass": ("tuft", YELLOW_GREEN),
    "brown-hairy-grass": ("tuft", BROWN),
    "brown-carpet-grass": ("tuft", BROWN),
    "green-asterisk": ("twig", GREEN),
    "green-asterisk-mini": ("twig", GREEN),
    "brown-asterisk": ("twig", BROWN),
    "brown-asterisk-mini": ("twig", BROWN),
    "red-asterisk": ("twig", RED),
    "green-pita": ("blade", GREEN),
    "green-pita-mini": ("blade", GREEN),
    "red-pita": ("blade", RED),
    "brown-fluff": ("clump", RUST),
    "brown-fluff-dry": ("clump", DRY_PINK),
    "green-bush-mini": ("puff", GREEN),
    "garballo": ("palm", GREEN),
    "garballo-mini-dry": ("palm", DRY_FROND),
    "green-croton": ("leaf", GREEN),
    "red-croton": ("leaf", RED),
    "green-desert-bush": ("bush", YELLOW_GREEN),
    "red-desert-bush": ("straw", STRAW),
    "white-desert-bush": ("clump", PALE),
    # cailloux et souche : la silhouette de l'original, taillée en facettes
    "small-rock": ("rock", ROCK),
    "tiny-rock": ("rock", ROCK),
    "medium-rock": ("rock", ROCK),
    "medium-sand-rock": ("rock", SAND_ROCK),
    "muddy-stump": ("stump", STUMP),
    # taches au sol : la forme de l'original en aplat (teinte moyenne de l'original), bord plus sombre
    "light-mud-decal": ("decal", None),
    "dark-mud-decal": ("decal", None),
    "cracked-mud-decal": ("decal", None),
    "red-desert-decal": ("decal", None),
    "sand-decal": ("decal", None),
    "sand-dune-decal": ("decal", None),
    "lichen-decal": ("decal", None),
    "shroom-decal": ("decal", None),
    "worms-decal": ("decal", None),
}
FOLDER = {"medium-sand-rock": "sand-rock"}          # famille dont les fichiers sont rangés ailleurs


class Rng:
    def __init__(self, seed):
        self.s = (seed * 2654435761 + 12345) & 0xFFFFFFFF

    def u(self, a=0.0, b=1.0):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return a + (b - a) * (self.s >> 8) / float(1 << 24)


# --- lecture de l'original --------------------------------------------------------------------------------------

def body_mask(im):
    """Corps de la plante : pixels assez opaques et pas presque noirs (l'ombre intégrée est noire, peu opaque)."""
    return ((im[:, :, 3] > 60) & (im[:, :, :3].max(2) >= 35)).astype(np.uint8)


def clusters(im):
    """Amas du sprite d'origine (sans son ombre) : liste de (x0, y0, x1, y1) en px du fichier."""
    body = body_mask(im)
    k = max(3, int(min(im.shape[:2]) * 0.06) | 1)
    merged = cv2.dilate(body, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(merged)
    out = []
    for i in range(1, n):
        ys, xs = np.nonzero((lab == i) & (body > 0))
        if len(xs) < 6:
            continue
        out.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return out


def spots(im, unit, rng, density=0.18):
    """Emplacements d'éléments de taille `unit` couvrant le corps de l'original : une grille décalée au hasard,
    une case retenue si le corps y est assez présent. Renvoie des boîtes (x0, y0, x1, y1)."""
    body = cv2.dilate(body_mask(im), np.ones((3, 3), np.uint8))
    h, w = body.shape
    if body.sum() == 0:
        return []
    ys, xs = np.nonzero(body)
    if xs.max() - xs.min() < unit * 1.2 and ys.max() - ys.min() < unit * 1.2:    # petit sprite : un élément
        return [(xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)]
    step = unit * 0.7
    out = []
    y = ys.min() + rng.u(0, step * 0.5)
    while y < ys.max():
        x = xs.min() + rng.u(0, step * 0.5)
        while x < xs.max():
            cell = body[int(y):int(y + step), int(x):int(x + step)]
            if cell.size and cell.mean() > density and rng.u() < KEEP:
                cx, cy = x + step / 2 + rng.u(-0.2, 0.2) * step, y + step / 2 + rng.u(-0.2, 0.2) * step
                s = unit * rng.u(0.8, 1.1)
                out.append((cx - s / 2, cy - s * 0.75, cx + s / 2, cy + s * 0.25))
            x += step
        y += step
    return out


# --- éléments (dessinés sur des calques à SS fois la taille) -----------------------------------------------------

def blade_poly(x0, y0, length, angle, width, bend):
    """Brin effilé courbé : de la base (x0, y0) vers `angle` (0 = vers le haut), largeur `width` à la base."""
    pts_l, pts_r = [], []
    n = 6
    for i in range(n + 1):
        t = i / n
        a = angle + bend * t * t
        x = x0 + math.sin(angle) * length * t + math.sin(a) * length * 0.0
        y = y0 - math.cos(angle) * length * t
        x += bend * length * 0.5 * t * t
        w = width * (1 - t) * 0.5
        nx, ny = math.cos(a), math.sin(a)
        pts_l.append((x - nx * w, y - ny * w))
        pts_r.append((x + nx * w, y + ny * w))
    return np.array(pts_l + pts_r[::-1], np.float32)


def draw_tuft(box, rng, layers):
    """Touffe : brins effilés partant d'une base commune, du fond (sombre) vers l'avant (clair)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, by = (x0 + x1) / 2, y1 - h * 0.08
    n = int(np.clip(w / 16, 4, 7))
    for i in range(n):
        f = (i + 0.5) / n
        ang = (f - 0.5) * 1.6 + rng.u(-0.12, 0.12)
        length = h * rng.u(0.75, 1.0) * (1 - abs(f - 0.5) * 0.6)
        poly = blade_poly(cx + (f - 0.5) * w * 0.2, by, length, ang, max(4.0, w * 0.16), (f - 0.5) * 0.5)
        tone = 2 if i % 3 == 1 else (0 if i % 3 == 0 else 1)
        layers.append((poly, tone))


def draw_blade(box, rng, layers):
    """Rosette de longues feuilles en épée (agave)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, by = x0 + w * 0.42, y1 - h * 0.25
    n = int(np.clip(w / 14, 5, 10))
    for i in range(n):
        ang = -1.35 + 2.7 * (i + 0.5) / n + rng.u(-0.1, 0.1)
        length = max(w, h) * rng.u(0.42, 0.55)
        poly = blade_poly(cx, by, length, ang, max(6, w * 0.15), 0.35 * math.copysign(1, ang))
        layers.append((poly, 0 if abs(ang) > 0.9 else (1 if i % 2 else 2)))


def draw_twig(box, rng, layers):
    """Rameaux : branches fines qui rayonnent du centre, terminées par de petites feuilles."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + h * 0.1
    n = int(np.clip(w / 18, 4, 8))
    for i in range(n):
        a = i * math.tau / n + rng.u(-0.3, 0.3)
        rx, ry = w * 0.45 * rng.u(0.7, 1.0), h * 0.42 * rng.u(0.7, 1.0)
        tip = (cx + math.cos(a) * rx, cy + math.sin(a) * ry)
        mid = (cx + math.cos(a + 0.25) * rx * 0.5, cy + math.sin(a + 0.25) * ry * 0.5)
        th = max(2.0, w * 0.03)
        for p, q in ((( cx, cy), mid), (mid, tip)):
            d = np.array(q) - np.array(p)
            nrm = np.array((-d[1], d[0])) / (np.linalg.norm(d) + 1e-6) * th / 2
            layers.append((np.array([np.array(p) - nrm, np.array(q) - nrm, np.array(q) + nrm, np.array(p) + nrm],
                                    np.float32), 0))
        leaf = max(4.0, w * 0.06)
        for (px, py), r in ((mid, leaf * 0.8), (tip, leaf)):
            layers.append((bumpy(px, py, r, r * 0.75, 3, 0.2, rng), 2 if math.sin(a) < 0 else 1))


def bumpy(cx, cy, rx, ry, bumps, depth, rng, phase=0.0):
    """Contour bosselé (nuage) : ellipse dont le rayon ondule en `bumps` bosses."""
    ang = np.linspace(0, math.tau, bumps * 10, endpoint=False)
    k = 1 + depth * np.abs(np.sin(ang * bumps / 2 + phase))
    return np.stack([cx + np.cos(ang) * rx * k, cy + np.sin(ang) * ry * k], 1).astype(np.float32)


def draw_puff(box, rng, layers):
    """Boule de feuillage : silhouette bosselée, une tache plus sombre en bas à droite, une plus claire en haut."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = w * 0.42, h * 0.4
    layers.append((bumpy(cx, cy, rx, ry, 9, 0.12, rng, rng.u(0, 3)), 1))
    layers.append((bumpy(cx - rx * 0.25, cy - ry * 0.3, rx * 0.45, ry * 0.38, 5, 0.15, rng), 2, "plein"))
    layers.append((bumpy(cx + rx * 0.35, cy + ry * 0.4, rx * 0.4, ry * 0.3, 5, 0.15, rng), 0, "plein"))


def draw_straw(box, rng, layers):
    """Touffe de paille dressée : nombreux brins fins en éventail, à la taille de l'amas."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, by = (x0 + x1) / 2, y1 - h * 0.05
    n = 11
    for i in range(n):
        f = (i + 0.5) / n
        ang = (f - 0.5) * 1.3 + rng.u(-0.12, 0.12)
        length = h * rng.u(0.8, 1.0) * (1 - abs(f - 0.5) * 0.5)
        layers.append((blade_poly(cx + (f - 0.5) * w * 0.12, by, length, ang, max(3.0, w * 0.07), (f - 0.5) * 0.4),
                       (0, 2, 1)[i % 3]))


def draw_palm(box, rng, layers):
    """Petit palmier : tronc court effilé, bouquet de palmes au sommet."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    bx, by = x0 + w * 0.48, y1
    tx, ty = x0 + w * (0.5 + rng.u(-0.06, 0.06)), y0 + h * 0.58          # tronc court, un peu penché
    tw = max(5.0, w * 0.22)
    layers.append((np.array([(bx - tw * 0.55, by), (tx - tw * 0.4, ty), (tx + tw * 0.4, ty), (bx + tw * 0.55, by)],
                            np.float32), "tronc"))
    for k in range(1, 4):                                                # cernes du tronc
        t = k / 4
        x, y, hw = bx + (tx - bx) * t, by + (ty - by) * t, tw * (0.55 - 0.15 * t)
        layers.append((np.array([(x - hw, y - 1.5), (x + hw, y - 1.5), (x + hw, y + 1.5), (x - hw, y + 1.5)],
                                np.float32), "cerne", "plein"))
    n = 8
    for i in range(n):
        ang = -1.6 + 3.2 * (i + 0.5) / n + rng.u(-0.12, 0.12)
        length = min(w * 0.45, h * 0.55) * rng.u(0.85, 1.05)
        layers.append((blade_poly(tx, ty, length, ang, max(5.0, w * 0.14), 0.5 * math.copysign(1, ang)),
                       2 if abs(ang) < 0.8 else (1 if i % 2 else 0)))


def draw_bush(box, rng, layers):
    """Touffe isolée à la taille de l'amas (petits buissons du désert)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = max(w * 0.7, h)
    cx, by = (x0 + x1) / 2, y1
    draw_tuft((cx - s * 0.6, by - s, cx + s * 0.6, by), rng, layers)


def draw_rock(box, rng, layers, hull=None):
    """Caillou : silhouette (enveloppe de l'amas d'origine) en facettes ; facette claire en haut à gauche,
    sombre en bas à droite."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    poly = hull.astype(np.float32)
    c = poly.mean(0)
    layers.append((poly, 1))
    light = (poly - (c + (-0.12 * w, -0.2 * h))) * 0.62 + (c + (-0.12 * w, -0.2 * h))
    dark = (poly - (c + (0.2 * w, 0.25 * h))) * 0.6 + (c + (0.2 * w, 0.25 * h))
    layers.append((dark, 0, "plein"))
    layers.append((light, 2, "plein"))


def draw_stump(box, rng, layers):
    """Souche : tronc court (côtés sombres), dessus coupé clair en ellipse avec un cerne."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    rx, ry = w * 0.36, w * 0.17
    top, bot = y0 + ry + h * 0.05, y1 - ry * 0.9
    ang = np.linspace(0, math.pi, 16)
    trunk = np.concatenate([np.stack([cx - np.cos(ang) * rx * 1.12, bot + np.sin(ang) * ry], 1),     # base évasée
                            [[cx + rx, top], [cx - rx, top]]]).astype(np.float32)
    layers.append((trunk, 0))
    layers.append((np.array([[cx - rx * 0.2, top], [cx + rx, top], [cx + rx * 1.12, bot], [cx, bot + ry]],
                            np.float32), 1, "plein"))
    layers.append((bumpy(cx, top, rx, ry, 1, 0.0, rng), 2))
    layers.append((bumpy(cx, top, rx * 0.5, ry * 0.5, 1, 0.0, rng), 1, "plein"))


def draw_leaf(box, rng, layers):
    """Plante à larges feuilles pointues (croton)."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx, by = (x0 + x1) / 2, y1 - h * 0.12
    n = 6
    for i in range(n):
        ang = -1.0 + 2.0 * (i + 0.5) / n + rng.u(-0.1, 0.1)
        length = h * rng.u(0.75, 0.9)
        width = length * 0.6
        tip = (cx + math.sin(ang) * length, by - math.cos(ang) * length * 0.8)
        side = (math.cos(ang) * width / 2, math.sin(ang) * width / 2 * 0.8)
        mid = ((cx + tip[0]) / 2, (by + tip[1]) / 2)
        layers.append((np.array([(cx, by), (mid[0] - side[0], mid[1] - side[1]), tip,
                                 (mid[0] + side[0], mid[1] + side[1])], np.float32), 2 if i in (2, 3) else (1 if i % 2 else 0)))


DRAW = {"straw": draw_straw, "palm": draw_palm, "stump": draw_stump, "rock": draw_rock, "tuft": draw_tuft, "bush": draw_bush, "blade": draw_blade, "twig": draw_twig, "puff": draw_puff, "leaf": draw_leaf}


# --- composition ------------------------------------------------------------------------------------------------

def render(orig, kind, tones, seed, outline, density=0.18):
    h, w = orig.shape[:2]
    H, W = h * SS, w * SS
    rng = Rng(seed)
    layers = []
    boxes = clusters(orig) if UNIT[kind] is None else spots(orig, UNIT[kind], rng, density)
    for box in sorted(boxes, key=lambda b: b[3]):                  # de l'arrière vers l'avant
        box = tuple(v * SS for v in box)
        if kind == "rock":
            x0, y0, x1, y1 = (int(v / SS) for v in box)
            m = body_mask(orig)[y0:y1, x0:x1]
            pts = cv2.findNonZero(m) + (x0, y0)
            hull = cv2.convexHull(pts)
            hull = cv2.approxPolyDP(hull, max(1.0, 0.07 * max(x1 - x0, y1 - y0)), True)[:, 0] * SS
            draw_rock(box, rng, layers, hull)
        else:
            DRAW[kind](box, rng, layers)
    cols = [hx(t) for t in tones]
    out_col = OUTLINE_BGR if outline == "noir" else tuple(int(c * 0.55) for c in cols[0])
    thick = max(1, int(round(OUTLINE_PX * SS)))
    color = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), np.float32)
    shadow = np.zeros((H, W), np.uint8)
    for layer in layers:                    # aplats, sans contour : les brins se distinguent par leur ton
        poly, tone = layer[:2]
        if tone == "tronc":
            col = hx(TRUNK[1])
        elif tone == "cerne":
            col = hx(TRUNK[0])
        else:
            col = cols[tone]
        inner = len(layer) > 2                                      # tache d'ombrage : seulement sur l'existant
        p = np.round(poly).astype(np.int32)
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [p], 255)
        sel = (m > 0) & (alpha > 0) if inner else m > 0
        color[sel] = col
        if inner:
            continue
        alpha[sel] = 1.0
        # ombre : la silhouette aplatie vers le sol (bas du polygone) et portée vers la droite
        base = p[:, 1].max()
        q = p.astype(np.float32).copy()
        dy = base - q[:, 1]
        q[:, 0] += dy * SHADOW_SHEAR
        q[:, 1] = base - dy * SHADOW_FLAT
        cv2.fillPoly(shadow, [np.round(q).astype(np.int32)], 255)
    # contour sur la silhouette seulement (pas sur chaque brin : il les noierait à cette taille)
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * thick + 1, 2 * thick + 1))
    edge = (cv2.dilate((alpha > 0).astype(np.uint8), disk) > 0) & (alpha == 0)
    color[edge] = out_col
    alpha[edge] = 1.0
    sh = (shadow > 0) & (alpha == 0)
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[..., :3] = color * alpha[..., None]
    rgba[..., 3] = alpha * 255
    rgba[sh, 3] = SHADOW_ALPHA * 255                                # ombre noire semi-transparente
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)


def render_clump(orig, tones, outline, seed=0):
    """Buisson touffu : des lobes ronds posés sur le corps de l'original (sans son ombre), de l'arrière vers l'avant ;
    chaque lobe a une tache claire en haut à gauche, les lobes du bas et de droite sont plus sombres. Contour sur la
    silhouette, ombre à plat portée vers la droite."""
    h, w = orig.shape[:2]
    H, W = h * SS, w * SS
    rng = Rng(seed)
    body = cv2.erode(body_mask(orig), np.ones((2, 2), np.uint8))
    ys, xs = np.nonzero(body)
    if len(xs) == 0:
        return np.zeros_like(orig)
    r = float(np.clip(min(xs.max() - xs.min(), ys.max() - ys.min()) * 0.16, 3.0, 9.0))     # rayon d'un lobe (px)
    lobes = []
    step = r * 1.1
    for y in np.arange(ys.min(), ys.max() + 1, step):
        for x in np.arange(xs.min(), xs.max() + 1, step):
            cell = body[int(y):int(y + step), int(x):int(x + step)]
            if cell.size and cell.mean() > 0.3:
                lobes.append((x + step / 2 + rng.u(-0.25, 0.25) * r, y + step / 2 + rng.u(-0.25, 0.25) * r,
                              r * rng.u(0.85, 1.15)))
    if not lobes:
        lobes = [((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, r)]
    pad = OUTLINE_PX + 1                                         # les lobes restent dans le cadre du fichier
    lobes = [(float(np.clip(x, rr + pad, w - rr - pad)), float(np.clip(y, rr + pad, h - rr - pad)), rr)
             for x, y, rr in ((x, y, min(rr, (min(w, h) - 2 * pad) / 2)) for x, y, rr in lobes)]
    cx0, cy0 = np.mean([l[0] for l in lobes]), np.mean([l[1] for l in lobes])
    cols = [hx(t) for t in tones]
    color = np.zeros((H, W, 3), np.float32)
    m = np.zeros((H, W), np.uint8)
    for x, y, rr in sorted(lobes, key=lambda l: l[1]):          # de l'arrière vers l'avant
        X, Y, R = x * SS, y * SS, rr * SS
        disc = np.zeros((H, W), np.uint8)
        cv2.circle(disc, (int(X), int(Y)), int(R), 1, -1)
        base = cols[0] if (x - cx0) + (y - cy0) > r * 1.2 else cols[1]   # côté bas-droit : plus sombre
        color[disc > 0] = base
        spot = np.zeros((H, W), np.uint8)
        cv2.circle(spot, (int(X - R * 0.3), int(Y - R * 0.3)), int(R * 0.55), 1, -1)
        color[(spot > 0) & (disc > 0)] = cols[2] if base == cols[1] else cols[1]
        m |= disc
    alpha = m.astype(np.float32)
    thick = max(1, int(round(OUTLINE_PX * SS)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * thick + 1, 2 * thick + 1))
    edge = (cv2.dilate(m, disk) > 0) & (m == 0)
    color[edge] = OUTLINE_BGR if outline == "noir" else tuple(int(c * 0.55) for c in cols[0])
    alpha[edge] = 1
    base_y = np.nonzero(m.any(1))[0].max()
    sh = cv2.warpAffine(m, np.float32([[1, -SHADOW_SHEAR, SHADOW_SHEAR * base_y],
                                       [0, SHADOW_FLAT, base_y * (1 - SHADOW_FLAT)]]), (W, H))
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[..., :3] = color * alpha[..., None]
    rgba[..., 3] = alpha * 255
    rgba[(sh > 0) & (alpha == 0), 3] = SHADOW_ALPHA * 255
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)


def render_decal(orig):
    """Tache au sol : la forme de l'original lissée et seuillée, en aplat de sa teinte moyenne, bord plus sombre ;
    ni contour noir ni ombre (elle est au ras du sol)."""
    h, w = orig.shape[:2]
    a = orig[:, :, 3].astype(np.float32) / 255
    if a.sum() == 0:
        return orig
    mean = (orig[:, :, :3].astype(np.float32) * a[..., None]).sum((0, 1)) / a.sum()
    big = cv2.resize(a, (w * SS, h * SS), interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), SS * 1.5)
    m = (big > 0.35).astype(np.uint8)
    rim = m - cv2.erode(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * SS + 1, 2 * SS + 1)))
    rgba = np.zeros((h * SS, w * SS, 4), np.float32)
    rgba[m > 0, :3] = np.clip(mean * 1.05, 0, 255)
    rgba[rim > 0, :3] = mean * 0.72
    rgba[..., 3] = m * 255.0 * DECAL_ALPHA
    rgba[..., :3] *= m[..., None] * DECAL_ALPHA
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    al = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / al, 0, 255), small[..., 3:4]]).astype(np.uint8)


def folder_of(family):
    return os.path.join("base/graphics/decorative", FOLDER.get(family, family))


def files_of(family):
    d = os.path.join(FACTORIO_DATA, folder_of(family))
    return sorted(f for f in os.listdir(d) if f.endswith(".png") and f.startswith(family))


def build_family(family, out, outline):
    kind, tones = FAMILIES[family]
    for f in files_of(family):
        orig = cv2.imread(os.path.join(FACTORIO_DATA, folder_of(family), f), cv2.IMREAD_UNCHANGED)
        if kind == "decal":
            im = render_decal(orig)
        elif kind == "clump":
            im = render_clump(orig, tones, outline, zlib.crc32(f.encode()))
        else:
            im = render(orig, kind, tones, zlib.crc32(f.encode()), outline, DENSITY.get(family, 0.18))
        path = os.path.join(out, folder_of(family).replace("graphics/", ""), f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cv2.imwrite(path, im)


if __name__ == "__main__":
    args = sys.argv[1:]
    outline = "teinte"                     # contour teinté (version foncée de la plante) [VALIDÉ]
    if "--taches" in args:
        i = args.index("--taches"); DECAL_ALPHA = float(args[i + 1]); del args[i:i + 2]
    if "--garde" in args:
        i = args.index("--garde"); KEEP = float(args[i + 1]); del args[i:i + 2]
    if "--contour" in args:
        i = args.index("--contour"); outline = args[i + 1]; del args[i:i + 2]
    out = args[0] if args else "deco_out"
    which = args[1] if len(args) > 1 else "toutes"
    for fam in (FAMILIES if which == "toutes" else which.split(",")):
        build_family(fam, out, outline)
        print("OK", fam, flush=True)
