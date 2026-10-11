"""Falaises de Nauvis : ce qui ne dépend pas du dessin de la roche (lecture de l'original, ombres, découpe).

Module utilisé par cartoon/blender/cliffs_3d.py, qui dessine la roche (relief à facettes, tons de l'original).

Chaque orientation de falaise est une cellule de 256 px (4 cases à l'échelle 0,5) de quatre planches : côtés
(`cliff-sides`, 8 x 4 cellules), coins extérieurs et intérieurs (`cliff-outer`, `cliff-inner`), entrées
(`cliff-entrance`, 4 x 4). Le jeu dessine chaque cellule en deux calques : le haut, au-dessus des entités, et le
pied (`-lower`), dessous ; plus une ombre (`-shadow`, même origine que le sprite, cellules de 320 px : 64 px de
marge à droite ; 256 px pour les entrées).
- silhouette : réunion des corps des deux calques de l'original (alpha > 200), gardée au pixel près ;
- la cellule est prolongée de ses bords (PAD) avant de dessiner, puis recadrée : une falaise se continue dans la
  cellule voisine, le dessin ne doit pas s'aligner sur le bord ;
- pas de halo : l'original peint au pied un fondu sombre semi-transparent, qui passe sur la roche voisine ;
- répartition : chaque pixel va au calque qui le portait dans l'original (alpha lissé le plus fort) ;
- ombre : une falaise est une marche de terrain, éclairée par la gauche. Le haut est toujours à gauche du sens de
  la falaise (ORIENTATIONS : `west_to_east` a le haut au nord, d'où la grande paroi vue de face ; `south_to_north`
  l'a à l'ouest). Seules les parois dont le haut est à l'ouest (tronçons parcourus vers le nord) jettent une ombre :
  leur roche balayée vers la droite (SHADOW_RUN), gardée sur le terrain bas et hors de la roche. Un trou a donc sa
  paroi gauche ombrée et rien en haut ; un plateau n'a pas d'ombre dessus, seulement à droite. L'original suit la
  même règle, mais son ombre est coupée net au bord des cellules (le fondu du pied le cachait).
"""
import os
import sys
import zlib

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decoratives import FACTORIO_DATA, OUTLINE_BGR, OUTLINE_PX, SS, hx  # noqa: E402

SHEETS = ("sides", "outer", "inner", "entrance")
CELL = 256
PAD = 40                 # px : prolongement de la cellule (bords répétés) avant de poser les formes
SHADOW_RUN = 96          # longueur de l'ombre portée vers la droite (px du fichier, ~ 1,5 case, comme l'original)

# sens de la falaise de chaque cellule : planche -> {rangée: (entrée, sortie)} ; entrées : {(rangée, colonne): ...}
ORIENTATIONS = {
    "sides": {0: ("east", "west"), 1: ("south", "north"), 2: ("west", "east"), 3: ("north", "south")},
    "outer": {0: ("north", "east"), 1: ("east", "south"), 2: ("south", "west"), 3: ("west", "north")},
    "inner": {0: ("west", "south"), 1: ("north", "west"), 2: ("east", "north"), 3: ("south", "east")},
    "entrance": {0: (("none", "east"), ("west", "none")), 1: (("none", "north"), ("south", "none")),
                 2: (("none", "west"), ("east", "none")), 3: (("none", "south"), ("north", "none"))},
}
SIDE_POINT = {"west": (0, 128), "east": (256, 128), "north": (128, 0), "south": (128, 256)}
SRC = os.path.join(FACTORIO_DATA, "base", "graphics", "terrain", "cliffs")

ROCK = ("#3e2b1d", "#6f5136", "#9b7b55", "#cdb38a")   # creux, flanc sombre, flanc éclairé, dessus


# --- lecture de l'original ----------------------------------------------------------------------------------------

def load(sheet):
    up = cv2.imread(os.path.join(SRC, f"cliff-{sheet}.png"), cv2.IMREAD_UNCHANGED)
    low = cv2.imread(os.path.join(SRC, f"cliff-{sheet}-lower.png"), cv2.IMREAD_UNCHANGED)
    return up, low


def body_of(up, low):
    """Corps de la falaise (uint8 0/1), trous de 3 px bouchés."""
    b = ((up[..., 3] > 200) | (low[..., 3] > 200)).astype(np.uint8)
    return cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))


def luminance(up, low, body):
    """Luminosité de l'original sur le corps (moyenne locale qui ignore le fond)."""
    a_u = up[..., 3:4] / 255.0
    a_l = low[..., 3:4] / 255.0
    rgb = up[..., :3] * a_u + low[..., :3] * a_l * (1 - a_u)
    rgb = rgb / np.maximum(a_u + a_l * (1 - a_u), 1e-6)
    lum = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    w = cv2.GaussianBlur(body.astype(np.float32), (0, 0), 2)
    return cv2.GaussianBlur(lum * body, (0, 0), 2) / np.maximum(w, 1e-3)


def big(mask):
    """Masque 0/1 à la taille du fichier -> booléen à SS, bord lissé."""
    h, w = mask.shape
    return cv2.resize(mask.astype(np.float32), (w * SS, h * SS), interpolation=cv2.INTER_LINEAR) > 0.5


def disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


# --- commun ---------------------------------------------------------------------------------------------------------

def finish(color, inside, lines):
    """Couleur et traits (à SS) -> BGRA à la taille du fichier : traits intérieurs en brun très sombre, contour noir
    chaud à l'intérieur de la silhouette (la silhouette d'origine ne bouge pas)."""
    h, w = inside.shape
    color = color.copy()
    color[lines & inside] = np.array(hx(ROCK[0]), np.float32) * 0.6
    thick = max(1, int(round(OUTLINE_PX * SS)))
    rim = inside & ~(cv2.erode(inside.astype(np.uint8), disk(thick)) > 0)
    color[rim] = OUTLINE_BGR
    alpha = inside.astype(np.float32)
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[..., :3] = color * alpha[..., None]
    rgba[..., 3] = alpha * 255
    small = cv2.resize(rgba, (w // SS, h // SS), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)


def split(im, up, low):
    """Chaque pixel au calque (haut, pied) qui le portait dans l'original."""
    au, al = up[..., 3].astype(np.float32), low[..., 3].astype(np.float32)
    su, sl = cv2.GaussianBlur(au, (0, 0), 3), cv2.GaussianBlur(al, (0, 0), 3)
    to_up = su >= sl
    hi, lo = im.copy(), im.copy()
    hi[~to_up] = 0
    lo[to_up] = 0
    return hi, lo


def orientation(sheet, r, c):
    o = ORIENTATIONS[sheet][r]
    return o[c // 2] if sheet == "entrance" else o


def low_ground(entry, exit_, shape):
    """(terrain bas, ombrant) pour la cellule prolongée de PAD. Bas : à droite du chemin entrée -> centre -> sortie
    (le haut est à gauche). Ombrant : les pixels dont le tronçon de chemin le plus proche monte vers le nord, c.-à-d.
    les parois dont le haut est à l'ouest, face à la lumière : seules elles jettent une ombre (balayer aussi les
    parois est-ouest y laisse des franges, les dents de la roche). Une extrémité (« none ») prolonge le chemin."""
    c = np.array([128.0, 128.0])
    a = np.array(SIDE_POINT[entry], float) if entry != "none" else None
    b = np.array(SIDE_POINT[exit_], float) if exit_ != "none" else None
    a = a if a is not None else 2 * c - b
    b = b if b is not None else 2 * c - a
    a, b = a + (a - c) * 2, b + (b - c) * 2                   # chemin prolongé au-delà de la cellule
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    pts = np.stack([xs - PAD, ys - PAD], -1)
    best_d = np.full((h, w), np.inf)
    side = np.zeros((h, w))
    north = np.zeros((h, w), bool)
    for p0, p1 in ((a, c), (c, b)):
        t = p1 - p0
        u = np.clip(((pts - p0) @ t) / (t @ t), 0, 1)
        d = np.linalg.norm(pts - (p0 + u[..., None] * t), axis=-1)
        left = np.array([t[1], -t[0]])                        # à gauche du sens (y vers le bas)
        s_ = (pts - p0) @ left
        closer = d < best_d
        best_d[closer] = d[closer]
        side[closer] = s_[closer]
        north[closer] = t[1] < -0.3 * np.linalg.norm(t)
    return side < 0, north


def shadow_cell(alpha_padded, width, low, caster):
    """Ombre (BGRA width x 256) : la roche (alpha de la cellule prolongée de PAD) balayée vers la droite, gardée sur
    le terrain bas `low`. Même origine que le sprite (prototype : shift de 0,5 case pour 64 px de plus en largeur).
    Le pied de la falaise (`-lower`) est dessiné sous les ombres : on retire de l'ombre toute la roche, y compris
    celle qui se prolonge dans la cellule voisine (bords répétés), sinon l'ombre fait un voile sur la roche."""
    extra = width - CELL                                       # l'ombre déborde de la cellule à droite
    a = cv2.copyMakeBorder((alpha_padded > 127).astype(np.uint8), 0, 0, 0, extra, cv2.BORDER_REPLICATE)
    low = cv2.copyMakeBorder(low.astype(np.uint8), 0, 0, 0, extra, cv2.BORDER_REPLICATE)
    caster = cv2.copyMakeBorder(caster.astype(np.uint8), 0, 0, 0, extra, cv2.BORDER_REPLICATE)
    src = a & caster
    h, w = a.shape
    # longueur adaptée à la cellule : l'image d'ombre ne déborde que de 64 px à droite ; une ombre coupée par son
    # bord fait un trait droit. On la raccourcit pour que son bout suive le profil de la roche (10e centile de la
    # place disponible par rangée, les éclats isolés ne comptent pas).
    run = SHADOW_RUN
    rows = src[PAD:PAD + CELL].any(1)
    if rows.any():
        right = (src[PAD:PAD + CELL][rows] > 0)[:, ::-1].argmax(1)          # distance au bord droit du canevas
        room = right - (w - (PAD + width))                                  # place jusqu'au bord de l'image d'ombre
        run = int(np.clip(np.percentile(room, 10) - 4, 24, SHADOW_RUN))
    sw = np.zeros((h, w), np.uint8)
    for d in range(0, run + 1, 2):
        sw[:, d:] = np.maximum(sw[:, d:], src[:, :w - d])
    sw[(cv2.dilate(a, np.ones((3, 3), np.uint8)) > 0) | (low == 0)] = 0
    out = np.zeros((CELL, width, 4), np.uint8)
    out[..., 3] = sw[PAD:PAD + CELL, PAD:PAD + width] * 255
    return out


def pad(im):
    return cv2.copyMakeBorder(im, PAD, PAD, PAD, PAD, cv2.BORDER_REPLICATE)


def build(sheet, out, render):
    """Écrit les trois fichiers d'une planche ; `render(up, low, seed)` dessine la cellule prolongée (BGRA)."""
    up, low = load(sheet)
    rows, cols = up.shape[0] // CELL, up.shape[1] // CELL
    hi, lo = np.zeros_like(up), np.zeros_like(low)
    sw = cv2.imread(os.path.join(SRC, f"cliff-{sheet}-shadow.png"), cv2.IMREAD_UNCHANGED).shape[1] // cols
    sh = np.zeros((up.shape[0], cols * sw, 4), np.uint8)
    for r in range(rows):
        for c in range(cols):
            y, x = r * CELL, c * CELL
            cu, cl = up[y:y + CELL, x:x + CELL], low[y:y + CELL, x:x + CELL]
            if max(cu[..., 3].max(), cl[..., 3].max()) == 0:
                continue
            im = render(pad(cu), pad(cl), zlib.crc32(f"{sheet}-{r}-{c}".encode()))
            low_side, caster = low_ground(*orientation(sheet, r, c), im.shape[:2])
            sh[y:y + CELL, c * sw:(c + 1) * sw] = shadow_cell(im[..., 3], sw, low_side, caster)
            crop = im[PAD:PAD + CELL, PAD:PAD + CELL].copy()
            crop[body_of(cu, cl) == 0] = 0            # la silhouette d'origine, au pixel près
            hi[y:y + CELL, x:x + CELL], lo[y:y + CELL, x:x + CELL] = split(crop, cu, cl)
    dst = os.path.join(out, "base", "terrain", "cliffs")
    os.makedirs(dst, exist_ok=True)
    cv2.imwrite(os.path.join(dst, f"cliff-{sheet}.png"), hi)
    cv2.imwrite(os.path.join(dst, f"cliff-{sheet}-lower.png"), lo)
    cv2.imwrite(os.path.join(dst, f"cliff-{sheet}-shadow.png"), sh)

