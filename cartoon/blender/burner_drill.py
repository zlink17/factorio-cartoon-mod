"""Foreuse à charbon (burner-mining-drill) : planches animées des 4 directions, ombres, icône.

Usage : python cartoon/blender/burner_drill.py <dossier_sortie> [direction[,direction...]|toutes] [--apercu]
        direction = N, E, S, W ; --apercu : une seule image par direction (réglages)

Écrit, aux chemins de l'original (base/entity/burner-mining-drill/ et base/icons/) :
  burner-mining-drill-<D>.png         32 images (4 par ligne) au cadre du prototype de la direction D
  burner-mining-drill-<D>-shadow.png  32 ombres, noires unies
  burner-mining-drill.png (icône)     64 px + mipmaps
Les restes sont laissés d'origine (lot 3.9).

La foreuse : quatre pieds arqués en fer sombre, plateau à ailes, carter et engrenages de laiton, vrille hélicoïdale
au centre qui s'enfonce dans le sol, piston, goulotte de sortie en cuivre rouillé du côté où tombe le minerai
(vector_to_place_result). Modèle construit vers le nord puis tourné pour chaque direction : l'éclairage (trois
tons selon l'orientation des faces) reste celui des autres bâtiments. L'animation (32 images, jouée en aller-retour
par le jeu) fait tourner engrenages et vrille et monter le piston.
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import (box, crop_centered, cyl, entity_path, gear, load, mat, render_scene, render_shadow, reset, rod,
                 save_icon, sheet)

P = S.PALETTE
NAME = "burner-mining-drill"
PX_PER_TILE = 64
CANVAS = 448
N_FRAMES, COLUMNS = 32, 4
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.018                            # pièces fines : contour un peu plus fin que la base
# cadre de chaque direction (taille, décalage en px = shift x 64), sprite puis ombre, d'après le prototype
FRAMES = {
    "N": (((173, 188), (5.5, 1.0)), ((217, 150), (47.5, -2.0))),
    "E": (((185, 168), (5.5, 2.0)), ((185, 128), (27.5, 1.0))),
    "S": (((174, 174), (1.0, -1.0)), ((174, 137), (22.0, 5.5))),
    "W": (((180, 176), (-3.0, 0.0)), ((176, 130), (15.0, 2.0))),
}
# pieds (courbe de Bézier : pied au sol, point de contrôle, sommet sous le plateau) et hauteur du plateau,
# ajustés sur la silhouette de l'original dans les quatre directions
LEG = dict(fx=0.87, fy=0.91, cx=0.85, cy=0.75, cz=0.54, tx=0.29, ty=0.4, zt=1.02)
YAW = {"N": 0, "E": -90, "S": 180, "W": 90}   # rotation du modèle (degrés, autour de z) ; nord = goulotte au fond


def vgear(center, r, depth, teeth, angle, m, hub_m, axis="y"):
    """Engrenage vertical (axe y : face vers l'avant ; axe x : face vers le côté)."""
    import bpy
    o = gear((0, 0, 0), r, depth, teeth, angle, m)
    o.location = center
    o.rotation_euler = (math.radians(90), 0, 0) if axis == "y" else (0, math.radians(90), 0)
    hub = cyl(center, r * 0.34, depth * 1.4, hub_m, verts=12,
              rot=(90, 0, 0) if axis == "y" else (0, 90, 0))
    return o, hub


def mesh(verts, faces, m, name="part"):
    """Objet d'un seul maillage (contour sur la silhouette seulement)."""
    import bpy, bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    return o


def leg(sx, sy, m, g, w=0.15, t=0.07, n=10):
    """Pied arqué : poutre plate balayée le long d'une courbe de Bézier, du sol (coin) jusque sous le plateau,
    bombée vers l'extérieur ; sa largeur est tournée vers l'extérieur (face visible de devant et de côté)."""
    p0 = np.array([g["fx"] * sx, g["fy"] * sy, 0.0])
    p1 = np.array([g["cx"] * sx, g["cy"] * sy, g["cz"]])
    p2 = np.array([g["tx"] * sx, g["ty"] * sy, g["zt"]])
    side = np.array([sy, -sx, 0.0]) / math.sqrt(2)              # horizontal, perpendiculaire à la diagonale
    verts = []
    for k in range(n + 1):
        u = k / n
        p = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u * u * p2
        d = 2 * (1 - u) * (p1 - p0) + 2 * u * (p2 - p1)
        d /= np.linalg.norm(d)
        nrm = np.cross(d, side)                                  # épaisseur : vers l'extérieur de l'arche
        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(tuple(p + side * a * w / 2 + nrm * b * t / 2))
    faces = [(0, 1, 2, 3), tuple(4 * n + i for i in (3, 2, 1, 0))]
    for k in range(n):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((4 * k + i, 4 * k + j, 4 * (k + 1) + j, 4 * (k + 1) + i))
    return mesh(verts, faces, m, "leg")


def auger(z0, z1, phase, m, axis_m, r=0.25, turns=3.0, n=72):
    """Vrille : axe et filet hélicoïdal d'un seul ruban, qui tourne avec la phase."""
    cyl((0, 0, (z0 + z1) / 2), 0.05, z1 - z0, axis_m, verts=10)
    verts, faces = [], []
    a0 = phase * 2 * math.pi * 2
    for k in range(n + 1):
        u = k / n
        a = a0 + u * turns * 2 * math.pi
        z = z0 + (z1 - z0) * u
        for rad, dz in ((0.05, 0.0), (r, -0.03)):
            verts.append((rad * math.cos(a), rad * math.sin(a), z + dz))
    for k in range(n):
        faces.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    o = mesh(verts, faces, m, "auger")
    mod = o.modifiers.new("epaisseur", "SOLIDIFY")
    mod.thickness = 0.04
    return o


def build(direction="N", phase=0.0, g=None):
    import bpy
    from mathutils import Matrix
    reset()
    iron, dark = mat("iron", P["drill_iron"]), mat("dark", P["dark"])
    steel, brass = mat("steel", P["grey"]), mat("brass", P["yellow"])
    rust, light = mat("rust", P["orange"]), mat("light", P["white"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg(sx, sy, iron, g or LEG)
    zt = (g or LEG)["zt"]
    # plateau : carré central, ailes vers la gauche et la droite
    box((0, 0, zt), (0.95, 0.9, 0.07), iron, 0.01)
    box((0, 0.1, zt + 0.04), (1.5, 0.2, 0.05), iron, 0.01)
    # carter et engrenages
    box((0.05, 0.02, zt + 0.2), (0.44, 0.36, 0.3), mat("case", P["drill_auger"]), 0.02)
    a = phase * 360
    vgear((-0.14, -0.24, zt + 0.3), 0.22, 0.06, 10, a, brass, steel)
    vgear((0.2, -0.24, zt + 0.22), 0.14, 0.06, 7, -a * 10 / 7 + 15, brass, steel)
    vgear((0.12, -0.24, zt + 0.5), 0.11, 0.06, 6, -a * 10 / 6 + 20, steel, dark)
    vgear((0.32, 0.0, zt + 0.32), 0.15, 0.06, 8, a * 1.3, brass, steel, axis="x")
    # piston : tige claire qui monte et descend à droite du carter
    lift = 0.12 * math.sin(phase * math.pi * 2)
    box((0.42, -0.15, zt + 0.15), (0.12, 0.12, 0.3), steel, 0.01)
    rod((0.42, -0.15, zt + 0.25), (0.42, -0.15, zt + 0.55 + lift), 0.035, light, verts=8)
    # vrille au centre, du plateau jusque dans le sol
    auger(-0.02, zt - 0.08, phase, mat("auger", P["drill_auger"]), dark)
    # foyer : panneau vertical gris-bleu contre le pied avant droit
    box((0.5, -0.5, 0.5), (0.2, 0.14, 0.9), mat("firebox", P["blue"]), 0.015)
    # goulotte de sortie : descend en biais vers le point où tombe le minerai, (-0.5, -1.3) au nord dans le jeu,
    # soit l'arrière gauche dans Blender (y +) ; ouverte en bas
    top, bot = np.array([-0.2, 0.3, zt + 0.1]), np.array([-0.5, 1.05, 0.12])
    d = bot - top
    length = float(np.linalg.norm(d))
    tilt = math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1])))
    yaw = math.degrees(math.atan2(d[0], d[1]))
    mid = (top + bot) / 2
    o = box(tuple(mid), (0.32, length, 0.18), rust, 0.02)
    o.rotation_euler = (math.radians(-tilt), 0, math.radians(-yaw))
    o = box(tuple(mid + np.array([0, 0, 0.09])), (0.22, length * 0.92, 0.03), dark)
    o.rotation_euler = (math.radians(-tilt), 0, math.radians(-yaw))
    bpy.context.view_layer.update()          # matrices à jour (sinon le dernier objet perd son échelle)
    rot = Matrix.Rotation(math.radians(YAW[direction]), 4, "Z")
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world


def frame(direction, phase, out):
    """Une image de la direction : sprite et ombre, découpés aux cadres de l'original."""
    path = os.path.join(out, "_drill.png")
    build(direction, phase)
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE)
    sprite = crop_centered(load(path), *FRAMES[direction][0])
    shadow = render_shadow(lambda: build(direction, phase), path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR)
    return sprite, crop_centered(shadow, *FRAMES[direction][1])


def render_direction(direction, out, preview=False):
    n = 1 if preview else N_FRAMES
    sprites, shadows = zip(*[frame(direction, i / N_FRAMES, out) for i in range(n)])
    if preview:
        sprites, shadows = sprites * N_FRAMES, shadows * N_FRAMES
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{direction}.png"), sheet(list(sprites), COLUMNS))
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{direction}-shadow.png"), sheet(list(shadows), COLUMNS))


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "burner_drill_out"
    which = args[1] if len(args) > 1 else "toutes"
    os.makedirs(out, exist_ok=True)
    for d in (FRAMES if which == "toutes" else which.split(",")):
        render_direction(d, out, preview)
        print("OK", d, flush=True)
    if which == "toutes":
        save_icon(out, NAME, lambda: build("N", 0.0))
