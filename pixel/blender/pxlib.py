"""Rendu Blender « B→px » du mod pixel : un modèle 3D rendu directement à la résolution d'art (16 px par case).

Pas un rendu en grand réduit ensuite (ce qui faisait « 3D pixelisée » : dégradés et anticrénelage survivaient) :
- Cycles, 1 échantillon au centre de chaque pixel (filtre de 0,01 px) : aucun anticrénelage ;
- matières en émission pure, un ton de leur rampe (pixlib/palette.py) par orientation de face : dessus clair,
  face avant et flanc gauche moyens, flanc droit sombre (lumière en haut à gauche) ;
- un second rendu, matières remplacées par une couleur d'identifiant, donne la carte des matières que la passe
  pixel utilise (contours colorés, jonctions).

Les briques de modélisation (box, cyl, gear...) sont celles du mod cartoon (cartoon/blender/lib.py), chargées sans
son rendu. Ensuite : pixlib.passe puis pixlib.cadre (voir pixel/pixlib/__init__.py).
"""
import importlib.util
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
from pixlib import palette as P  # noqa: E402

CARTOON = os.path.normpath(os.path.join(HERE, "..", "..", "cartoon", "blender"))
PITCH_DEG = 30            # vue des bâtiments, comme les sprites originaux
ART_PER_TILE = 16
FACES = {"top": 3, "front": 2, "left": 2, "right": 1, "other": 1}   # orientation -> rang dans la rampe


def _cartoon_lib():
    if "cartoon_lib" not in sys.modules:
        sys.path.insert(0, CARTOON)                     # son module style
        spec = importlib.util.spec_from_file_location("cartoon_lib", os.path.join(CARTOON, "lib.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["cartoon_lib"] = module
        spec.loader.exec_module(module)
    return sys.modules["cartoon_lib"]


_C = _cartoon_lib()
reset, box, cyl, blob, frustum, hull, gear, rod, tri_plate = (
    _C.reset, _C.box, _C.cyl, _C.blob, _C.frustum, _C.hull, _C.gear, _C.rod, _C.tri_plate)


def _linear(c):
    """sRGB 8 bits -> linéaire (Blender émet en linéaire ; la vue « Standard » réencode en sRGB)."""
    v = [x / 255 for x in c]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v)


def mat(material, faces=None):
    """Matière de la palette (nom d'une rampe de pixlib/palette.py) : émission, un ton par orientation de face.
    `faces` remplace des rangs de FACES (ex. {"top": 4} pour un dessus brillant)."""
    ranks = dict(FACES, **(faces or {}))
    ramp = P.RAMPS[material]
    m = bpy.data.materials.new(material)
    m["pixel_material"] = material
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    n, link = nt.nodes, nt.links.new
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    link(geo.outputs["Normal"], sep.inputs[0])

    def test(axis, sign):                            # 1 si la normale pointe vers axis * sign
        mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = sign
        link(sep.outputs[axis], mul.inputs[0])
        gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
        link(mul.outputs[0], gt.inputs[0])
        return gt.outputs[0]

    color = n.new("ShaderNodeRGB")
    color.outputs[0].default_value = (*_linear(ramp[ranks["other"]]), 1)
    current = color.outputs[0]
    # priorités croissantes : la dernière qui s'applique gagne
    for face, axis, sign in (("right", "X", 1), ("left", "X", -1), ("front", "Y", -1), ("top", "Z", 1)):
        rgb = n.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = (*_linear(ramp[ranks[face]]), 1)
        mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
        link(test(axis, sign), mix.inputs[0])
        link(current, mix.inputs[6]); link(rgb.outputs[0], mix.inputs[7])
        current = mix.outputs[2]
    em = n.new("ShaderNodeEmission")
    link(current, em.inputs["Color"])
    out = n.new("ShaderNodeOutputMaterial")
    link(em.outputs[0], out.inputs[0])
    return m


def _camera(size, pitch_deg):
    p = math.radians(pitch_deg)
    d = 20
    bpy.ops.object.camera_add(location=(0, -d * math.sin(p), d * math.cos(p)))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(size) / ART_PER_TILE      # 1 unité = 1 case
    cam.data.clip_end = 100
    cam.rotation_euler = (p, 0, 0)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    sc.cycles.use_denoising = False
    sc.cycles.filter_width = 0.01                         # un point au centre du pixel : pas d'anticrénelage
    sc.cycles.seed = 0
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.dither_intensity = 0.0                      # pas de tramage à l'écriture en 8 bits
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.use_freestyle = False


def _render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGBA")).copy()
    os.remove(path)
    return a


def render_art(size, tmp, pitch_deg=PITCH_DEG):
    """Rend la scène courante en `size` = (l, h) px d'art, l'origine du monde au centre de l'image (coin de pixel
    si l et h sont pairs : c'est l'ancre (l/2, h/2) à donner à pixlib.cadre.place).
    Renvoie (image RGBA, carte des matières : tableau de noms, "" hors objet)."""
    if size[0] % 2 or size[1] % 2:
        raise ValueError("taille d'art paire attendue (origine sur un coin de pixel)")
    _camera(size, pitch_deg)
    color = _render(tmp)
    # second rendu : chaque matière en couleur d'identifiant
    names = sorted({m["pixel_material"] for m in bpy.data.materials if "pixel_material" in m})
    ids = {}
    for m in bpy.data.materials:
        if "pixel_material" not in m:
            continue
        k = names.index(m["pixel_material"]) + 1
        ids[k] = m["pixel_material"]
        nt = m.node_tree
        nt.nodes.clear()
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (k / 255, 0, 0, 1)
        em.inputs["Strength"].default_value = 1.0
        nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
    bpy.context.scene.view_settings.view_transform = "Raw"
    ident = _render(tmp)
    materials = np.full(color.shape[:2], "", dtype=object)
    for k, name in ids.items():
        materials[(ident[..., 0] == k) & (ident[..., 3] > 0)] = name
    return color, materials


def render_shadow(size, tmp, kx=1.0, ky=0.6, pitch_deg=PITCH_DEG):
    """Silhouette de l'ombre portée (soleil en haut à gauche), même cadrage que render_art. À appeler sur une scène
    neuve (la scène est remplacée par son ombre)."""
    _C.flatten_to_shadow(kx, ky)
    _camera(size, pitch_deg)
    return _render(tmp)
