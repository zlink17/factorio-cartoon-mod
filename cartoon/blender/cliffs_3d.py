"""Falaises de Nauvis : relief à facettes, tons de l'original, ombres portées selon le relief.

Usage : python cartoon/blender/cliffs_3d.py <dossier_sortie> [planche[,planche...]|toutes]
        planche = sides, outer, inner, entrance

Pour chaque cellule (prolongée de ses bords), un relief : un maillage dont chaque sommet reste sur son pixel à
l'écran (la silhouette d'origine ne bouge pas) et ne reçoit qu'une hauteur. Avec la caméra des bâtiments (30° de
la verticale, sol raccourci par cos 30°), un point de hauteur z vu à la hauteur d'écran s est posé au sol en
y = (s - z sin 30°) / cos 30°. Hauteur : une paroi presque verticale qui monte depuis le pied de la roche (colonne
par colonne), découpée en dalles par un bruit étiré à la verticale ; Blender simplifie le maillage en facettes
planes (Decimate). On ne rend pas le maillage : on projette ses facettes à l'écran et chacune prend la luminosité
moyenne de l'original sous elle, ramenée à 4 tons (seuils communs à toutes les falaises) ; trait entre deux
facettes de tons différents, contour noir chaud. L'éclairage est donc celui de Wube (parois éclairées à gauche,
à contre-jour à droite), le dessin en pans nets.
Écartés (choix de Bastien, 11 octobre) : colonnes hexagonales (ombres fausses, « colonnes de granite ») ; tons du
rendu 3D (lib.mat) : un relief inventé met les clairs et les sombres au hasard ; blocs anguleux, lobes, talus.
Lecture de l'original, ombres portées et découpe en calques : cartoon/terrain/cliffs.py.
"""
import math
import os
import sys

import bpy
import bmesh
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "terrain"))
import style as S  # noqa: E402
from lib import reset  # noqa: E402
import cliffs as C  # noqa: E402
from cliffs import SS  # noqa: E402

PX = 64.0                # px du fichier par case (échelle 0,5)
GRID = 3                 # pas du maillage (px)
WALL_MAX_PX = 180        # hauteur d'écran maximale de la paroi (au-delà : plateau)
STEEP = 1.9              # z / s : 2 = paroi verticale vue à 30° ; un peu moins, elle penche en arrière
EDGE_PX = 6              # arrondi des autres bords
NOISE = 0.25             # dalles (part de la hauteur)
DECIMATE = 0.04


def heights(body, rng):
    """Hauteur (cases) par pixel de la cellule prolongée : une paroi qui monte depuis le pied (bord bas de la
    roche, colonne par colonne) jusqu'au rebord, presque verticale (z = 2 s à 30°), arrondie sur les autres bords,
    bosselée en dalles verticales."""
    h, w = body.shape
    run = np.where(body[-1] > 0, 1e6, 0).astype(np.float32)    # roche coupée par le bord : la paroi continue
    from_foot = np.zeros((h, w), np.float32)
    for y in range(h - 1, -1, -1):
        run = np.where(body[y] > 0, run + 1, 0)
        from_foot[y] = run
    wall = np.minimum(from_foot, WALL_MAX_PX) / PX * STEEP     # z = 2 s : paroi verticale vue à 30°
    dt = cv2.distanceTransform(body.astype(np.uint8), cv2.DIST_L2, 5)
    edge = np.clip(dt / EDGE_PX, 0, 1) ** 0.5                     # bords arrondis (rebord en haut)
    noise = rng.standard_normal(body.shape).astype(np.float32)
    noise = cv2.GaussianBlur(noise, (0, 0), sigmaX=6, sigmaY=20)
    noise /= max(noise.std(), 1e-6)
    return wall * edge * (1 + NOISE * noise) * body


def build_mesh(body, z):
    h, w = body.shape
    p = math.radians(S.PITCH_BUILDING_DEG)
    bm = bmesh.new()
    ys = list(range(0, h, GRID))
    xs = list(range(0, w, GRID))
    verts = {}
    for j, py in enumerate(ys):
        for i, px in enumerate(xs):
            if not body[py, px]:
                continue
            zz = float(z[py, px])
            s = (h / 2 - py) / PX                     # hauteur à l'écran (cases), centre de la cellule = 0
            x = (px - w / 2) / PX
            y = (s - zz * math.sin(p)) / math.cos(p)
            verts[(i, j)] = bm.verts.new((x, y, zz))
    for (i, j), v in verts.items():
        q = [verts.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
        if all(q):
            bm.faces.new((q[0], q[3], q[2], q[1]))
    me = bpy.data.meshes.new("cliff")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("cliff", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.ratio = DECIMATE
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier="dec")
    for f in ob.data.polygons:
        f.use_smooth = False
    return ob


TONE_CUTS = (28, 62, 90)  # centiles de luminosité de l'original : creux / flanc sombre / flanc éclairé / dessus


_CUTS = []


def global_cuts():
    """Seuils de tons communs à toutes les falaises (centiles sur toutes les planches) : une paroi tournée vers la
    lumière reste claire, une paroi à contre-jour reste sombre (des seuils par cellule les ramenaient au même
    mélange)."""
    if not _CUTS:
        vals = []
        for sh in C.SHEETS:
            up, low = C.load(sh)
            body = C.body_of(up, low)
            lum = C.luminance(up.astype(np.float32), low.astype(np.float32), body)
            vals.append(lum[body > 0][::7])
        _CUTS.append(np.percentile(np.concatenate(vals), TONE_CUTS))
    return _CUTS[0]


def facets(up, low, seed):
    """La géométrie du relief (facettes du maillage simplifié, projetées à l'écran) et le ton
    de l'original. Chaque facette prend la luminosité moyenne de l'original sous elle, ramenée à 4 tons : l'éclairage
    reste celui de Wube (continu d'une cellule à l'autre), le dessin devient des pans nets. Trait entre deux facettes
    de tons différents seulement (sinon on dessine le maillage)."""
    body = C.body_of(up, low)
    h, w = body.shape
    if body.sum() < 20:
        return np.zeros((h, w, 4), np.uint8)
    lum = C.luminance(up.astype(np.float32), low.astype(np.float32), body)
    cuts = global_cuts()
    reset()
    ob = build_mesh(body, heights(body, np.random.default_rng(seed)))
    p = math.radians(S.PITCH_BUILDING_DEG)
    me = ob.data
    co = np.array([v.co[:] for v in me.vertices], np.float64)
    sx = (co[:, 0] * PX + w / 2) * SS
    sy = (h / 2 - (co[:, 1] * math.cos(p) + co[:, 2] * math.sin(p)) * PX) * SS
    H, W = h * SS, w * SS
    lum_big = cv2.resize(lum, (W, H), interpolation=cv2.INTER_LINEAR)
    ids = np.full((H, W), -1, np.int32)
    polys = sorted(me.polygons, key=lambda f: -np.mean(co[list(f.vertices), 1]))   # du fond vers l'avant
    for k, f in enumerate(polys):
        pts = np.stack([sx[list(f.vertices)], sy[list(f.vertices)]], 1)
        cv2.fillPoly(ids, [np.round(pts).astype(np.int32)], k)
    inside = C.big(body)
    tone = np.digitize(lum_big, cuts).astype(np.int32)                 # repli : ton du pixel
    valid = (ids >= 0) & inside
    if valid.any():
        n = len(polys)
        sums = np.bincount(ids[valid], weights=lum_big[valid], minlength=n)
        cnt = np.bincount(ids[valid], minlength=n)
        mean = sums / np.maximum(cnt, 1)
        tone[valid] = np.digitize(mean, cuts)[ids[valid]]
    cols = np.array([C.hx(c) for c in C.ROCK], np.float32)
    color = cols[tone]
    t8 = tone.astype(np.uint8)
    k3 = np.ones((3, 3), np.uint8)
    lines = (cv2.morphologyEx(t8, cv2.MORPH_GRADIENT, k3) > 0) & (t8 == cv2.erode(t8, k3))   # côté sombre du bord
    return C.finish(color, inside, lines)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = argv[0]
    which = argv[1] if len(argv) > 1 else "toutes"
    for sh in (C.SHEETS if which == "toutes" else which.split(",")):
        C.build(sh, out, facets)
        print("OK", sh, flush=True)
