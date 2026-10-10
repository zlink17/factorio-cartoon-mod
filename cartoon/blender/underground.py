"""Souterrains (underground-belt, fast-, express-) : le capot qui recouvre la moitié de la case côté tunnel.

Usage : python cartoon/blender/underground.py <dossier_sortie> [convoyeur|tous]

Pour chaque niveau, écrit les fichiers du prototype d'origine :
  <nom>-structure.png              768 x 768 : 4 colonnes (nord, est, sud, ouest) de cellules de 192 x 192 ;
                                   rangée 0 = sortie, 1 = entrée, 2 et 3 = les mêmes pour l'est et l'ouest (chargement par le côté)
  <nom>-structure-back-patch.png   192 x 768, vide
  <nom>-structure-front-patch.png  192 x 768, vide
  <nom>-icon.png                   icône 64 px + mipmaps

Le capot couvre la moitié aval de la case pour une entrée (le tapis y disparaît) et la moitié amont pour une
sortie, avec un léger débord pour cacher les objets au bord. La cellule d'une sortie est celle de la direction
opposée (c'est ce que fait Factorio, vérifié en jeu : sinon les chevrons sont à l'envers). Le dessus porte des chevrons sombres qui pointent dans le sens du flux (bande de danger).
Les pièces « patch » de l'original servent à cacher les objets qui entrent sous le capot : on les laisse vides,
donc les objets passent un instant par-dessus le bord du capot (à revoir en jeu).
L'ordre des colonnes (N, E, S, O) et la moitié couverte par le capot sont déduits de l'original, sans certitude.
"""
import math, os, sys
import bpy, bmesh
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from belt import BELTS, build_belt
from lib import flatten_to_shadow, mat, mip_strip, render_icon, render_scene, reset

P = S.PALETTE
CELL = 192
PX_PER_TILE = 64
SHADOW = (0.5, 0.02, 0.4)          # décalage au sol par unité de hauteur (x, y) et opacité
OUTLINE = 0.009                    # contour plus fin que le style de base (pièces de 0,5 case)
DIRS = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}

UNDERGROUNDS = {
    "underground-belt": "transport-belt",
    "fast-underground-belt": "fast-transport-belt",
    "express-underground-belt": "express-transport-belt",
    "turbo-underground-belt": "turbo-transport-belt",
}

HOOD_H = 0.42            # hauteur du capot à la bouche
HOOD_LOW = 0.12          # hauteur au bout opposé (le toit descend jusqu'au sol)
HOOD_W = 0.5             # demi-largeur
HOOD_LEN = 0.62          # longueur du capot le long du flux : un peu plus que la demi-case, pour cacher les objets au bord
WALL = 0.09              # épaisseur des parois
ROOF = 0.07              # épaisseur du toit


def wprism(to_world, g, nu, nv, zb, zt, m):
    """Prisme dont les faces du dessus et du dessous suivent les hauteurs zt(s, d) et zb(s, d), s étant l'abscisse
    le long du flux et d le décalage en travers. g(u, v) -> (s, d) ; to_world(s, d) -> (x, y)."""
    bm = bmesh.new()
    top, bot = [], []
    for i in range(nu + 1):
        rt, rb = [], []
        for j in range(nv + 1):
            s, d = g(i / nu, j / nv)
            x, y = to_world(s, d)
            rt.append(bm.verts.new((x, y, zt(s, d))))
            rb.append(bm.verts.new((x, y, zb(s, d))))
        top.append(rt)
        bot.append(rb)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]))
    for i in range(nu):
        bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))
        bm.faces.new((top[i][nv], top[i + 1][nv], bot[i + 1][nv], bot[i][nv]))
    for j in range(nv):
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((bot[nu][j], bot[nu][j + 1], top[nu][j + 1], top[nu][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("hood")
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("hood", mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(m)
    return o


def build_hood(direction, entering, belt):
    """Ajoute le capot à la scène (sans la réinitialiser). `direction` : N, E, S ou O ; `entering` : entrée ou sortie.

    Entrée : la bouche est au bord amont (le tapis y arrive) et le toit descend vers l'aval, où le tapis plonge. Le toit est une plaque courbée le long du flux (quart d'ellipse), comme dans le jeu d'origine.
    Sortie : la bouche est au bord aval (le tapis en sort) et le toit descend vers l'amont."""
    fx, fy = DIRS[direction]
    lx, ly = -fy, fx                                  # gauche du flux
    rail, dark = mat("hood", P[BELTS[belt]["rail"]]), mat("stripe", P["dark"])
    steel = mat("hood_steel", P["grey"])
    mouth = -0.04 if entering else 0.04               # abscisse de la bouche, le long du flux
    inward = 1 if entering else -1                    # sens de la bouche vers l'intérieur du capot

    def to_world(s, d):
        return fx * s + lx * d, fy * s + ly * d

    def height(s):                                    # profil le long du flux : quart d'ellipse, haut à la bouche, courbé vers le sol
        x = min(1.0, abs(s - mouth) / HOOD_LEN)
        return HOOD_LOW + (HOOD_H - HOOD_LOW) * math.sqrt(1.0 - x * x)

    def roof(s, d):                                   # dessus du toit : plat en travers
        return height(s)

    def along(t0, t1):                                # abscisse à la profondeur t (de la bouche vers l'intérieur)
        return lambda u: mouth + inward * (t0 + (t1 - t0) * u)

    def body(d0, d1, t0, t1, zb, zt, m, nu=8, nv=1):
        s_of = along(t0, t1)
        wprism(to_world, lambda u, v: (s_of(u), d0 + (d1 - d0) * v), nu, nv, zb, zt, m)

    ground = lambda s, d: 0.0
    under = lambda s, d: roof(s, d) - ROOF
    body(HOOD_W - WALL, HOOD_W, 0.0, HOOD_LEN, ground, roof, steel, 16)                            # paroi gauche (bord métallique)
    body(-HOOD_W, -HOOD_W + WALL, 0.0, HOOD_LEN, ground, roof, steel, 16)                          # paroi droite
    body(-HOOD_W, HOOD_W, 0.0, HOOD_LEN, under, roof, rail, 16, 4)                                 # toit courbé
    body(-HOOD_W, HOOD_W, HOOD_LEN - 0.04, HOOD_LEN, ground, roof, rail, 2, 4)                   # paroi du bout, côté sol
    # fond du tunnel : sombre, visible par la bouche
    body(-HOOD_W + WALL, HOOD_W - WALL, 0.03, 0.09, ground, under, dark, 2, 2)
    # chevrons de danger sur l'arche : trois, pointant dans le sens du flux
    for k in range(3):
        sa = mouth + inward * HOOD_LEN * (k + 0.6) / 3

        def g(u, v, sa=sa):
            d = (2 * u - 1) * (HOOD_W - WALL - 0.03)
            return sa - 0.13 * abs(d) / HOOD_W + (v - 0.5) * 0.075, d
        wprism(to_world, g, 16, 1, roof, lambda s, d: roof(s, d) + 0.012, dark)
    # linteau (arqué) et montants en acier autour de la bouche
    body(-HOOD_W, HOOD_W, -0.015, 0.075, lambda s, d: roof(s, d) - ROOF - 0.1, lambda s, d: roof(s, d) + 0.02, steel, 2, 4)
    for sd in (-1, 1):
        body(sd * (HOOD_W - 0.035) - 0.035, sd * (HOOD_W - 0.035) + 0.035, -0.015, 0.075, ground,
             lambda s, d: roof(s, d) - ROOF - 0.1, steel, 2, 1)
    return to_world


def build_scene(direction, entering, belt):
    reset()
    build_hood(direction, entering, belt)


def render_cell(direction, entering, belt, out):
    """Une cellule 192 x 192 : le capot et son ombre à plat (semi-transparente)."""
    path = os.path.join(out, "_ug.png")
    scale = CELL / PX_PER_TILE
    build_scene(direction, entering, belt)
    render_scene(path, size=CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline_units=OUTLINE)
    sprite = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    build_scene(direction, entering, belt)
    flatten_to_shadow(SHADOW[0], SHADOW[1])
    render_scene(path, size=CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline=False)
    shadow = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    shadow[:, :, :3] = 0
    shadow[:, :, 3] = (shadow[:, :, 3] * SHADOW[2]).astype(np.uint8)
    return over(sprite, shadow)


def over(top, bottom):
    ta, ba = top[:, :, 3:4] / 255.0, bottom[:, :, 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


def build_icon(belt, out):
    def model():
        build_belt(0, 0, BELTS[belt])                 # un tronçon de convoyeur (réinitialise la scène)
        build_hood("E", True, belt)                   # et le capot par-dessus
    icon = render_icon(model, os.path.join(out, "_icon.png"), 64, 60)
    return mip_strip(icon, 64)


def build_underground(name, out):
    belt = UNDERGROUNDS[name]
    cells = {(d, e): render_cell(d, e, belt, out) for d in DIRS for e in (False, True)}
    sheet = np.zeros((4 * CELL, 4 * CELL, 4), np.uint8)
    for col, d in enumerate(DIRS):
        for row, entering in ((0, False), (1, True)):
            # Factorio dessine une sortie avec la cellule de la direction opposée (comme dans l'original, où la
            # cellule « sortie est » a les chevrons tournés vers l'ouest) : on y range donc la sortie du flux inverse.
            src = cells[(d, entering)] if entering else cells[(OPPOSITE[d], False)]
            sheet[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL] = src
            if d in ("E", "W"):                       # chargement par le côté : mêmes images
                sheet[(row + 2) * CELL:(row + 3) * CELL, col * CELL:(col + 1) * CELL] = src
    cv2.imwrite(os.path.join(out, f"{name}-structure.png"), sheet)
    empty = np.zeros((CELL, 4 * CELL, 4), np.uint8)
    cv2.imwrite(os.path.join(out, f"{name}-structure-back-patch.png"), empty)
    cv2.imwrite(os.path.join(out, f"{name}-structure-front-patch.png"), empty)
    cv2.imwrite(os.path.join(out, f"{name}-icon.png"), build_icon(belt, out))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "underground_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (UNDERGROUNDS if which == "tous" else [which]):
        build_underground(name, out)
        print("OK", name, flush=True)
