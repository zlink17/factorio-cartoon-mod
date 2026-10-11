"""Petite lampe (small-lamp) : sprite, ombre, icône.

Usage : python cartoon/blender/lamp.py <dossier_sortie>

Écrit, aux chemins de l'original (base/entity/small-lamp/ et base/icons/) :
  lamp.png, lamp-shadow.png      la lampe éteinte et son ombre (noire unie)
  small-lamp.png (icône)         64 px + mipmaps
Laissés d'origine : la lampe allumée (lamp-light, dessinée en lumière par-dessus) et les restes (lot 3.9).

La lampe (1 case) : socle carré en fer sombre à pattes devant, plateau à rivets cuivre aux coins,
globe de verre dépoli arrondi au centre (le jeu l'éclaire la nuit), petite tige cuivre à l'arrière droit.
"""
import os, sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, cyl, load, mat, render_scene, render_shadow, reset, save_icon, target

P = S.PALETTE
NAME = "small-lamp"
PX_PER_TILE = 64
CANVAS = 192
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.02
SPRITE = ((83, 70), (0.5, 6.0))            # cadre de l'original (taille, décalage en px = shift x 64)
SHADOW = ((76, 47), (8.0, 9.5))

DIMS = dict(w=0.78, h=0.19, gw=0.5, gh=0.22, down=0.11)       # ajustées sur la silhouette de l'original


def build(d=None):
    reset()
    d = d or DIMS
    body = mat("body", P["lamp_body"])
    plate = mat("plate", P["lamp_plate"])
    glass = mat("glass", P["lamp_glass"])
    copper = mat("copper", P["brown"])
    w, h = d["w"], d["h"]
    box((0, 0, h / 2), (w, w, h), body, bevel=0.02)                              # socle
    for x in (-0.16, 0.16):                                                      # pattes devant
        box((x, -w / 2 - 0.025, 0.08), (0.07, 0.05, 0.16), body)
    box((0, 0, h + 0.025), (w * 0.92, w * 0.92, 0.05), plate, bevel=0.01)       # plateau
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl((sx * w * 0.38, sy * w * 0.38, h + 0.055), 0.025, 0.02, copper, verts=8)
    import bpy
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(0, 0.01, h + 0.05))
    g = bpy.context.object                                                       # globe : demi-ellipsoïde
    g.scale = (d["gw"] / 2, d["gw"] * 0.45, d["gh"])
    g.data.materials.append(glass)
    cyl((w * 0.4, w * 0.4, h + 0.15), 0.025, 0.25, copper, verts=8)             # tige


def camera_shift(d=None):
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


def write(out):
    path = os.path.join(out, "_lamp.png")
    build()
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
    cv2.imwrite(target(out, "base/entity/small-lamp/lamp.png"), crop_centered(load(path), *SPRITE))
    sh = render_shadow(build, path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR, shift_y=camera_shift())
    cv2.imwrite(target(out, "base/entity/small-lamp/lamp-shadow.png"), crop_centered(sh, *SHADOW))
    save_icon(out, NAME, build, fill=58)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "lamp_out"
    os.makedirs(out, exist_ok=True)
    write(out)
    print("OK lampe", flush=True)
