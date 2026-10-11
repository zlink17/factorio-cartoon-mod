"""Personnage (character) : modèle articulé, animations, calques du jeu (lot 2.10).

Usage : python cartoon/blender/character.py <dossier_sortie> [--essai] [--anim idle,running...]

Le jeu dessine le personnage en calques (base/prototypes/entity/character-animations.lua, lu ici avec lupa) :
  level1_<anim>.png             le corps, sans armure
  level1_<anim>_mask.png        les pièces à la couleur du joueur, en gris clair : le jeu les multiplie par cette
                                couleur et les dessine par-dessus le corps
  level1_<anim>_shadow.png      l'ombre (draw_as_shadow)
  levelNaddon_<anim>*.png       armure de niveau 2 (lourde, modulaire) ou 3 (assistée), dessinée par-dessus le
                                corps de niveau 1, avec son masque et son ombre
Animations : idle et idle_gun (8 directions x 22 images), running (8 x 22), running_gun (18 directions du nord au
sud par l'est, 22 images ; le jeu retourne l'image pour l'ouest et prend alors running_gun_shadow_flipped : l'ombre
du personnage retourné, non retournée), mining_tool (8 x 26), dead (2 corps, sans direction). Directions des
planches : nord, puis sens horaire. Certaines planches sont coupées en deux fichiers (`stripes`, -1 et -2 : les
images 0 à n/2 - 1, puis les suivantes, de toutes les directions).
Laissés d'origine : traces de pas (footprints), carte d'effet et reflet dans l'eau (techniques).

Modèle : pièces arrondies (un maillage par pièce, donc un contour par pièce) accrochées à une hiérarchie
d'articulations (objets vides) ; une pose = des rotations d'articulations. Le modèle est construit une fois, chaque
image règle la pose puis rend ses calques : pièces cachées, pièces en réserve (holdout : elles cachent ce qui est
derrière sans se dessiner), matériau de masque.
"""
import math, os, sys

import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import FACTORIO_DATA, mat, mip_strip, render_icon, reset, sheet, target

PX_PER_TILE = 64                      # fichiers à scale 0.5 : 64 px par case
CANVAS = (448, 288)                   # canevas de rendu ; l'entité (les pieds) est en ENTITY
ENTITY = (224, 180)
SIZE = 1.15                           # échelle du modèle : hauteur à l'écran de l'original (~97 px du fichier)
PITCH = 50                            # caméra à 50° de la verticale (bâtiments : 30°) : le personnage de l'original
                                      # est vu plus de côté (couché, il est aussi long que haut debout)
OUTLINE_PX = 2.0                      # largeur totale du contour, en px du fichier (1 px à l'écran)
SUN_SHEAR = (0.8, 0.03)               # ombre : décalage au sol par unité de hauteur (vers la droite)
GUN_DIRS = 18                         # running_gun : du nord au sud par l'est

J = {}                                # articulations : nom -> objet vide
PARTS = {}                            # groupe -> pièces

# Groupes de pièces : corps (niveau 1), accessoires selon l'animation, armures. « *_tint » : à la couleur du joueur.
LEVEL1 = ("body", "tint", "gun_back", "gun_hand", "pick")
ARMOR = {2: ("armor2", "armor2_tint"), 3: ("armor3", "armor3_tint")}
PROPS = {"idle": "gun_back", "running": "gun_back", "idle_gun": "gun_hand", "running_gun": "gun_hand",
         "mining_tool": "pick", "dead": None}


def lin(hex_):
    return S._lin(hex_)


COL = {                               # teintes de l'image cible (cartoon/concept/cibles/personnage-b-24.png)
    "suit": lin("#a5b6ad"),           # combinaison gris-bleu clair
    "tint": lin("#94a29a"),           # pièces à la couleur du joueur (casque, veste, manches, genouillères),
                                      # sous le masque
    "skin": lin("#d9a383"),
    "goggles": lin("#fcd20e"),        # lunettes et lampe jaunes
    "strap": lin("#6a5444"),          # harnais, ceinture, sac
    "leather": lin("#7a6656"),        # gants et bottes
    "cuff": lin("#ed9835"),           # brassards orange
    "muff": lin("#5e6662"),
    "gun": lin("#8fa2a2"),
    "gun_dark": lin("#4e5257"),
    "wood": lin("#a8743a"),
    "tool": lin("#80868c"),
    "armor2": lin("#8a8478"),
    "armor3": lin("#5e6266"),
    "mask": lin("#e8e8e8"),           # masque : gris clair, le jeu le multiplie par la couleur du joueur
}


# --- prototype ---------------------------------------------------------------------------------------------------

def animations():
    """character_animations du jeu (table Lua lue avec lupa)."""
    import lupa
    lua = lupa.LuaRuntime()
    src = open(os.path.join(FACTORIO_DATA, "base/prototypes/entity/character-animations.lua")).read()
    lua.execute("util = {by_pixel = function(x, y) return {x / 32, y / 32} end}\n" + src)
    return lua.globals().character_animations


def layer_files(spec):
    """Fichiers d'un calque : [(chemin sous graphics/, première image, nombre d'images par direction)]."""
    fc = spec["frame_count"] or 1
    if spec["stripes"]:
        out, f0 = [], 0
        for k in sorted(spec["stripes"].keys()):
            st = spec["stripes"][k]
            out.append((st["filename"].replace("__base__/graphics/", "base/"), f0, st["width_in_frames"]))
            f0 += st["width_in_frames"]
        return out
    return [(spec["filename"].replace("__base__/graphics/", "base/"), 0, fc)]


# --- construction ------------------------------------------------------------------------------------------------

def joint(name, parent, loc):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = J.get(parent)
    e.location = loc
    e.rotation_mode = "XYZ"
    J[name] = e
    return e


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def part(o, j, loc, group, m, rot=(0, 0, 0)):
    """Accroche la pièce `o` à l'articulation `j` (position et rotation locales), dans le groupe `group`."""
    for c in o.users_collection:
        c.objects.unlink(o)
    coll(group).objects.link(o)
    o.parent = J[j]
    o.location = loc
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    o.data.materials.append(m)
    PARTS.setdefault(group, []).append(o)
    return o


def rbox(size, bevel):
    """Boîte aux arêtes arrondies (un seul maillage : pas de contour sur les arrondis)."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    b = o.modifiers.new("b", "BEVEL")
    b.width = bevel
    b.segments = 3
    b.limit_method = "NONE"
    return o


def ball(r, k=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=r)
    o = bpy.context.object
    o.scale = k
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.shade_smooth()
    return o


def limb(length, r0, r1):
    """Segment de membre vertical centré, section ronde (r0 en haut, r1 en bas), bouts arrondis."""
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r1, radius2=r0, depth=length)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    b = o.modifiers.new("b", "BEVEL")
    b.width = min(r0, r1) * 0.6
    b.segments = 3
    b.limit_method = "NONE"
    return o


def build():
    """Le personnage debout, face au sud (vers la caméra, -y), pieds à l'origine ; armures et accessoires inclus."""
    reset()
    J.clear()
    PARTS.clear()
    M = {k: mat(k, v) for k, v in COL.items()}
    joint("base", None, (0, 0, 0))                     # retournement (ombre retournée)
    joint("root", "base", (0, 0, 0))                   # direction, échelle
    J["root"].scale = (SIZE, SIZE, SIZE)
    joint("hips", "root", (0, 0, 0.66))
    joint("chest", "hips", (0, 0, 0.0))
    joint("neck", "chest", (0, 0, 0.47))
    # bassin, ceinture, torse (veste à la couleur du joueur), harnais
    part(rbox((0.34, 0.22, 0.18), 0.06), "hips", (0, 0, -0.01), "body", M["suit"])
    part(rbox((0.38, 0.26, 0.06), 0.025), "chest", (0, 0, 0.07), "body", M["strap"])
    part(rbox((0.42, 0.28, 0.42), 0.14), "chest", (0, 0, 0.28), "tint", M["tint"])
    for x in (-0.1, 0.1):                              # bretelles devant, sangle de poitrine
        part(rbox((0.05, 0.03, 0.34), 0.012), "chest", (x, -0.13, 0.28), "body", M["strap"])
    part(rbox((0.36, 0.03, 0.045), 0.012), "chest", (0, -0.135, 0.33), "body", M["strap"])
    # tête : visage, casque rond à la couleur du joueur, lunettes et lampe jaunes, oreillettes
    part(limb(0.08, 0.075, 0.08), "neck", (0, 0, 0.02), "body", M["suit"])
    part(ball(0.115, (1, 0.95, 1.05)), "neck", (0, -0.03, 0.12), "body", M["skin"])
    part(ball(0.15, (1, 1, 0.78)), "neck", (0, 0.03, 0.21), "tint", M["tint"])
    part(rbox((0.2, 0.06, 0.045), 0.02), "neck", (0, -0.115, 0.16), "body", M["goggles"])
    part(limb(0.03, 0.04, 0.04), "neck", (0, -0.1, 0.27), "body", M["goggles"], rot=(60, 0, 0))
    for x in (-0.15, 0.15):
        part(limb(0.04, 0.045, 0.045), "neck", (x, 0.0, 0.15), "body", M["muff"], rot=(0, 90, 0))
    # sac à dos, tuyau, fusil en bandoulière
    part(rbox((0.32, 0.15, 0.36), 0.05), "chest", (0, 0.2, 0.28), "body", M["strap"])
    part(limb(0.3, 0.025, 0.025), "chest", (0.13, 0.26, 0.48), "body", M["gun"])
    for s, side in ((-1, "L"), (1, "R")):
        # bras : manche à la couleur du joueur, avant-bras gris, brassard orange, gros gant de cuir
        joint(f"sh{side}", "chest", (s * 0.225, 0, 0.42))
        joint(f"el{side}", f"sh{side}", (0, 0, -0.23))
        joint(f"ha{side}", f"el{side}", (0, 0, -0.22))
        part(limb(0.27, 0.08, 0.065), f"sh{side}", (0, 0, -0.09), "tint", M["tint"])
        part(limb(0.13, 0.062, 0.058), f"el{side}", (0, 0, -0.05), "body", M["suit"])
        part(limb(0.08, 0.068, 0.068), f"el{side}", (0, 0, -0.15), "body", M["cuff"])
        part(rbox((0.12, 0.11, 0.14), 0.045), f"ha{side}", (0, 0, -0.03), "body", M["leather"])
        # jambes : cuisse, genouillère à la couleur du joueur, tibia, botte haute
        joint(f"hip{side}", "hips", (s * 0.095, 0, -0.05))
        joint(f"kn{side}", f"hip{side}", (0, 0, -0.29))
        joint(f"an{side}", f"kn{side}", (0, 0, -0.27))
        part(limb(0.29, 0.1, 0.085), f"hip{side}", (0, 0, -0.14), "body", M["suit"])
        part(ball(0.08, (1, 0.75, 1.05)), f"kn{side}", (0, -0.055, -0.01), "tint", M["tint"])
        part(limb(0.12, 0.08, 0.075), f"kn{side}", (0, 0, -0.07), "body", M["suit"])
        part(limb(0.16, 0.088, 0.085), f"an{side}", (0, 0, 0.07), "body", M["leather"])
        part(rbox((0.15, 0.23, 0.09), 0.035), f"an{side}", (0, -0.04, -0.035), "body", M["leather"])
        # armure 2 : épaulières et jambières ; armure 3 : coque assistée (provisoire)
        part(ball(0.11, (1, 1, 0.8)), f"sh{side}", (s * 0.02, 0, 0.0), "armor2_tint", M["tint"])
        part(rbox((0.19, 0.21, 0.24), 0.05), f"kn{side}", (0, -0.01, -0.10), "armor2", M["armor2"])
        part(ball(0.13, (1, 1, 0.85)), f"sh{side}", (s * 0.03, 0, 0.0), "armor3_tint", M["tint"])
        part(limb(0.26, 0.09, 0.08), f"el{side}", (0, 0, -0.11), "armor3", M["armor3"])
        part(rbox((0.2, 0.26, 0.3), 0.06), f"kn{side}", (0, -0.01, -0.12), "armor3", M["armor3"])
    part(rbox((0.46, 0.31, 0.30), 0.08), "chest", (0, -0.02, 0.26), "armor2", M["armor2"])
    part(rbox((0.50, 0.34, 0.44), 0.10), "chest", (0, -0.01, 0.28), "armor3_tint", M["tint"])
    part(ball(0.19, (1, 1, 0.95)), "neck", (0, 0.0, 0.18), "armor3", M["armor3"])
    # fusil : en bandoulière dans le dos (crosse en bas à gauche, canon en haut à droite), ou en main
    part(rbox((0.08, 0.06, 0.5), 0.02), "chest", (0.0, 0.3, 0.32), "gun_back", M["gun"], rot=(0, -40, 0))
    part(rbox((0.07, 0.05, 0.12), 0.015), "chest", (0.08, 0.33, 0.28), "gun_back", M["gun_dark"], rot=(0, -40, 0))
    part(rbox((0.08, 0.46, 0.1), 0.02), "haR", (-0.04, -0.12, 0.0), "gun_hand", M["gun"])
    part(rbox((0.06, 0.1, 0.12), 0.015), "haR", (-0.04, 0.02, -0.08), "gun_hand", M["gun_dark"])
    # pioche : manche dans la main droite, fer au bout
    part(limb(0.5, 0.022, 0.022), "haR", (0, -0.22, 0), "pick", M["wood"], rot=(90, 0, 0))
    part(rbox((0.045, 0.06, 0.34), 0.015), "haR", (0, -0.46, 0), "pick", M["tool"])
    bpy.context.view_layer.update()


# --- poses -------------------------------------------------------------------------------------------------------
# Rotations en degrés : x avant/arrière (négatif = vers l'avant pour un membre qui pend), y latéral, z vertical.

def rot(name, x=0.0, y=0.0, z=0.0):
    J[name].rotation_euler = (math.radians(x), math.radians(y), math.radians(z))


def pose_rest():
    for k, e in J.items():
        if k not in ("base", "root"):
            e.rotation_euler = (0, 0, 0)
    J["hips"].location = (0, 0, 0.66)
    J["root"].location = (0, 0, 0)
    rot("shL", x=-4, y=-6); rot("shR", x=-4, y=6)
    rot("elL", x=-20, y=4); rot("elR", x=-20, y=-4)


def breathe(t):
    b = math.sin(2 * math.pi * t)
    J["hips"].location = (0, 0, 0.66 - 0.006 * (1 - b))
    rot("chest", x=2 + 1.5 * b)
    rot("neck", x=-2 * b)
    rot("knL", x=3); rot("knR", x=3)
    rot("hipL", x=-2); rot("hipR", x=-2)
    return b


def pose_idle(t):
    """Repos : respiration lente."""
    pose_rest()
    b = breathe(t)
    rot("shL", x=3 * b, y=-8 - 2 * b); rot("shR", x=-3 * b, y=8 + 2 * b)


def aim():
    """Fusil tenu à deux mains devant soi, à hauteur de hanche."""
    rot("shR", x=-35, y=6); rot("elR", x=-55)
    rot("shL", x=-55, y=-20, z=-30); rot("elL", x=-50)


def pose_idle_gun(t):
    pose_rest()
    breathe(t)
    aim()


def legs_run(t):
    """Jambes de la course (cycle de deux pas) : grande foulée, genou haut au retour, bassin qui rebondit."""
    ph = 2 * math.pi * t
    s = math.sin(ph)
    J["hips"].location = (0, 0, 0.57 + 0.06 * abs(math.cos(ph)))
    rot("hips", z=10 * s)
    rot("neck", x=-16)
    for side, k in (("L", 1), ("R", -1)):
        a = k * s                                       # +1 : jambe en avant (contact)
        c = k * math.cos(ph)                            # > 0 : jambe qui revient vers l'avant
        rot(f"hip{side}", x=-48 * a - 18 - 25 * max(0.0, c))
        rot(f"kn{side}", x=18 + 95 * max(0.0, c) + 20 * max(0.0, -a))
        rot(f"an{side}", x=-12 * a)
    return s


def pose_run(t):
    """Course : un cycle de deux pas, buste penché, bras pliés qui balancent."""
    pose_rest()
    s = legs_run(t)
    rot("chest", x=22, z=-16 * s)
    for side, k in (("L", 1), ("R", -1)):
        rot(f"sh{side}", x=50 * k * s - 10, y=-k * 12)
        rot(f"el{side}", x=-85)


def pose_run_gun(t):
    pose_rest()
    s = legs_run(t)
    rot("chest", x=16, z=-4 * s)
    aim()


def pose_mining(t):
    """Pioche : lente montée au-dessus de l'épaule droite (images 0 à 16), coup (17 à 21), retour."""
    pose_rest()
    breathe(0)
    f = t * 26
    if f < 17:
        k = f / 17
        sh = -40 - 130 * (0.5 - 0.5 * math.cos(math.pi * k))
    elif f < 22:
        k = (f - 17) / 5
        sh = -170 + 150 * k * k
    else:
        k = (f - 22) / 4
        sh = -20 - 20 * k
    up = (-sh - 20) / 150                              # 0 : pioche en bas, 1 : au-dessus de la tête
    rot("shR", x=sh, y=10)
    rot("elR", x=-30 - 20 * up)
    rot("shL", x=-30, y=-15)
    rot("elL", x=-60)
    rot("chest", x=18 - 14 * up, z=6 * up)
    rot("hipL", x=-20); rot("knL", x=25); rot("hipR", x=10); rot("knR", x=10)


def pose_dead(t):
    """Corps couché sur le dos (deux variantes : t = 0 ou 0,5)."""
    pose_rest()
    v = int(t * 2)
    J["root"].location = (0, 0, 0.13 * SIZE)
    J["hips"].location = (0, 0, 0.0)
    rot("hipL", x=10, y=-15 - 10 * v); rot("hipR", x=-5, y=20); rot("knL", x=30 * v)
    rot("shL", y=-70, x=-20 * v); rot("shR", y=60 + 30 * v); rot("elL", x=-40); rot("elR", x=-30 * v)
    rot("neck", y=25 - 50 * v)


POSES = {"idle": pose_idle, "idle_gun": pose_idle_gun, "running": pose_run, "running_gun": pose_run_gun,
         "mining_tool": pose_mining, "dead": pose_dead}


def set_facing(angle_deg, dead_variant=None):
    """Direction en degrés depuis le nord, sens horaire. Le modèle est construit face au sud."""
    r = J["root"]
    if dead_variant is None:
        r.rotation_euler = (0, 0, math.radians(180.0 - angle_deg))
    else:                                             # couché : la tête vers le nord-est ou l'ouest
        r.rotation_euler = (math.radians(-90), 0, math.radians((-60, 120)[dead_variant]))


# --- rendu -------------------------------------------------------------------------------------------------------

def setup_camera():
    sc = bpy.context.scene
    p = math.radians(PITCH)
    d = 20
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0, -d * math.sin(p), d * math.cos(p))
    cam.rotation_euler = (p, 0, 0)
    cam_data.type = "ORTHO"
    W, H = CANVAS
    cam_data.ortho_scale = W / PX_PER_TILE
    cam_data.shift_x = (W / 2 - ENTITY[0]) / W
    cam_data.shift_y = (ENTITY[1] - H / 2) / W
    cam_data.clip_end = 100
    sc.camera = cam
    ss = S.SUPERSAMPLE
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = S.RENDER_SAMPLES
    sc.cycles.use_denoising = False
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = W * ss, H * ss
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = S.VIEW_TRANSFORM
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = OUTLINE_PX * ss
    vl = sc.view_layers[0]
    vl.freestyle_settings.crease_angle = math.radians(S.OUTLINE_CREASE_DEG)
    for old in list(vl.freestyle_settings.linesets):
        vl.freestyle_settings.linesets.remove(old)
    ls = vl.freestyle_settings.linesets.new("outline")
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    ls.linestyle.color = S.OUTLINE_COLOR
    ls.linestyle.thickness = 1.0                   # (3 par défaut)
    ls.select_by_collection = True
    return ls


def shot(path):
    import cv2, numpy as np
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32)
    os.remove(path)
    if S.SUPERSAMPLE > 1:
        a = im[:, :, 3:4] / 255.0
        pre = np.dstack([im[:, :, :3] * a, im[:, :, 3:4]])
        small = cv2.resize(pre, CANVAS, interpolation=cv2.INTER_AREA)
        al = np.clip(small[:, :, 3:4] / 255.0, 1e-6, 1)
        im = np.dstack([np.clip(small[:, :, :3] / al, 0, 255), small[:, :, 3:4]])
    return np.clip(im, 0, 255).astype(np.uint8)


class Layers:
    """Calques d'une pose : corps et masque du niveau 1, armure et masque des niveaux 2 et 3, ombres."""

    def __init__(self, out):
        self.out = out
        self.ls = setup_camera()
        self.mask_m = mat("mask", COL["mask"])
        black = bpy.data.materials.new("black")
        black.use_nodes = True
        nt = black.node_tree
        nt.nodes.clear()
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (0, 0, 0, 1)
        nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs[0])
        self.black = black
        self.shear = bpy.data.objects.new("shear", None)
        bpy.context.scene.collection.objects.link(self.shear)
        kx, ky = SUN_SHEAR
        self.shear_m = Matrix(((1, 0, kx, 0), (0, 1, -ky, 0), (0, 0, 0.001, 0), (0, 0, 0, 1)))
        # collections des traits : une par calque dessiné
        self.lines = {}
        for name, groups in (("l1", ("body", "tint", "gun_back", "gun_hand", "pick")), ("l1_tint", ("tint",)),
                             ("a2", ARMOR[2]), ("a2_tint", ("armor2_tint",)),
                             ("a3", ARMOR[3]), ("a3_tint", ("armor3_tint",))):
            c = bpy.data.collections.new("lines_" + name)
            bpy.context.scene.collection.children.link(c)
            for g in groups:                            # Freestyle ne voit que les objets directs d'une collection
                for o in PARTS[g]:
                    c.objects.link(o)
            self.lines[name] = c
        self.prop = None

    def setup(self, prop):
        self.prop = prop

    def _state(self, shown, drawn, masked=()):
        """shown : groupes présents (les autres cachés) ; drawn : dessinés ; masked : dessinés en masque ;
        les groupes présents mais ni dessinés ni masqués sont en réserve."""
        self.saved = []
        for g, objs in PARTS.items():
            for o in objs:
                o.hide_render = g not in shown
                o.is_holdout = g in shown and g not in drawn and g not in masked
                if g in masked:
                    self.saved.append((o, o.material_slots[0].material))
                    o.material_slots[0].material = self.mask_m

    def _restore(self):
        for o, m in self.saved:
            o.material_slots[0].material = m

    def _render(self, lines, freestyle=True):
        sc = bpy.context.scene
        sc.render.use_freestyle = freestyle
        sc.view_layers[0].use_freestyle = freestyle
        if lines:
            self.ls.collection = self.lines[lines]
        im = shot(os.path.join(self.out, "_perso.png"))
        self._restore()
        return im

    def level1(self):
        return [g for g in ("body", "tint") + ((self.prop,) if self.prop else ())]

    def body(self):
        l1 = self.level1()
        self._state(l1, l1)
        return self._render("l1")

    def mask(self):
        l1 = self.level1()
        self._state(l1, (), ("tint",))
        return self._render("l1_tint")

    def addon(self, n):
        l1 = self.level1()
        self._state(l1 + list(ARMOR[n]), ARMOR[n])
        return self._render(f"a{n}")

    def addon_mask(self, n):
        l1 = self.level1()
        self._state(l1 + list(ARMOR[n]), (), (f"armor{n}_tint",))
        return self._render(f"a{n}_tint")

    def shadow(self, n=1, flipped=False):
        shown = self.level1() + (list(ARMOR[n]) if n > 1 else [])
        self._state(shown, shown)
        vl = bpy.context.scene.view_layers[0]
        base = J["base"]
        base.scale = (-1, 1, 1) if flipped else (1, 1, 1)
        base.parent = self.shear
        base.matrix_parent_inverse = self.shear_m
        vl.material_override = self.black
        bpy.context.view_layer.update()
        im = self._render(None, freestyle=False)
        vl.material_override = None
        base.parent = None
        base.matrix_parent_inverse = Matrix.Identity(4)
        base.scale = (1, 1, 1)
        im[:, :, :3] = 0
        return im


def crop(im, spec):
    """Cadre d'un calque du prototype (taille, shift en cases à 32 px) dans le canevas centré sur ENTITY."""
    w, h = spec["width"], spec["height"]
    sx, sy = spec["shift"][1] * 2 * 32, spec["shift"][2] * 2 * 32
    x0 = int(round(ENTITY[0] + sx - w / 2))
    y0 = int(round(ENTITY[1] + sy - h / 2))
    return im[y0:y0 + h, x0:x0 + w].copy()


# Calques produits pour chaque image : (niveau, nom du calque dans le prototype, fonction de rendu)
def layer_jobs(L, anim):
    jobs = [("level1", anim, L.body), ("level1", anim + "_mask", L.mask)]
    if anim != "dead":
        jobs.append(("level1", anim + "_shadow", lambda: L.shadow(1)))
    else:
        jobs.append(("level1", "dead_shadow", lambda: L.shadow(1)))
    for n in (2, 3):
        jobs += [(f"level{n}addon", anim, lambda n=n: L.addon(n)),
                 (f"level{n}addon", anim + "_mask", lambda n=n: L.addon_mask(n))]
        if anim != "dead":
            jobs.append((f"level{n}addon", anim + "_shadow", lambda n=n: L.shadow(n)))
    if anim == "running_gun":
        jobs.append(("level1", "running_gun_shadow_flipped", lambda: L.shadow(1, True)))
        for n in (2, 3):
            jobs.append((f"level{n}addon", "running_gun_shadow_flipped", lambda n=n: L.shadow(n, True)))
    return jobs


def frames_of(anim):
    """(nombre de directions, angles, nombre d'images)."""
    if anim == "dead":
        return 1, [0], 2
    n = GUN_DIRS if anim == "running_gun" else 8
    angles = [180.0 * d / (n - 1) for d in range(n)] if anim == "running_gun" else [45.0 * d for d in range(n)]
    return n, angles, 26 if anim == "mining_tool" else 22


def write_anim(out, CA, L, anim, frame_step=1):
    import cv2, numpy as np
    n_dirs, angles, fc = frames_of(anim)
    L.setup(PROPS[anim])
    jobs = layer_jobs(L, anim)
    got = {(lv, name): [] for lv, name, _ in jobs}
    for d, ang in enumerate(angles):
        for f in range(fc):
            if f % frame_step:                         # essai : images sautées remplacées par la précédente
                for k in got:
                    got[k].append(got[k][-1])
                continue
            POSES[anim](f / fc)
            set_facing(ang, f if anim == "dead" else None)
            bpy.context.view_layer.update()
            for lv, name, fn in jobs:
                got[(lv, name)].append(crop(fn(), CA[lv][name]))
    written = []
    for (lv, name), frames in got.items():
        spec = CA[lv][name]
        for path, f0, nf in layer_files(spec):
            sel = [frames[d * fc + f] for d in range(n_dirs) for f in range(f0, f0 + nf)]
            if spec["line_length"] and not spec["stripes"]:
                cols = spec["line_length"]
            else:
                full = cv2.imread(os.path.join(FACTORIO_DATA, path.replace("base/", "base/graphics/", 1)),
                                  cv2.IMREAD_UNCHANGED)
                cols = full.shape[1] // spec["width"]
            if spec["stripes"]:
                cols = nf
            img = sheet(sel, cols) if len(sel) % cols == 0 else sheet(sel + [np.zeros_like(sel[0])] *
                                                                       (cols - len(sel) % cols), cols)
            cv2.imwrite(target(out, path), img)
            written.append(path)
    return written


def write(out, anims=None, frame_step=1):
    CA = animations()
    build()
    L = Layers(out)
    for anim in anims or ("idle", "idle_gun", "running", "running_gun", "mining_tool", "dead"):
        for p in write_anim(out, CA, L, anim, frame_step):
            print(p, flush=True)
    import cv2
    icon = render_icon(lambda: (build(), pose_idle(0), set_facing(150), bpy.context.view_layer.update()),
                       os.path.join(out, "_icon.png"), fill=60, outline_px=0.5)
    cv2.imwrite(target(out, "core/icons/entity/character.png"), mip_strip(icon))


if __name__ == "__main__":
    args = sys.argv[1:]
    out = [a for a in args if not a.startswith("--")][0]
    os.makedirs(out, exist_ok=True)
    anims = None
    for a in args:
        if a.startswith("--anim="):
            anims = a.split("=", 1)[1].split(",")
    write(out, anims, 4 if "--essai" in args else 1)
    print("OK personnage", flush=True)
