"""Essai du rendu cel-shading sur des formes simples : boîte biseautée, cylindre, sphère, tore.

Usage : python celshading/blender/essai.py <dossier_sortie>
Écrit <sortie>/essai.png (rendu à la taille du jeu, 64 px par case) et essai-x4.png (agrandi, pixels nets).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import cv2
from lib import S, reset, mat, box, cyl, render_scene

P = S.PALETTE


def build():
    reset()
    box((-1.6, 0, 0.45), (1.0, 1.0, 0.9), mat("boite", P["grey"]), bevel=0.08)
    cyl((0, 0, 0.6), 0.5, 1.2, mat("cylindre", P["brown"]), verts=48)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(1.5, 0, 0.5), segments=48, ring_count=24)
    o = bpy.context.object
    o.data.materials.append(mat("sphere", P["steel_blue"]))
    bpy.ops.object.shade_smooth()
    # une plaque devant la boîte, pour voir une ombre portée sur un objet
    box((-1.6, -0.9, 0.05), (1.2, 0.6, 0.1), mat("socle", P["yellow"]))
    bpy.ops.mesh.primitive_torus_add(location=(0.1, -1.0, 0.15), major_radius=0.35, minor_radius=0.13)
    o = bpy.context.object
    o.data.materials.append(mat("tore", P["olive"]))
    bpy.ops.object.shade_smooth()


def main(out):
    os.makedirs(out, exist_ok=True)
    build()
    path = render_scene(os.path.join(out, "essai.png"), size=(320, 192), scale=5.0)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    cv2.imwrite(os.path.join(out, "essai-x4.png"), cv2.resize(im, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    print("OK", path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sortie")
