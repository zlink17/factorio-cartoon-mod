"""Convoyeurs (transport-belt, fast-transport-belt, express-transport-belt), vus directement du dessus.

Usage : python cartoon/blender/belt.py <dossier_sortie> [convoyeur|tous] [nb d'images max, pour tester]

Écrit <convoyeur>-icon.png (icône 64 px + mipmaps, 120 x 64) et <convoyeur>.png : la planche de l'original, 20 rangées de `frames` images de 128 x 128 px
(64 px par case, la case est centrée dans l'image).

Rangées (comme l'original) :
  0-3    droits : est, ouest, nord, sud
  4-11   courbes, deux sens par coin : NE (4, 5), NO (6, 7), SE (8, 9), SO (10, 11)
  12-19  bouts de ligne : haut (12 animé, 13 fixe), droite (14, 15), bas (16, 17), gauche (18, 19)
Les rangées ont été identifiées par le mouvement des chevrons dans l'original (flux optique), pas par
les noms des index du prototype : si un bout de ligne est à l'envers en jeu, échanger les rangées.

Principe : le convoyeur est modélisé « à plat » (s le long du flux, d en travers), puis chaque point est
envoyé dans le monde par `place` : identité pour un droit, coordonnées polaires autour du coin pour une courbe.
Les stries avancent de 2 px par image, comme dans l'original (même vitesse que les objets transportés) ;
une strie sur deux (une sur quatre pour le rapide et l'express) porte une flèche colorée.
"""
import math, os, sys
import bpy, bmesh
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import mip_strip, reset, mat, render_scene

P = S.PALETTE
FRAME = 128
PX_PER_TILE = 64
MARGIN = 2 / PX_PER_TILE          # recouvrement de 2 px entre cases voisines (contours)

# frames : images par rangée ; rail : couleur des rails et des flèches ;
# arrow_every : une strie sur n porte une flèche (comme l'original : 1/2 pour le basique, 1/4 ensuite)
BELTS = {
    "transport-belt":         dict(frames=16, rail="yellow", arrow_every=2),
    "fast-transport-belt":    dict(frames=32, rail="red", arrow_every=4),
    "express-transport-belt": dict(frames=32, rail="steel_blue", arrow_every=4),
}

HALF = 0.5                 # demi-largeur de la case
BAND = 0.31                # demi-largeur de la bande sombre (le reste = rails colorés)
CHEVRON_BACK = 0.17        # recul des branches du chevron
RIDGE_THICK = 0.12         # épaisseur d'une strie
ARROW_THICK = 0.2          # épaisseur d'une flèche (strie qui porte la flèche)
RIDGES_PER_TILE = 4        # une strie tous les 16 px, comme l'original
Z_BAND, Z_RAIL, Z_CHEVRON = 0.04, 0.12, 0.09
OVERSHOOT = 0.1            # les pistes dépassent la case de cette longueur avant rognage

# (type, paramètres) pour les 20 rangées
#   droit : angle du flux en degrés
#   courbe : (coin, sens, angle de départ, signe) ; coin = centre de l'arc, signe +1 = antihoraire
#   bout : (angle vers l'extérieur, animé)
ROWS = (
    [("straight", a) for a in (0, 180, 90, 270)] +
    [("curve", c) for c in (
        ((0.5, 0.5), -90, -1), ((0.5, 0.5), 180, 1),     # NE
        ((-0.5, 0.5), -90, 1), ((-0.5, 0.5), 0, -1),     # NO
        ((0.5, -0.5), 180, -1), ((0.5, -0.5), 90, 1),    # SE
        ((-0.5, -0.5), 0, 1), ((-0.5, -0.5), 90, -1),    # SO
    )] +
    [("end", (a, anim)) for a in (90, 0, 270, 180) for anim in (True, False)]
)


def prism(f, nu, nv, z0, z1, m):
    """Prisme dont la face du dessus est la grille f(u, v) -> (x, y), u et v dans [0, 1]."""
    bm = bmesh.new()
    top = [[bm.verts.new((*f(i / nu, j / nv), z1)) for j in range(nv + 1)] for i in range(nu + 1)]
    bot = [[bm.verts.new((*f(i / nu, j / nv), z0)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
    for i in range(nu):                                   # côtés v = 0 et v = 1
        bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))
        bm.faces.new((top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv]))
    for j in range(nv):                                   # côtés u = 0 et u = 1
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((bot[nu][j], bot[nu][j + 1], top[nu][j + 1], top[nu][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("belt")
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("belt", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    return o


def make_place(kind, arg):
    """Renvoie (place, L, P) : place(s, d) -> (x, y), longueur de la piste, période des chevrons."""
    if kind == "straight":
        a = math.radians(arg)
        c, s_ = math.cos(a), math.sin(a)
        return (lambda s, d: (s * c - d * s_, s * s_ + d * c)), 1.0, 1.0 / RIDGES_PER_TILE
    corner, th0, sign = arg
    L = HALF * math.pi / 2

    def place(s, d):
        theta = math.radians(th0) + sign * (s + L / 2) / HALF
        rho = HALF + (d if sign < 0 else -d)               # centre à droite (sens horaire) : d > 0 s'éloigne
        return corner[0] + rho * math.cos(theta), corner[1] + rho * math.sin(theta)
    return place, L, 1.0 / RIDGES_PER_TILE


def build_belt(row, frame, cfg):
    reset()
    kind, arg = ROWS[row]
    dark, rail = mat("band", P["dark"]), mat("rail", P[cfg["rail"]])
    tread = mat("tread", P["tread"])
    steel = mat("steel", P["grey"])
    if kind == "end":
        angle, animated = arg
        place, L, period = make_place("straight", angle)
        lo, hi = HALF - 0.16, HALF + 0.12                   # fenêtre du bout de ligne (le long du flux)
    else:
        place, L, period = make_place(kind, arg)
        lo, hi = -L / 2 - OVERSHOOT, L / 2 + OVERSHOOT    # dépasse la case : le rognage supprime le contour des bouts
        animated = True
    if kind == "end":
        s_range = (lo, HALF)
    else:
        s_range = (lo, hi)
    n = max(2, int(round((s_range[1] - s_range[0]) * 24)))

    def strip(d0, d1, z0, z1, m, nv=1):
        s0, s1 = s_range
        return prism(lambda u, v: place(s0 + (s1 - s0) * u, d0 + (d1 - d0) * v), n, nv, z0, z1, m)

    strip(-BAND, BAND, 0.0, Z_BAND, dark, 4)
    strip(BAND, HALF, 0.0, Z_RAIL, rail)
    strip(-HALF, -BAND, 0.0, Z_RAIL, rail)

    if kind == "end":
        # rouleau à l'extrémité, qui dépasse de la case
        sx0, sx1 = HALF - 0.04, hi
        prism(lambda u, v: place(sx0 + (sx1 - sx0) * u, -HALF + 1.0 * v), 4, 8, 0.0, Z_RAIL + 0.02, steel)
    if animated:
        # Le motif est celui d'un droit de longueur 1 : stries aux multiples de `period`, flèche sur la strie k si
        # k % arrow_every == 0, avance de period / 8 par image (2 px, la vitesse des objets). Dans un virage on
        # l'étire sur la longueur de l'arc (`unit`) : stries et flèches tombent aux bords comme sur un droit,
        # donc elles se raccordent aux cases voisines à chaque image (la bande est 21 % plus lente sur l'arc).
        unit = L if kind == "curve" else 1.0
        period = 1.0 / RIDGES_PER_TILE
        shift = frame * period / 8
        for k in range(-12, 13):
            sa = unit * (k * period + shift)
            if sa < s_range[0] - CHEVRON_BACK - 0.1 or sa > s_range[1] + ARROW_THICK:
                continue
            if kind == "end" and sa > HALF:                 # pas de strie sous le rouleau
                continue
            arrow = k % cfg["arrow_every"] == 0
            thick = ARROW_THICK if arrow else RIDGE_THICK

            def chev(u, v, sa=sa, thick=thick):
                d = (2 * u - 1) * (BAND - 0.04)
                return place(sa - CHEVRON_BACK * abs(d) / BAND + (v - 0.5) * thick, d)
            prism(chev, 16, 1, Z_BAND, Z_CHEVRON + (0.02 if arrow else 0.0), rail if arrow else tread)


def tile_mask(row):
    """Masque 128 x 128 de la zone de la case (+ marge) dans l'image ; on rogne le reste."""
    kind, arg = ROWS[row]
    m = np.zeros((FRAME, FRAME), np.uint8)
    c = FRAME // 2
    half = int(PX_PER_TILE * (HALF + 0.03))
    if kind != "end":
        m[c - half:c + half, c - half:c + half] = 255
        return m
    angle, _ = arg
    e, d = int(PX_PER_TILE * (HALF - 0.16)), int(PX_PER_TILE * (HALF + 0.14))
    w = half
    x0, x1, y0, y1 = {90: (c - w, c + w, c - d, c - e), 0: (c + e, c + d, c - w, c + w),
                      270: (c - w, c + w, c + e, c + d), 180: (c - d, c - e, c - w, c + w)}[angle]
    m[y0:y1, x0:x1] = 255
    return m


def render_row(row, frame, cfg, out):
    build_belt(row, frame, cfg)
    path = os.path.join(out, "_belt.png")
    render_scene(path, size=FRAME, scale=FRAME / PX_PER_TILE, pitch_deg=S.PITCH_TOPDOWN_DEG)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    mask = tile_mask(row)
    im[:, :, 3] = np.minimum(im[:, :, 3], mask)
    im[mask == 0] = 0
    return im


def build_sheet(name, out, max_frames=None):
    cfg = BELTS[name]
    n = min(cfg["frames"], max_frames) if max_frames else cfg["frames"]
    sheet = np.zeros((len(ROWS) * FRAME, cfg["frames"] * FRAME, 4), np.uint8)
    for row in range(len(ROWS)):
        for f in range(n):
            sheet[row * FRAME:(row + 1) * FRAME, f * FRAME:(f + 1) * FRAME] = render_row(row, f, cfg, out)
        print(f"{name} rangée {row}/{len(ROWS) - 1}", flush=True)
    path = os.path.join(out, f"{name}.png")
    cv2.imwrite(path, sheet)
    return path


ICON = 64
ICON_FILL = 60                     # largeur de la case dans l'icône (px)
ICON_OUTLINE_PX = 0.5              # réglage empirique : rend environ 1,2 px de contour


def build_icon(name, out):
    """Icône : un virage vu de dessus (plus lisible qu'un tronçon droit), plus la bande de mipmaps (120 x 64)."""
    cfg = BELTS[name]
    build_belt(4, 0, cfg)
    scale = ICON / ICON_FILL
    path = os.path.join(out, "_icon.png")
    render_scene(path, size=ICON, scale=scale, pitch_deg=S.PITCH_TOPDOWN_DEG, supersample=4,
                 outline_units=ICON_OUTLINE_PX * scale / ICON)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    path = os.path.join(out, f"{name}-icon.png")
    cv2.imwrite(path, mip_strip(im, ICON))
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "belt_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    max_frames = int(sys.argv[3]) if len(sys.argv) > 3 else None
    os.makedirs(out, exist_ok=True)
    for name in (BELTS if which == "tous" else [which]):
        print("OK", build_icon(name, out))
        print("OK", build_sheet(name, out, max_frames))
