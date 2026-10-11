"""Fonctions communes de rendu cel-shading (voir ../STYLE.md et cel_style.py).

Mêmes fonctions que cartoon/blender/lib.py, dont on reprend tout (briques de modélisation, chemins, planches,
icônes, ombres portées), sauf deux :
- mat() : couleur avivée, marquée « cel », avec la couleur de son contour ;
- render_scene() : deux rendus de la même caméra, puis assemblage :
    1. couleurs : aplats sans ombrage, contour de silhouette à la teinte foncée de chaque matière ;
    2. lumière : matières remplacées par du blanc mat, éclairé par un soleil (LIGHT_DIR) à ombres dures ;
  l'éclairement de chaque pixel, seuillé (SHADOW_BELOW, HIGHLIGHT_ABOVE), choisit le ton : ombre bleutée,
  éclairé ou clair. Ombres portées sur l'objet comprises.

Comme les générateurs cartoon importent `lib`, run_cartoon.py peut rendre un modèle cartoon en cel-shading.
"""
import colorsys, importlib.util, math, os, sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
CARTOON = os.path.normpath(os.path.join(HERE, "..", "..", "cartoon", "blender"))
sys.path.insert(0, HERE)
import cel_style as C


def _cartoon_lib():
    """cartoon/blender/lib.py, chargé sous le nom cartoon_lib (avec son propre module style)."""
    if "cartoon_lib" not in sys.modules:
        spec = importlib.util.spec_from_file_location("cartoon_lib", os.path.join(CARTOON, "lib.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["cartoon_lib"] = module
        spec.loader.exec_module(module)
    return sys.modules["cartoon_lib"]


_cl = _cartoon_lib()
S = _cl.S                                   # style cartoon : projection, format, palette d'origine
for _name in dir(_cl):
    if not _name.startswith("_") and callable(getattr(_cl, _name)) and _name not in globals():
        globals()[_name] = getattr(_cl, _name)


# --- couleurs ---------------------------------------------------------------------------------------------------

def _to_srgb(v):
    return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def _to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def vivid(rgb):
    """Couleur de la palette (RGB linéaire) avivée : saturation et valeur multipliées (en sRGB, HSV)."""
    h, s, v = colorsys.rgb_to_hsv(*(_to_srgb(c) for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, s * C.SATURATION_GAIN), min(1.0, v * C.VALUE_GAIN))
    return tuple(_to_linear(c) for c in (r, g, b))


def line_color(rgb):
    """Couleur du contour d'une matière (RGB linéaire) : sa teinte assombrie, un peu bleutée."""
    r, g, b = (_to_srgb(c) * C.OUTLINE_DARKEN for c in rgb)
    return tuple(_to_linear(min(1.0, c)) for c in (r, g, min(1.0, b * C.OUTLINE_BLUE)))


def mat(name, rgb, avive=True):
    """Aplat de la couleur (RGB linéaire), en émission ; le ton (ombre, éclairé, clair) est posé par render_scene.
    `avive` : couleur de la palette cartoon, avivée (modèles du mod cartoon) ; False : couleur prise telle quelle."""
    base = vivid(rgb) if avive else tuple(rgb)
    m = bpy.data.materials.new(name)
    m["cel"] = 1
    m.line_color = (*line_color(base), 1)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*base, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def couleur(name, hex_):
    """Matière d'une couleur #rrggbb (sRGB) prise telle quelle : ton « éclairé » de l'objet (modèles du mod)."""
    return mat(name, S._lin(hex_), avive=False)


def _flat(name, shader, value):
    """Matière de la passe de lumière : blanc mat (« diffuse ») ou émission uniforme."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    node = nt.nodes.new(shader)
    node.inputs["Color"].default_value = (value, value, value, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(node.outputs[0], out.inputs[0])
    return m


# --- rendu ------------------------------------------------------------------------------------------------------

def _camera(scale, pitch_deg, cy, shift_x, shift_y):
    """Caméra de cartoon/blender/lib.render_scene (même projection, même cadrage)."""
    p = math.radians(pitch_deg)
    root = bpy.data.objects.new("root", None)
    bpy.context.scene.collection.objects.link(root)
    root.scale = (1, 1 / math.cos(p), 1) if S.GROUND_STRETCH else (1, 1, 1)
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH":
            o.parent = root
    d = 20
    bpy.ops.object.camera_add(location=(0, -d * math.sin(p), d * math.cos(p) + cy))
    cam = bpy.context.object
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.shift_y = shift_y
    cam.data.shift_x = shift_x
    cam.data.clip_end = 100
    cam.rotation_euler = (p, 0, 0)
    bpy.context.scene.camera = cam


def _render(path, size, view_transform, outline_px=None, depth="8"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = S.RENDER_SAMPLES
    sc.cycles.use_denoising = False
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = depth
    sc.view_settings.view_transform = view_transform
    outline = outline_px is not None
    sc.render.use_freestyle = outline
    vl = sc.view_layers[0]
    vl.use_freestyle = outline
    if outline:
        sc.render.line_thickness_mode = "ABSOLUTE"
        sc.render.line_thickness = outline_px
        for old in list(vl.freestyle_settings.linesets):
            vl.freestyle_settings.linesets.remove(old)
        ls = vl.freestyle_settings.linesets.new("silhouette")
        ls.select_silhouette = ls.select_border = True
        ls.select_crease = False
        ls.linestyle.color = (0, 0, 0)
        tint = ls.linestyle.color_modifiers.new("matiere", "MATERIAL")
        tint.material_attribute = "LINE"
        tint.blend = "MIX"
        tint.influence = 1.0
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _light_pass(path, size):
    """Éclairement de chaque pixel (0 à 1 : cosinus normale-lumière, 0 dans les ombres portées). Les matières non
    « cel » (ombres, lueurs) valent un éclairement moyen : ton éclairé, ni ombre ni clair."""
    import cv2, numpy as np
    sc = bpy.context.scene
    white = _flat("cel-lumiere", "ShaderNodeBsdfDiffuse", 1.0)
    neutral = _flat("cel-neutre", "ShaderNodeEmission", (C.SHADOW_BELOW + C.HIGHLIGHT_ABOVE) / 2)
    saved = {}
    for o in sc.objects:
        if o.type == "MESH" and o.data.name not in saved:
            mats = list(o.data.materials)
            saved[o.data.name] = (o.data, mats)
            for i, m in enumerate(mats):
                o.data.materials[i] = white if m is not None and m.get("cel") else neutral
    from mathutils import Vector
    sun_data = bpy.data.lights.new("soleil", "SUN")
    sun_data.angle = 0.0
    sun_data.energy = math.pi            # blanc mat face au soleil = 1
    sun = bpy.data.objects.new("soleil", sun_data)
    sun.rotation_euler = Vector(C.LIGHT_DIR).to_track_quat("Z", "Y").to_euler()
    sc.collection.objects.link(sun)
    bounces = sc.cycles.max_bounces
    sc.cycles.max_bounces = 0            # lumière directe seulement
    world = sc.world
    sc.world = None
    _render(path, size, "Raw", depth="16")
    sc.world = world
    sc.cycles.max_bounces = bounces
    bpy.data.objects.remove(sun)
    for me, mats in saved.values():
        for i, m in enumerate(mats):
            me.materials[i] = m
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0
    os.remove(path)
    return im[:, :, 2], im[:, :, 3]


def tones(light, alpha):
    """Multiplicateur RGB (en sRGB, ordre BGR d'OpenCV) de chaque pixel selon son éclairement ; 1 hors de l'objet
    (le contour qui déborde de la silhouette garde sa couleur)."""
    import numpy as np
    out = np.ones(light.shape + (3,), np.float32)
    inside = alpha > 0.5
    out[inside & (light < C.SHADOW_BELOW)] = C.SHADOW_TINT[::-1]
    out[inside & (light > C.HIGHLIGHT_ABOVE)] = C.HIGHLIGHT_TINT[::-1]
    return out


def render_scene(path, size=256, scale=4.4, pitch_deg=S.PITCH_BUILDING_DEG, cy=0.0, supersample=None, shift_y=0.0,
                 outline=True, outline_units=None, shift_x=0.0):
    """Rend la scène courante en cel-shading, avec la projection du guide de style (signature de cartoon/lib).

    Rendu à `supersample` fois la taille puis réduit (alpha prémultiplié). `outline_units` : épaisseur de contour
    pensée pour le mod cartoon (icônes), ramenée à celle du cel-shading ; `outline=False` le supprime."""
    import cv2, numpy as np
    ss = supersample or S.SUPERSAMPLE
    size_final = size if isinstance(size, tuple) else (size, size)
    big = (size_final[0] * ss, size_final[1] * ss)
    _camera(scale, pitch_deg, cy, shift_x, shift_y)
    outline_px = None
    if outline:
        units = (outline_units or S.OUTLINE_UNITS) * C.OUTLINE_UNITS / S.OUTLINE_UNITS
        outline_px = units * max(big) / scale
    colors_path = path + ".couleurs.png"
    _render(colors_path, big, "Standard", outline_px)
    im = cv2.imread(colors_path, cv2.IMREAD_UNCHANGED).astype(np.float32)
    os.remove(colors_path)
    cel = any(m is not None and m.get("cel") for o in bpy.context.scene.objects if o.type == "MESH"
              for m in o.data.materials)
    if cel:
        light, alpha = _light_pass(path + ".lumiere.png", big)
        im[:, :, :3] = np.clip(im[:, :, :3] * tones(light, alpha), 0, 255)
    a = im[:, :, 3:4] / 255.0
    pre = np.dstack([im[:, :, :3] * a, im[:, :, 3:4]])
    small = cv2.resize(pre, size_final, interpolation=cv2.INTER_AREA) if ss > 1 else pre
    al = np.clip(small[:, :, 3:4] / 255.0, 1e-6, 1)
    out = np.dstack([np.clip(small[:, :, :3] / al, 0, 255), small[:, :, 3:4]])
    cv2.imwrite(path, np.clip(out, 0, 255).astype(np.uint8))
    return path


def render_shadow(build, path, size, scale, shear, shift_x=0.0, shift_y=0.0):
    """Ombre portée du modèle (voir cartoon/lib.render_shadow), allégée : alpha x GROUND_SHADOW_ALPHA."""
    import numpy as np
    shadow = _cartoon_render_shadow(build, path, size, scale, shear, shift_x, shift_y)
    shadow[:, :, 3] = np.round(shadow[:, :, 3] * C.GROUND_SHADOW_ALPHA).astype(np.uint8)
    return shadow


_cartoon_render_shadow = _cl.render_shadow

# Les fonctions reprises du mod cartoon (icônes, ombres portées...) appellent render_scene et mat dans leur module.
_cl.render_scene = render_scene
_cl.mat = mat
_cl.render_shadow = render_shadow
