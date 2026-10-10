"""Pylônes électriques (small-electric-pole, medium-electric-pole, big-electric-pole, substation) et câbles.

Usage : python cartoon/blender/pole.py <dossier_sortie> [pylône|tous]

Pour chaque pylône, écrit les fichiers du prototype d'origine :
  <nom>.png          4 variantes côte à côte (le moteur choisit celle qui évite le chevauchement des câbles)
  <nom>-shadow.png   les 4 ombres
  <nom>-icon.png     icône 64 px + mipmaps
et, pour les câbles (jeu « core »), copper-wire.png, red-wire.png, green-wire.png, wire-shadow.png, wire-highlight.png.

Les câbles s'accrochent aux points définis par le prototype (« connection_points », en pixels par rapport au
centre de l'entité), donc les isolateurs de chaque variante sont placés exactement là. Un point d'attache est
une position à l'écran : on retrouve sa position dans le monde en supposant que chaque isolateur est à hauteur
constante sur sa variante 0 (bras dans le plan de l'image), puis en déduisant la profondeur dans les autres.
"""
import math, os, sys
import bpy
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, cyl, flatten_to_shadow, mat, mip_strip, render_icon, render_scene, reset

P = S.PALETTE
PX_PER_TILE = 64
SIN, COS = math.sin(math.radians(S.PITCH_BUILDING_DEG)), math.cos(math.radians(S.PITCH_BUILDING_DEG))
OUTLINE = 0.013                   # contour plus fin que le style de base : pièces très élancées
SHADOW = (0.45, 0.0, 0.4)         # décalage au sol par unité de hauteur (x, y) et opacité
CANVAS = 800


def g(v):                          # by_pixel : 32 px par case
    return v / 32.0


def h(v):                          # by_pixel_hr : 64 px par case
    return v / 64.0


def pts(unit, rows):
    """rows : 4 variantes de {copper, red, green} -> (x, y) en px ; renvoie en cases, y vers le bas de l'écran."""
    return [{k: (unit(x), unit(y)) for k, (x, y) in row.items()} for row in rows]


POLES = {
    "small-electric-pole": dict(
        cell=(72, 220), shift=(3, -85), shadow=((256, 52), (102, 6)), kind="wood", color="tan",
        points=pts(g, [
            dict(copper=(0, -82.5), red=(13, -81), green=(-12.5, -81)),
            dict(copper=(1.5, -81), red=(12, -76), green=(-6, -89.5)),
            dict(copper=(2.5, -79.5), red=(4, -71), green=(5, -89.5)),
            dict(copper=(0.5, -86.5), red=(-10.5, -81.5), green=(8, -93.5))])),
    "medium-electric-pole": dict(
        cell=(84, 252), shift=(7, -88), shadow=((280, 64), (113, -2)), kind="tower", color="coral", base=0.42, top=0.12,
        points=pts(h, [
            dict(copper=(15, -199), red=(43, -179), green=(-15, -185)),
            dict(copper=(15, -199), red=(27, -167), green=(-9, -200)),
            dict(copper=(15, -199), red=(5, -166), green=(13, -206)),
            dict(copper=(15, -199), red=(-12, -175), green=(36, -199))])),
    "big-electric-pole": dict(
        cell=(148, 312), shift=(0, -102), shadow=((374, 94), (120, 0)), kind="tower", color="steel_light", base=0.95, top=0.2,
        points=pts(h, [
            dict(copper=(0, -246), red=(58, -211), green=(-58, -211)),
            dict(copper=(34, -235), red=(41, -183), green=(-40, -240)),
            dict(copper=(47, -212), red=(1, -170), green=(1, -251)),
            dict(copper=(33, -188), red=(-41, -182.5), green=(41, -239))])),
    "substation": dict(
        cell=(138, 270), shift=(0, -62), shadow=((370, 104), (124, 20)), kind="substation", color="steel_blue",
        points=pts(g, [
            dict(copper=(0, -86), green=(-21, -82), red=(22, -81)),
            dict(copper=(0, -85), green=(15, -70), red=(-15, -92)),
            dict(copper=(0, -85), green=(0, -66), red=(0, -97)),
            dict(copper=(0, -86), green=(-15, -71), red=(15, -92))])),
}


def tips(cfg):
    """Pour chaque variante, la position monde (x, y, z) du bout de chaque isolateur."""
    base = cfg["points"][0]
    z = {k: 2 * -base[k][1] for k in base}        # variante 0 : y monde = 0, donc haut d'écran = z * sin(30°)
    out = []
    for row in cfg["points"]:
        o = {}
        for k, (sx, sy) in row.items():
            up = -sy
            o[k] = (sx, (up - SIN * z[k]) / COS, z[k])
        out.append(o)
    return out


def rod(p0, p1, r, m, verts=8):
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)
    return o


def build_pole(name, variant):
    reset()
    cfg = POLES[name]
    main = mat("main", P[cfg["color"]])
    dark, steel = mat("dark", P["dark"]), mat("steel", P["grey"])
    white, wood = mat("white", P["white"]), main
    accent = mat("accent", P["brown"] if cfg["color"] in ("tan", "coral") else P["grey"])      # entretoises et croix
    tip = tips(cfg)[variant]
    z_top = max(v[2] for v in tip.values())
    kind = cfg["kind"]

    if kind == "wood":                                              # poteau en bois sur un pied métallique
        cyl((0, 0, 0.25), 0.2, 0.5, dark, verts=14)
        rod((0, 0, 0.4), (0, 0, z_top - 0.2), 0.1, wood, 12)
    elif kind == "tower":                                           # pylône : quatre montants qui se rapprochent
        b, t = cfg["base"], cfg["top"]
        for sx in (-1, 1):
            for sy in (-1, 1):
                rod((sx * b, sy * b, 0), (sx * t, sy * t, z_top - 0.4), 0.065, main)
        for f in (0.28, 0.55, 0.8):                                 # entretoises horizontales
            z, r = f * (z_top - 0.4), b + (t - b) * f
            for sx, sy, ex, ey in ((-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)):
                rod((sx * r, sy * r, z), (ex * r, ey * r, z), 0.045, accent)
        for sx in (-1, 1):                                          # croix sur la face avant
            rod((sx * b, -b, 0.1), (-sx * (b + (t - b) * 0.28), -(b + (t - b) * 0.28), 0.28 * (z_top - 0.4)), 0.04, accent)
    else:                                                           # sous-station : transformateur et treillis au-dessus
        box((0, 0, 0.9), (1.5, 1.2, 1.8), main, 0.08)               # caisse
        box((0, -0.62, 1.0), (1.2, 0.04, 1.2), dark, 0.02)          # panneau avant
        for k in range(3):                                          # persiennes de ventilation
            box((-0.25, -0.67, 0.62 + 0.28 * k), (0.62, 0.05, 0.12), steel, 0.02)
        box((0.4, -0.67, 1.0), (0.3, 0.05, 0.8), steel, 0.02)       # coffret
        cyl((0, -0.12, 1.88), 0.1, 1.4, mat("copper", P["orange"]), verts=14, rot=(0, 90, 0))   # barre de cuivre
        for sx in (-1, 1):
            for sy in (-1, 1):
                rod((sx * 0.5, sy * 0.4, 1.8), (sx * 0.12, sy * 0.12, z_top - 0.3), 0.045, steel)
    # bras et isolateurs : un bras horizontal de l'axe jusqu'à chaque point d'attache, puis le plot jusqu'au bout
    for k, (x, y, z) in tip.items():
        arm_z = z - 0.45
        rod((0, 0, arm_z), (x, y, arm_z), 0.055, accent if kind == "tower" else main)
        rod((x, y, arm_z), (x, y, z - 0.08), 0.045, steel)
        cyl((x, y, z - 0.12), 0.07, 0.24, white, verts=10)


# --- rendu -----------------------------------------------------------------------------------------------
def camera_for(cfg):
    """Échelle et décalages de caméra pour que l'origine (pied du pylône) tombe au centre de l'entité."""
    w, hh = cfg["cell"]
    big = max(w, hh)
    sx, sy = cfg["shift"]
    return w / PX_PER_TILE if w >= hh else hh / PX_PER_TILE, sx / big, -sy / big


def over(top, bottom):
    ta, ba = top[:, :, 3:4] / 255.0, bottom[:, :, 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


def render_variant(name, variant, out):
    cfg = POLES[name]
    scale, shift_x, shift_y = camera_for(cfg)
    path = os.path.join(out, "_pole.png")
    build_pole(name, variant)
    render_scene(path, size=cfg["cell"], scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_x=shift_x, shift_y=shift_y,
                 outline_units=OUTLINE)
    sprite = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    # ombre : grand canevas centré sur l'entité, découpé à la fenêtre de l'ombre de l'original
    build_pole(name, variant)
    flatten_to_shadow(SHADOW[0], SHADOW[1])
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, pitch_deg=S.PITCH_BUILDING_DEG, outline=False)
    big = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    (sw, sh), (ox, oy) = cfg["shadow"]
    x0, y0 = int(round(CANVAS / 2 + ox - sw / 2)), int(round(CANVAS / 2 + oy - sh / 2))
    shadow = big[y0:y0 + sh, x0:x0 + sw].copy()
    shadow[:, :, :3] = 0
    return sprite, shadow


def build_icon(name, out):
    return mip_strip(render_icon(lambda: build_pole(name, 0), os.path.join(out, "_icon.png"), 64, 60, pitch_deg=S.PITCH_BUILDING_DEG), 64)


def build_poles(name, out):
    sprites, shadows = zip(*[render_variant(name, v, out) for v in range(4)])
    cv2.imwrite(os.path.join(out, f"{name}.png"), np.hstack(sprites))
    cv2.imwrite(os.path.join(out, f"{name}-shadow.png"), np.hstack(shadows))
    cv2.imwrite(os.path.join(out, f"{name}-icon.png"), build_icon(name, out))


# --- câbles --------------------------------------------------------------------------------------------------
WIRES = {                                # nom du fichier -> (couleur du trait BGR, couleur du contour BGR, épaisseur, alpha)
    "copper-wire": ((61, 130, 214), (28, 40, 62), 3, 255),
    "red-wire": ((60, 70, 200), (28, 28, 70), 3, 255),
    "green-wire": ((74, 160, 84), (28, 56, 30), 3, 255),
    "wire-shadow": ((0, 0, 0), (0, 0, 0), 4, 255),
    "wire-highlight": ((235, 235, 235), (235, 235, 235), 3, 255),
}


def build_wires(out, core_dir):
    """Redessine chaque câble le long du même arc que l'original, plus épais et contourné."""
    for name, (color, outline, width, _) in WIRES.items():
        src = cv2.imread(os.path.join(core_dir, f"{name}.png"), cv2.IMREAD_UNCHANGED)
        h, w = src.shape[:2]
        alpha = src[:, :, 3].astype(np.float32)
        xs, ys = [], []
        for x in range(w):
            col = alpha[:, x]
            if col.sum() > 0:
                xs.append(x)
                ys.append((col * np.arange(h)).sum() / col.sum())
        poly = np.array(list(zip(xs, ys)), np.float32)
        ss = 4                                              # dessin 4x puis réduction : trait lisse
        canvas = np.zeros((h * ss, w * ss, 4), np.uint8)
        big = (poly * ss).astype(np.int32).reshape(-1, 1, 2)
        if name != "wire-shadow":
            cv2.polylines(canvas, [big], False, (*outline, 255), (width + 2) * ss, cv2.LINE_AA)
        cv2.polylines(canvas, [big], False, (*color, 255), width * ss, cv2.LINE_AA)
        a = canvas[:, :, 3:4].astype(np.float32) / 255.0
        pre = np.dstack([canvas[:, :, :3] * a, canvas[:, :, 3:4]]).astype(np.float32)
        small = cv2.resize(pre, (w, h), interpolation=cv2.INTER_AREA)
        al = np.clip(small[:, :, 3:4] / 255.0, 1e-6, 1)
        res = np.dstack([np.clip(small[:, :, :3] / al, 0, 255), small[:, :, 3:4]]).astype(np.uint8)
        cv2.imwrite(os.path.join(out, f"{name}.png"), res)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "pole_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (POLES if which == "tous" else [which]):
        if name in POLES:
            build_poles(name, out)
            print("OK", name, flush=True)
    if which in ("tous", "wires"):
        build_wires(out, "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data/core/graphics")
        print("OK câbles")
