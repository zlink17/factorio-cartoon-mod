"""Bras robotisés (burner-inserter, inserter, long-handed-inserter, fast-inserter, bulk-inserter).

Usage : python cartoon/blender/inserter.py <dossier_sortie> [bras|tous]

Pour chaque bras, écrit les fichiers du prototype d'origine, au même format :
  <nom>-platform.png      4 plateformes de 105 x 79 côte à côte (tripode + tambour, vue à 30°, ombre comprise)
  <nom>-hand-base.png     le bras, 32 x 136, vu de dessus (128 px par case)
  <nom>-hand-open.png     la pince ouverte, 72 x 164, vue de dessus
  <nom>-hand-closed.png   la pince fermée, 72 x 164
  <nom>-icon.png          icône 64 px + mipmaps (120 x 64)
et, une seule fois (les bras partagent les ombres de la main du bras à charbon) :
  burner-inserter-hand-{base,open,closed}-shadow.png
sauf le bras en vrac, qui a ses propres ombres de pince : bulk-inserter-hand-{open,closed}-shadow.png

Les pièces de la main sont dessinées vues de dessus parce que le moteur les fait tourner autour du
pivot : un dessus pur reste juste quel que soit l'angle. La plateforme, elle, est fixe et suit la
projection des bâtiments.
"""
import math, os, sys
import bpy
import cv2
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, cyl, flatten_to_shadow, mat, mip_strip, render_icon, render_scene, reset

P = S.PALETTE

INSERTERS = {
    "burner-inserter":      dict(color="brown"),
    "inserter":             dict(color="yellow"),
    "long-handed-inserter": dict(color="red"),
    "fast-inserter":        dict(color="steel_blue"),
    # le bras en vrac a une pince à part : deux tubes, deux bras articulés, deux patins ; ombres de pince propres
    "bulk-inserter":        dict(color="green", hand="bulk", open_size=(130, 164), closed_size=(100, 164)),
}

HAND_PX = 128                  # px par case des pièces de la main (scale 0.25 dans le prototype)
PLATFORM_PX = 64               # px par case de la plateforme (scale 0.5)
PLATFORM_CELL = (105, 79)
PLATFORM_DRUM = (51, 31)       # centre du tambour dans une cellule de l'original (px)
HAND_BASE_SIZE = (32, 136)
HAND_SIZE = (72, 164)
SHADOW_ALPHA = 130             # opacité maximale des ombres de la main, comme l'original
PLATFORM_SHADOW = (0.5, 0.02, 0.4)   # décalage au sol par unité de hauteur (x, y) et opacité
ICON = 64
HAND_OUTLINE = 0.011           # contour plus fin que le style de base : ces pièces font 5 px de large en jeu
PLATFORM_OUTLINE = 0.016


def rod(p0, p1, r, m, verts=12):
    """Cylindre entre deux points."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)
    return o


def materials(color):
    return dict(main=mat("main", P[color]), dark=mat("dark", P["dark"]), light=mat("light", P["white"]),
                steel=mat("steel", P["grey"]))


# --- plateforme : tripode et tambour -------------------------------------------------------------
def build_platform(color, direction):
    """direction 0..3 : le tripode tourne d'un quart de tour entre les quatre cellules."""
    reset()
    m = materials(color)
    for k in range(3):
        a = math.radians(90 + 120 * k + 90 * direction)
        c, s = math.cos(a), math.sin(a)
        rod((0.17 * c, 0.17 * s, 0.36), (0.5 * c, 0.5 * s, 0.07), 0.085, m["main"])
        box((0.55 * c, 0.55 * s, 0.03), (0.22, 0.22, 0.06), m["dark"], 0.02, rot_z=math.degrees(a))
    cyl((0, 0, 0.38), 0.27, 0.2, m["main"], verts=24)               # tambour
    cyl((0, 0, 0.49), 0.2, 0.03, m["dark"], verts=24)               # creux
    cyl((0, 0, 0.51), 0.12, 0.04, m["steel"], verts=16)             # engrenage
    cyl((0, 0, 0.54), 0.05, 0.04, m["light"], verts=12)             # moyeu


def render_platform_cell(color, direction, out):
    """Une cellule de 105 x 79 : l'ombre à plat (semi-transparente) sous la plateforme."""
    path = os.path.join(out, "_plat.png")
    scale = PLATFORM_CELL[0] / PLATFORM_PX
    # le dessus du tambour (z = 0.5) est à 0,5 * sin(30°) * 64 = 16 px au-dessus de son pied : on cale la caméra
    # pour qu'il tombe en PLATFORM_DRUM (la caméra décale de shift * 105 px vers le bas)
    shift = (PLATFORM_DRUM[1] + 0.5 * math.sin(math.radians(S.PITCH_BUILDING_DEG)) * PLATFORM_PX
             - PLATFORM_CELL[1] / 2) / max(PLATFORM_CELL)
    build_platform(color, direction)
    render_scene(path, size=PLATFORM_CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift,
                 outline_units=PLATFORM_OUTLINE)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    sprite = im
    build_platform(color, direction)
    flatten_to_shadow(PLATFORM_SHADOW[0], PLATFORM_SHADOW[1])
    render_scene(path, size=PLATFORM_CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift, outline=False)
    shadow = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    shadow[:, :, :3] = 0
    shadow[:, :, 3] = (shadow[:, :, 3] * PLATFORM_SHADOW[2]).astype(np.uint8)
    return over(sprite, shadow)


def over(top, bottom):
    """Composition « top sur bottom » (RGBA, alpha non prémultiplié)."""
    ta, ba = top[:, :, 3:4] / 255.0, bottom[:, :, 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


# --- la main : bras et pince, vus de dessus ----------------------------------------------------
def build_hand_base(color):
    reset()
    m = materials(color)
    box((0, -0.05, 0.0), (0.17, 1.0, 0.1), m["main"], 0.04)                     # tige
    cyl((0, 0.43, 0.06), 0.105, 0.14, m["dark"], verts=20)                      # pivot
    cyl((0, 0.43, 0.14), 0.05, 0.06, m["light"], verts=12)
    box((0, -0.5, 0.06), (0.08, 0.06, 0.1), m["dark"], 0.01)                    # pointe


def build_bulk_hand(color, opened):
    """Deux tubes parallèles, puis deux bras articulés (acier clair) qui écartent ou resserrent deux patins."""
    reset()
    m = materials(color)
    for sx in (-1, 1):
        box((sx * 0.1, -0.25, 0.0), (0.15, 0.8, 0.1), m["main"], 0.04)            # tube
        cyl((sx * 0.1, 0.17, 0.08), 0.07, 0.1, m["dark"], verts=14)               # articulation
        pad = (sx * (0.43 if opened else 0.31), 0.5)
        elbow = (sx * (0.3 if opened else 0.17), 0.3)
        rod((sx * 0.1, 0.17, 0.1), (*elbow, 0.1), 0.045, m["light"])
        rod((*elbow, 0.1), (*pad, 0.1), 0.045, m["light"])
        cyl((*elbow, 0.1), 0.055, 0.1, m["dark"], verts=12)
        box((*pad, 0.09), (0.14, 0.2, 0.1), m["light"], 0.03)                      # patin


def build_hand(color, opened):
    reset()
    m = materials(color)
    gap = 0.2 if opened else 0.11
    box((0, -0.1, 0.0), (0.3, 1.05, 0.1), m["main"], 0.04)                      # montant
    box((0, -0.1, 0.07), (0.1, 0.8, 0.1), m["dark"], 0.02)                      # fente
    box((0, 0.4, 0.07), (0.5 if opened else 0.36, 0.1, 0.12), m["dark"], 0.03)  # traverse
    for sx in (-1, 1):                                                         # deux doigts
        box((sx * gap + sx * 0.04, 0.52, 0.09), (0.07, 0.2, 0.1), m["light"], 0.02)


def render_part(build, size, px_per_tile, path):
    build()
    render_scene(path, size=size, scale=max(size) / px_per_tile, pitch_deg=S.PITCH_TOPDOWN_DEG,
                 outline_units=HAND_OUTLINE)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    return im


def silhouette_shadow(im, rows=None):
    sh = np.zeros_like(im)
    a = (im[:, :, 3] > 10).astype(np.uint8) * SHADOW_ALPHA
    sh[:, :, 3] = cv2.GaussianBlur(a, (3, 3), 0)
    return sh if rows is None else sh[:rows]


# --- icône : le bras complet, vu comme les machines -------------------------------------------------
def build_icon_model(color):
    reset()
    m = materials(color)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        c, s = math.cos(a), math.sin(a)
        rod((0.17 * c, 0.17 * s, 0.36), (0.5 * c, 0.5 * s, 0.07), 0.075, m["main"])
        box((0.55 * c, 0.55 * s, 0.03), (0.2, 0.2, 0.06), m["dark"], 0.02, rot_z=math.degrees(a))
    cyl((0, 0, 0.38), 0.27, 0.2, m["main"], verts=24)
    cyl((0, 0, 0.49), 0.2, 0.03, m["dark"], verts=24)
    cyl((0, 0, 0.51), 0.12, 0.04, m["steel"], verts=16)
    # bras levé vers le haut-droite, pince au bout
    tip = (0.55, 0.62, 0.7)
    rod((0, 0, 0.55), tip, 0.075, m["main"])
    box((0.55, 0.62, 0.7), (0.34, 0.1, 0.1), m["dark"], 0.02, rot_z=-35)
    for sx in (-1, 1):
        box((0.55 + sx * 0.15 * math.cos(math.radians(-35)) + 0.06, 0.62 + sx * 0.15 * math.sin(math.radians(-35)) + 0.06,
             0.78), (0.07, 0.07, 0.2), m["light"], 0.02)


# --- assemblage ---------------------------------------------------------------------------------
def build_inserter(name, out):
    color = INSERTERS[name]["color"]
    cells = [render_platform_cell(color, d, out) for d in range(4)]
    cv2.imwrite(os.path.join(out, f"{name}-platform.png"), np.hstack(cells))
    cfg = INSERTERS[name]
    hand = build_bulk_hand if cfg.get("hand") == "bulk" else build_hand
    tmp = os.path.join(out, "_p.png")
    parts = {
        "hand-base": render_part(lambda: build_hand_base(color), HAND_BASE_SIZE, HAND_PX, tmp),
        "hand-open": render_part(lambda: hand(color, True), cfg.get("open_size", HAND_SIZE), HAND_PX, tmp),
        "hand-closed": render_part(lambda: hand(color, False), cfg.get("closed_size", HAND_SIZE), HAND_PX, tmp),
    }
    for part, im in parts.items():
        cv2.imwrite(os.path.join(out, f"{name}-{part}.png"), im)
    icon = render_icon(lambda: build_icon_model(color), os.path.join(out, "_icon.png"), ICON, 58)
    cv2.imwrite(os.path.join(out, f"{name}-icon.png"), mip_strip(icon, ICON))
    return parts


def build_shadows(parts, out):
    """Ombres de la main, communes aux quatre bras (fichiers du bras à charbon)."""
    base = silhouette_shadow(parts["hand-base"], rows=132)
    cv2.imwrite(os.path.join(out, "burner-inserter-hand-base-shadow.png"), base)
    for part in ("open", "closed"):
        cv2.imwrite(os.path.join(out, f"burner-inserter-hand-{part}-shadow.png"),
                    silhouette_shadow(parts[f"hand-{part}"]))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "inserter_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    first, saved = None, {}
    for name in (INSERTERS if which == "tous" else [which]):
        parts = build_inserter(name, out)
        saved[name] = parts
        first = first or parts
        print("OK", name, flush=True)
    build_shadows(first, out)
    print("OK ombres")
    if "bulk-inserter" in saved:
        for part in ("open", "closed"):
            cv2.imwrite(os.path.join(out, f"bulk-inserter-hand-{part}-shadow.png"),
                        silhouette_shadow(saved["bulk-inserter"][f"hand-{part}"]))
