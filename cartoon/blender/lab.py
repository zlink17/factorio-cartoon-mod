"""Laboratoire (lab) : planche animée, ombre, plaque d'intégration, icône.

Usage : python cartoon/blender/lab.py <dossier_sortie> [--apercu]

Écrit, aux chemins de l'original (base/entity/lab/ et base/icons/) :
  lab.png              33 images (11 par ligne) : la lueur bleue des vitres vacille comme dans l'original ; l'image
                       0 (vitres éteintes) sert aussi au laboratoire à l'arrêt
  lab-shadow.png       ombre portée, noire unie
  lab-integration.png  terre tassée autour du socle : forme de l'original en aplat semi-transparent
  lab.png (icône)      64 px + mipmaps
Laissés d'origine : le halo (lab-light, dessiné en lumière) et les restes (lot 3.9).

Le laboratoire (3 x 3 cases) : socle octogonal sombre portant de petites trappes colorées, coiffé d'un dôme
géodésique vitré ; les montants cuivre sont peints sur le verre (nœud « Wireframe » : pas de contour par montant).
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, cyl, load, mat, render_scene, render_shadow, reset, save_icon, sheet, target

P = S.PALETTE
NAME = "lab"
PX_PER_TILE = 64
CANVAS = 384
N_FRAMES, COLUMNS = 33, 11
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.022
SPRITE = ((194, 174), (0.0, 3.0))           # cadres de l'original (taille, décalage en px = shift x 64)
SHADOW = ((243, 136), (26.5, 22.0))         # le fichier fait 243 px de large (le prototype en déclare 242)
# intensité de la lueur bleue par image, mesurée sur l'original (bleu moins rouge des vitres, ramené à 0..1)
GLOW = [-12, 42, 28, 25, -6, 20, 29, -7, 42, 14, -3, 35, 42, 23, 16, 24, -8, 20, 33, 18, 5, 20, 12, 20, 27, 37, 50,
        55, 34, 20, 26, 17, 3]

GLASS_TINTS = (0.8, 1.0, 1.25)

DIMS = dict(R=1.32, zs=0.85, hb=0.3, rb=1.36, down=0.08)     # ajustées sur la silhouette de l'original, socle
                                                              # resserré sous le dôme (sinon anneau sombre)


def glow(i):
    return float(np.clip((GLOW[i] + 12) / 67, 0, 1))


def mat_dome(name, glass, frame, size=0.06):
    """Verre du dôme (trois tons comme lib.mat) avec les montants peints le long des arêtes des triangles."""
    m = mat(name, (1, 1, 1))
    nt = m.node_tree
    n = nt.nodes
    mix = next(x for x in n if x.bl_idname == "ShaderNodeMix")
    wire = n.new("ShaderNodeWireframe")
    wire.use_pixel_size = False
    wire.inputs[0].default_value = size
    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"
    nt.links.new(wire.outputs[0], col.inputs[0])
    col.inputs[6].default_value = (*glass, 1)
    col.inputs[7].default_value = (*frame, 1)
    nt.links.new(col.outputs[2], mix.inputs[6])
    return m


def build(k=0.0, d=None):
    """Scène du laboratoire, lueur `k` (0 : vitres éteintes, 1 : bleu vif)."""
    import bpy, bmesh
    reset()
    d = d or DIMS
    base = mat("base", P["lab_base"])
    glass = tuple(a + (b - a) * k for a, b in zip(P["lab_glass"], P["lab_glow"]))
    hb, rb = d["hb"], d["rb"]
    cyl((0, 0, hb / 2), rb, hb, base, verts=16)                                  # socle
    for ang, c in ((-120, "red"), (-90, "steel_blue"), (-60, "ore_uranium"), (150, "yellow"), (30, "yellow")):
        a = math.radians(ang)                                                   # trappes colorées sur le socle
        r = rb + 0.04
        box((r * math.cos(a), r * math.sin(a), hb * 0.5), (0.34, 0.2, hb * 0.8), mat("door" + c, P[c]), rot_z=ang + 90)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(0, 0, 0))
    dome = bpy.context.object
    bm = bmesh.new()
    bm.from_mesh(dome.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.05], context="VERTS")
    bm.to_mesh(dome.data)
    bm.free()
    dome.scale = (d["R"], d["R"], d["zs"])
    dome.location = (0, 0, hb)
    # panneaux de verre en trois teintes tirées au hasard (graine fixe) : on lit les facettes du dôme
    for j, t in enumerate(GLASS_TINTS):
        dome.data.materials.append(mat_dome(f"dome{j}", tuple(c * t for c in glass), P["lab_frame"]))
    rng = np.random.default_rng(7)
    for f in dome.data.polygons:
        f.material_index = int(rng.integers(len(GLASS_TINTS)))
    bpy.context.view_layer.update()


def camera_shift(d=None):
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


def write(out, preview=False):
    path = os.path.join(out, "_lab.png")
    frames = []
    for i in range(1 if preview else N_FRAMES):
        build(glow(i))
        render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
        frames.append(crop_centered(load(path), *SPRITE))
    if preview:
        frames = frames * N_FRAMES
    cv2.imwrite(target(out, "base/entity/lab/lab.png"), sheet(frames, COLUMNS))
    sh = render_shadow(build, path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR, shift_y=camera_shift())
    cv2.imwrite(target(out, "base/entity/lab/lab-shadow.png"), crop_centered(sh, *SHADOW))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "terrain"))
    from decoratives import FACTORIO_DATA, render_decal
    orig = cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity/lab/lab-integration.png"), cv2.IMREAD_UNCHANGED)
    cv2.imwrite(target(out, "base/entity/lab/lab-integration.png"), render_decal(orig))
    save_icon(out, NAME, lambda: build(0.8))


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "lab_out"
    os.makedirs(out, exist_ok=True)
    write(out, preview)
    print("OK laboratoire", flush=True)
