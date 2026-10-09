"""Démo : rend plusieurs objets en style toon et assemble une planche contact.

Usage : python tools/blender/sprites_demo.py <dossier_sortie>
"""
import math, os, sys
import bpy
import cv2
import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_out"
SIZE = 256
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def box(loc, scale, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        bpy.ops.object.modifier_add(type="BEVEL")
        o.modifiers["Bevel"].width = bevel
        o.modifiers["Bevel"].segments = 3
    o.data.materials.append(m)
    return o


def cyl(loc, r, d, m, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=rot)
    o = bpy.context.object
    o.data.materials.append(m)
    return o


def blob(loc, r, m):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=loc)
    o = bpy.context.object
    o.data.materials.append(m)
    return o


ORANGE, YELLOW = (0.95, 0.55, 0.15), (1.0, 0.8, 0.35)
BLUE, WHITE = (0.35, 0.45, 0.8), (0.95, 0.95, 0.95)
GREY, DARK = (0.55, 0.6, 0.65), (0.25, 0.27, 0.32)
BROWN, RED = (0.65, 0.4, 0.2), (0.9, 0.25, 0.2)


def assembler():
    box((0, 0, 0.15), (3, 3, 0.3), mat("b", BLUE))
    box((0, 0, 0.9), (2.6, 2.6, 1.2), mat("o", ORANGE), 0.15)
    box((0, 0, 1.52), (2.0, 2.0, 0.08), mat("y", YELLOW))
    cyl((0, 0, 1.65), 0.7, 0.15, mat("w", WHITE), 8)
    cyl((0, 0, 1.66), 0.25, 0.2, mat("y2", YELLOW))


def furnace():
    box((0, 0, 0.9), (2.4, 2.4, 1.8), mat("g", GREY), 0.15)
    box((0, -1.22, 0.7), (1.2, 0.1, 0.9), mat("d", DARK))
    box((0, -1.25, 0.55), (0.9, 0.05, 0.4), mat("r", RED))
    cyl((0.6, 0.6, 2.2), 0.3, 1.0, mat("br", BROWN))


def chest():
    box((0, 0, 0.5), (2.0, 1.4, 1.0), mat("br", BROWN), 0.1)
    box((0, 0, 1.15), (2.1, 1.5, 0.3), mat("y", YELLOW), 0.08)
    box((0, -0.75, 0.85), (0.3, 0.08, 0.35), mat("d", DARK))


def belt():
    box((0, 0, 0.1), (3.0, 1.2, 0.2), mat("g", DARK))
    for i in range(-3, 4):
        box((i * 0.4, 0, 0.22), (0.18, 0.9, 0.05), mat(f"y{i}", YELLOW))
    box((0, 0.7, 0.2), (3.0, 0.1, 0.3), mat("o", ORANGE))
    box((0, -0.7, 0.2), (3.0, 0.1, 0.3), mat("o2", ORANGE))


def pole():
    cyl((0, 0, 1.5), 0.12, 3.0, mat("br", BROWN))
    box((0, 0, 2.7), (1.4, 0.12, 0.12), mat("br2", BROWN))
    for x in (-0.6, 0.6):
        blob((x, 0, 2.85), 0.1, mat("w", WHITE))


def ore():
    m = mat("o", (0.45, 0.55, 0.75))
    for loc, r in [((0, 0, 0.4), 0.7), ((0.7, 0.2, 0.3), 0.5), ((-0.6, 0.3, 0.25), 0.45), ((0.1, -0.7, 0.3), 0.5)]:
        blob(loc, r, m)


def render(builder, name, scale):
    reset()
    builder()
    bpy.ops.object.camera_add(location=(6, -6, 6.2))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.rotation_euler = (math.radians(58), 0, math.radians(45))
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 4
    sc.cycles.use_denoising = False
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 2.2
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    ls = vl.freestyle_settings.linesets.new("outline")
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    ls.linestyle.color = (0.05, 0.03, 0.03)
    path = os.path.join(OUT, f"{name}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


ITEMS = [("assembleur", assembler, 5.2), ("four", furnace, 5.2), ("coffre", chest, 4.6),
         ("convoyeur", belt, 5.2), ("poteau", pole, 6.0), ("minerai", ore, 3.8)]
paths = [render(b, n, s) for n, b, s in ITEMS]

# planche contact sur fond gris (comme en jeu)
tiles = []
for p in paths:
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    a = im[:, :, 3:4] / 255.0
    bg = np.full(im.shape[:2] + (3,), (90, 90, 90), np.float32)
    tiles.append((im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8))
sheet = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
cv2.imwrite(os.path.join(OUT, "planche.png"), sheet)
print("OK", os.path.join(OUT, "planche.png"))
