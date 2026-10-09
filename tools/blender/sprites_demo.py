"""Démo : rend plusieurs objets en style toon (projection façon Factorio).

Projection : le sol n'est pas raccourci (une case reste carrée à l'écran), les
bâtiments sont alignés sur la grille (aucune rotation), vus de face avec le dessus
visible. La hauteur est décalée vers le haut de l'écran (tan(PITCH) par unité).
Les convoyeurs sont vus directement du dessus (PITCH = 0).

Usage : python tools/blender/sprites_demo.py <dossier_sortie>
"""
import math, os, sys
import bpy
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_out"
SIZE = 256
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb):
    """Aplat de couleur à trois tons : dessus clair, face avant moyenne, côtés sombres."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    n = nt.nodes
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    top = n.new("ShaderNodeMath"); top.operation = "GREATER_THAN"; top.inputs[1].default_value = 0.5
    nt.links.new(sep.outputs["Z"], top.inputs[0])
    negy = n.new("ShaderNodeMath"); negy.operation = "MULTIPLY"; negy.inputs[1].default_value = -1.0
    nt.links.new(sep.outputs["Y"], negy.inputs[0])
    front = n.new("ShaderNodeMath"); front.operation = "GREATER_THAN"; front.inputs[1].default_value = 0.5
    nt.links.new(negy.outputs[0], front.inputs[0])
    # ombre = 0.68 + 0.42*top + 0.2*front
    a = n.new("ShaderNodeMath"); a.operation = "MULTIPLY_ADD"; a.inputs[1].default_value = S.SHADE_TOP - S.SHADE_SIDE; a.inputs[2].default_value = S.SHADE_SIDE
    nt.links.new(top.outputs[0], a.inputs[0])
    b = n.new("ShaderNodeMath"); b.operation = "MULTIPLY_ADD"; b.inputs[1].default_value = S.SHADE_FRONT - S.SHADE_SIDE
    nt.links.new(front.outputs[0], b.inputs[0]); nt.links.new(a.outputs[0], b.inputs[2])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (*rgb, 1)
    nt.links.new(b.outputs[0], mix.inputs[7])
    # le facteur est scalaire : on le passe par un CombineXYZ -> couleur grise
    comb = n.new("ShaderNodeCombineXYZ")
    for i in range(3):
        nt.links.new(b.outputs[0], comb.inputs[i])
    nt.links.new(comb.outputs[0], mix.inputs[7])
    em = n.new("ShaderNodeEmission")
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    out = n.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def box(loc, scale, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        bpy.ops.object.modifier_add(type="BEVEL")
        o.modifiers["Bevel"].width = bevel
        o.modifiers["Bevel"].segments = 2
    o.data.materials.append(m)
    return o


def cyl(loc, r, d, m, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc)
    o = bpy.context.object
    o.data.materials.append(m)
    return o


def blob(loc, r, m):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=loc)
    o = bpy.context.object
    o.data.materials.append(m)
    return o


ORANGE, YELLOW = S.PALETTE["orange"], S.PALETTE["yellow"]
BLUE, WHITE = S.PALETTE["blue"], S.PALETTE["white"]
GREY, DARK = S.PALETTE["grey"], S.PALETTE["dark"]
BROWN, RED = S.PALETTE["brown"], S.PALETTE["red"]
ORE = S.PALETTE["ore_iron"]


def assembler():
    box((0, 0, 0.15), (3, 3, 0.3), mat("b", BLUE))
    box((0, 0, 0.9), (2.6, 2.6, 1.2), mat("o", ORANGE), 0.15)
    box((0, 0, 1.52), (2.0, 2.0, 0.08), mat("y", YELLOW))
    cyl((0, 0, 1.65), 0.7, 0.15, mat("w", WHITE), 8)
    cyl((0, 0, 1.66), 0.25, 0.2, mat("y2", YELLOW))


def furnace():
    box((0, 0, 0.9), (2.4, 2.4, 1.8), mat("g", GREY), 0.15)
    box((0, -1.22, 0.7), (1.2, 0.1, 0.9), mat("d", DARK))
    box((0, -1.26, 0.55), (0.9, 0.05, 0.4), mat("r", RED))
    cyl((0.6, 0.6, 2.2), 0.3, 1.0, mat("br", BROWN))


def chest():
    box((0, 0, 0.5), (2.0, 1.4, 1.0), mat("br", BROWN), 0.1)
    box((0, 0, 1.15), (2.1, 1.5, 0.3), mat("y", YELLOW), 0.08)
    box((0, -0.76, 0.85), (0.3, 0.08, 0.35), mat("d", DARK))


def belt():
    # vu de dessus, horizontal (axe X), non incliné
    box((0, 0, 0.05), (3.0, 1.0, 0.1), mat("g", DARK))
    for i in range(-3, 4):
        box((i * 0.4, 0, 0.12), (0.16, 0.7, 0.04), mat(f"y{i}", YELLOW))
    box((0, 0.5, 0.08), (3.0, 0.1, 0.16), mat("o", ORANGE))
    box((0, -0.5, 0.08), (3.0, 0.1, 0.16), mat("o2", ORANGE))


def pole():
    cyl((0, 0, 1.5), 0.12, 3.0, mat("br", BROWN))
    box((0, 0, 2.7), (1.4, 0.12, 0.12), mat("br2", BROWN))
    for x in (-0.6, 0.6):
        blob((x, 0, 2.85), 0.1, mat("w", WHITE))


def ore():
    m = mat("o", ORE)
    for loc, r in [((0, 0, 0.4), 0.7), ((0.7, 0.2, 0.3), 0.5), ((-0.6, 0.3, 0.25), 0.45), ((0.1, -0.7, 0.3), 0.5)]:
        blob(loc, r, m)


def render(builder, name, scale, pitch_deg, cy=0.0):
    reset()
    builder()
    p = math.radians(pitch_deg)
    # étire le sol en Y pour que, une fois raccourci par la caméra, il reste carré
    root = bpy.data.objects.new("root", None)
    bpy.context.scene.collection.objects.link(root)
    root.scale = (1, 1 / math.cos(p), 1)
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH":
            o.parent = root
    d = 20
    bpy.ops.object.camera_add(location=(0, -d * math.sin(p), d * math.cos(p) + cy))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_end = 100
    cam.rotation_euler = (p, 0, 0)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = S.RENDER_SAMPLES
    sc.cycles.use_denoising = False
    sc.render.film_transparent = S.FILM_TRANSPARENT
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = S.VIEW_TRANSFORM
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = S.OUTLINE_PX_AT_256 * SIZE / 256
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    ls = vl.freestyle_settings.linesets.new("outline")
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    ls.linestyle.color = S.OUTLINE_COLOR
    path = os.path.join(OUT, f"{name}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


# (nom, fonction, taille de cadrage, inclinaison en degrés, décalage vertical caméra)
ITEMS = [("assembleur", assembler, 4.4, S.PITCH_BUILDING_DEG, 0.9), ("four", furnace, 4.4, S.PITCH_BUILDING_DEG, 0.9),
         ("coffre", chest, 3.4, S.PITCH_BUILDING_DEG, 0.5), ("convoyeur", belt, 3.6, S.PITCH_TOPDOWN_DEG, 0.0),
         ("poteau", pole, 4.4, S.PITCH_BUILDING_DEG, 1.2), ("minerai", ore, 3.0, S.PITCH_BUILDING_DEG, 0.3)]
paths = [render(b, n, s, pt, cy) for n, b, s, pt, cy in ITEMS]

tiles = []
for p in paths:
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    a = im[:, :, 3:4] / 255.0
    bg = np.full(im.shape[:2] + (3,), (90, 90, 90), np.float32)
    tiles.append((im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8))
sheet = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
cv2.imwrite(os.path.join(OUT, "planche.png"), sheet)
print("OK", os.path.join(OUT, "planche.png"))
