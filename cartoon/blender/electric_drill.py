"""Foreuse électrique (electric-mining-drill) : cadre, tête de forage, pièces avant, sorties, ombres, icône.

Usage : python cartoon/blender/electric_drill.py <dossier_sortie> [partie[,partie...]|toutes] [--apercu]
        partie = cadres, tetes, sorties, integrations, icone ; --apercu : une seule image par planche (réglages)

Le jeu compose la foreuse de calques (voir le prototype) ; on les produit tous à partir d'un même modèle 3D, au
cadre et au décalage (shift) de l'original :
  electric-mining-drill-<D>.png, -<D>-shadow.png   cadre fixe de la direction D (rails, poutre jaune, moteur,
                                                    trémie) et son ombre
  electric-mining-drill-<D>-front.png               (S, E, W) pièces du cadre situées devant la tête, redessinées
                                                    par-dessus elle
  electric-mining-drill.png, -shadow.png            tête verticale (nord et sud), 30 images ; ombre 21 images
  electric-mining-drill-horizontal.png, -shadow     tête horizontale (est et ouest), idem
  electric-mining-drill-horizontal-front.png        pièce de la tête horizontale devant le rail avant
  electric-mining-drill-<D>-output.png              tambour de sortie, 5 images
  electric-mining-drill-<D>-integration.png         terre remuée sous la foreuse, en aplat semi-transparent
  electric-mining-drill.png (icône)                 64 px + mipmaps
Le jeu fait glisser la tête le long des rails (shift_animation_waypoints) : elle est rendue à l'origine.
Laissés d'origine : voyants (teintés par l'état), poussières et fumées (lot 3.9), restes (lot 3.9).

Modèle (construit pour le nord, puis tourné) : deux rails crantés le long des côtés (x = ±RAIL_X), poutre jaune
coudée en travers à l'arrière (côté sortie) portant le moteur et la trémie ; tête : corps gris-bleu à plaque
cuivre, moteur, deux bras jusqu'aux rails, foret à vis qui tourne, tuyau rouge.
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, cyl, entity_path, load, mat, render_scene, render_shadow, reset, rod, save_icon, sheet

P = S.PALETTE
NAME = "electric-mining-drill"
PX_PER_TILE = 64
CANVAS = 512
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.018
YAW = {"N": 0, "E": -90, "S": 180, "W": 90}

def px(shift):
    return (shift[0] * PX_PER_TILE, shift[1] * PX_PER_TILE)

# cadres de l'original : (taille, décalage en px)
BASE = {"N": ((190, 208), (0, -0.125)), "E": ((192, 188), (0, -0.125)), "S": ((184, 192), (0, -0.03125)),
        "W": ((192, 188), (0, -0.125))}
BASE_SHADOW = {"N": ((212, 204), (0.1875, -0.09375)), "E": ((222, 182), (0.3125, 0.0625)),
               "S": ((212, 204), (0.1875, 0.0625)), "W": ((200, 182), (-0.15625, 0.0625))}
FRONT = {"S": ((190, 104), (0, 0.84375)), "E": ((136, 148), (0.65625, 0.3125)), "W": ((134, 140), (-0.6875, 0.375))}
OUTPUT = {"N": ((60, 66), (-0.09375, -1.375)), "E": ((50, 74), (0.9375, -0.25)), "S": ((84, 56), (-0.03125, 1.0625)),
          "W": ((50, 60), (-0.96875, -0.40625))}
HEAD = {"vertical": ((162, 156), (0.03125, -0.34375)), "horizontal": ((80, 160), (0.0625, -0.375))}
HEAD_SHADOW = {"vertical": ((218, 56), (0.65625, 0.15625)), "horizontal": ((180, 164), (1.03125, 0.03125))}
HEAD_FRONT = ((66, 154), (-0.09375, 0.09375))
HEAD_FRAMES, HEAD_COLUMNS = 30, 6
HEAD_SHADOW_FRAMES, HEAD_SHADOW_COLUMNS = 21, 7
OUTPUT_FRAMES = 5

# dimensions (unités du monde)
RAIL_X, RAIL_LEN, RAIL_W, RAIL_H = 1.15, 2.85, 0.24, 0.42
BEAM_Y, BEAM_Z = 1.22, 0.62                # poutre jaune : position (arrière) et hauteur
BODY_Z = 1.65
ARM_Y = 0.24                               # décalage des bras vers l'arrière de la tête                              # tête : hauteur du corps


def mat_rack(name, c_tooth, c_gap, period):
    """Crémaillère : bandes alternées le long de l'axe y de l'objet (texture, pas de relief : pas de contours)."""
    m = mat(name, (1, 1, 1))
    nt = m.node_tree
    n = nt.nodes
    mix = next(x for x in n if x.bl_idname == "ShaderNodeMix")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    k = n.new("ShaderNodeMath"); k.operation = "MULTIPLY"; k.inputs[1].default_value = 1.0 / period
    nt.links.new(sep.outputs["Y"], k.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; nt.links.new(k.outputs[0], fr.inputs[0])
    gt = n.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.55
    nt.links.new(fr.outputs[0], gt.inputs[0])
    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"
    col.inputs[6].default_value = (*c_tooth, 1); col.inputs[7].default_value = (*c_gap, 1)
    nt.links.new(gt.outputs[0], col.inputs[0])
    nt.links.new(col.outputs[2], mix.inputs[6])
    return m


def mats():
    return dict(
        rail=mat("rail", P["dark"]), rack=mat_rack("rack", P["grey"], P["dark"], 0.11),
        steel=mat("steel", P["grey"]), light=mat("light", P["white"]), dark=mat("dark", P["dark"]),
        yellow=mat("yellow", P["drill_yellow"]), body=mat("body", P["drill_body"]),
        copper=mat("copper", P["orange"]), red=mat("red", P["red"]), bit=mat("bit", P["drill_auger"]),
    )


# --- cadre ------------------------------------------------------------------------------------------------------

def frame_parts(m):
    """Cadre (orienté nord) ; renvoie la liste des objets créés."""
    objs = []
    for sx in (-1, 1):
        x = sx * RAIL_X
        objs.append(box((x, 0, RAIL_H / 2), (RAIL_W, RAIL_LEN, RAIL_H), m["rail"], 0.015))
        o = box((x - sx * 0.02, 0, RAIL_H + 0.02), (RAIL_W * 0.55, RAIL_LEN * 0.98, 0.04), m["rack"])
        objs.append(o)
        objs.append(box((x + sx * (RAIL_W / 2 + 0.03), 0, RAIL_H * 0.55), (0.06, RAIL_LEN * 0.96, RAIL_H * 0.8),
                        m["steel"], 0.01))                                      # plat d'acier côté extérieur
        # montant et coude de la poutre jaune au-dessus du rail
        objs.append(box((x, BEAM_Y, (RAIL_H + BEAM_Z) / 2), (0.2, 0.2, BEAM_Z - RAIL_H), m["yellow"], 0.015))
    objs.append(box((0, BEAM_Y, BEAM_Z), (2 * RAIL_X + 0.2, 0.2, 0.16), m["yellow"], 0.015))   # poutre
    objs.append(cyl((-0.38, BEAM_Y, BEAM_Z + 0.2), 0.16, 0.34, m["dark"], verts=16, rot=(0, 90, 0)))   # moteur
    objs.append(cyl((-0.17, BEAM_Y, BEAM_Z + 0.2), 0.1, 0.08, m["yellow"], verts=16, rot=(0, 90, 0)))
    o = box((0.55, BEAM_Y - 0.1, BEAM_Z + 0.22), (0.38, 0.34, 0.24), m["steel"], 0.015, rot_x=-20)   # trémie
    objs.append(o)
    objs.append(box((0.55, BEAM_Y - 0.12, BEAM_Z + 0.35), (0.28, 0.24, 0.02), m["dark"], rot_x=-20))
    return objs


def drum(phase, m):
    """Tambour de sortie : cylindre à ailettes, axe x, derrière la poutre ; tourne avec la phase."""
    objs = [cyl((-0.06, BEAM_Y + 0.25, BEAM_Z + 0.05), 0.17, 0.42, m["steel"], verts=16, rot=(0, 90, 0))]
    for k in range(6):
        a = phase * 60 + k * 60
        objs.append(box((-0.06, BEAM_Y + 0.25, BEAM_Z + 0.05), (0.44, 0.05, 0.42), m["dark"], rot_x=a))
    return objs


# --- tête -------------------------------------------------------------------------------------------------------

def sweep(points, r, m, verts=8):
    """Tube d'un seul maillage le long d'une polyligne (tuyau)."""
    import bpy, bmesh
    pts = [np.array(p, float) for p in points]
    bm = bmesh.new()
    rings = []
    for i, p in enumerate(pts):
        d = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        d /= np.linalg.norm(d)
        a = np.cross(d, [0, 0, 1]) if abs(d[2]) < 0.9 else np.cross(d, [1, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        rings.append([bm.verts.new(tuple(p + r * (math.cos(t) * a + math.sin(t) * b)))
                      for t in np.linspace(0, 2 * math.pi, verts, endpoint=False)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(verts):
            bm.faces.new((r0[k], r0[(k + 1) % verts], r1[(k + 1) % verts], r1[k]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("tube"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("tube", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m)
    return o


def drill_bit(z0, z1, phase, m, thread_m, r=0.2, turns=3.0, n=60):
    """Foret à vis : cône et filet hélicoïdal d'un seul ruban, qui tourne avec la phase."""
    import bpy, bmesh
    objs = []
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=r * 0.6, radius2=0.03, depth=z1 - z0,
                                    location=(0, 0, (z0 + z1) / 2), rotation=(math.pi, 0, 0))
    o = bpy.context.object; o.data.materials.append(m); objs.append(o)
    bm = bmesh.new()
    vs = []
    a0 = -phase * 2 * math.pi
    for k in range(n + 1):
        u = k / n
        a = a0 + u * turns * 2 * math.pi
        z = z1 - (z1 - z0) * u
        rad = r * (1 - 0.8 * u)
        vs.append((bm.verts.new((0.04 * math.cos(a), 0.04 * math.sin(a), z)),
                   bm.verts.new((rad * math.cos(a), rad * math.sin(a), z - 0.03))))
    for (a, b), (c, d) in zip(vs, vs[1:]):
        bm.faces.new((a, b, d, c))
    me = bpy.data.meshes.new("vis"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("vis", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(thread_m)
    mod = o.modifiers.new("epaisseur", "SOLIDIFY"); mod.thickness = 0.035
    objs.append(o)
    return objs


def head_parts(phase, m, near_only=False):
    """Tête (bras vers les rails en x = ±RAIL_X). `near_only` : seulement la pince du bras de devant (y < 0)
    une fois tournée, pour la pièce avant de la tête horizontale (voir head_front)."""
    objs = []
    z = BODY_Z
    if not near_only:
        objs.append(box((0, 0, z), (0.72, 0.46, 1.0), m["body"], 0.04))                # corps, debout
        objs.append(box((0, -0.235, z + 0.27), (0.6, 0.03, 0.36), m["copper"], 0.01))  # plaque cuivre (face avant)
        objs.append(cyl((0.04, 0.04, z + 0.6), 0.17, 0.2, m["dark"], verts=16))         # moteur
        objs.append(cyl((0.04, 0.04, z + 0.72), 0.11, 0.04, m["steel"], verts=16))
        objs += drill_bit(-0.6, z - 0.5, phase, m["steel"], m["bit"], r=0.38)
        objs.append(sweep([(0.37, -0.1, z - 0.15), (0.58, -0.2, z - 0.55), (0.52, -0.1, z - 0.95),
                           (0.3, 0.05, z - 1.15)], 0.06, m["red"]))                   # tuyau, sur le côté
    for sx in (-1, 1):
        if near_only and sx == -1:                         # x + : devant une fois tourné de -90° (tête horizontale)
            continue
        ay = ARM_Y                                         # bras décalés vers l'arrière : ils ne cachent pas le foret
        objs.append(rod((sx * 0.38, ay, z + 0.1), (sx * (RAIL_X - 0.12), ay, RAIL_H + 0.3), 0.09, m["steel"], verts=8))
        objs.append(rod((sx * 0.38, ay + 0.12, z - 0.25), (sx * (RAIL_X - 0.12), ay + 0.1, RAIL_H + 0.2), 0.05, m["dark"], verts=8))
        objs.append(box((sx * RAIL_X, ay, RAIL_H + 0.17), (0.3, 0.42, 0.22), m["dark"], 0.02))   # pince sur le rail
    return objs


# --- rendu ------------------------------------------------------------------------------------------------------

def turn(objs, yaw):
    import bpy
    from mathutils import Matrix
    bpy.context.view_layer.update()
    rot = Matrix.Rotation(math.radians(yaw), 4, "Z")
    for o in objs:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world


def scene(what, direction="N", phase=0.0):
    """Construit une partie : « cadre », « avant » (pièces du cadre devant la tête), « sortie », « tête »,
    « tête-avant » ; `direction` donne l'orientation (tête : N/S verticale, E/W horizontale)."""
    import bpy
    reset()
    m = mats()
    if what in ("cadre", "avant"):
        objs = frame_parts(m)
        turn(objs, YAW[direction])
        if what == "avant":
            bpy.context.view_layer.update()
            for o in list(objs):
                ys = [(o.matrix_world @ v.co).y for v in o.data.vertices]
                if max(ys) > -0.75:                                # garde ce qui est entièrement devant
                    bpy.data.objects.remove(o)
    elif what == "sortie":
        turn(drum(phase, m), YAW[direction])
    elif what in ("tête", "tête-avant"):
        yaw = 0 if direction in ("N", "S") else -90
        turn(head_parts(phase, m, near_only=(what == "tête-avant")), yaw)


def render_part(what, direction, phase, cell, out, shadow_cell=None):
    path = os.path.join(out, "_emd.png")
    build = lambda: scene(what, direction, phase)
    build()
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE)
    sprite = crop_centered(load(path), cell[0], px(cell[1]))
    if shadow_cell is None:
        return sprite, None
    sh = render_shadow(build, path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR)
    return sprite, crop_centered(sh, shadow_cell[0], px(shadow_cell[1]))


def write(out, file, im):
    cv2.imwrite(entity_path(out, NAME, file), im)


def build_frames(out):
    for d in YAW:
        sprite, shadow = render_part("cadre", d, 0.0, BASE[d], out, BASE_SHADOW[d])
        write(out, f"{NAME}-{d}.png", sprite)
        write(out, f"{NAME}-{d}-shadow.png", shadow)
        if d in FRONT:
            write(out, f"{NAME}-{d}-front.png", render_part("avant", d, 0.0, FRONT[d], out)[0])
        print("OK cadre", d, flush=True)


def build_heads(out, preview=False):
    for kind, d in (("vertical", "N"), ("horizontal", "E")):
        n = 1 if preview else HEAD_FRAMES
        frames = [render_part("tête", d, i / HEAD_FRAMES, HEAD[kind], out)[0] for i in range(n)]
        frames = frames * HEAD_FRAMES if preview else frames
        file = f"{NAME}.png" if kind == "vertical" else f"{NAME}-horizontal.png"
        write(out, file, sheet(frames, HEAD_COLUMNS))
        n = 1 if preview else HEAD_SHADOW_FRAMES
        shadows = [render_part("tête", d, i / HEAD_SHADOW_FRAMES, HEAD[kind], out, HEAD_SHADOW[kind])[1] for i in range(n)]
        shadows = shadows * HEAD_SHADOW_FRAMES if preview else shadows
        write(out, file.replace(".png", "-shadow.png"), sheet(shadows, HEAD_SHADOW_COLUMNS))
        if kind == "horizontal":
            n = 1 if preview else HEAD_FRAMES
            fronts = [render_part("tête-avant", d, i / HEAD_FRAMES, HEAD_FRONT, out)[0] for i in range(n)]
            fronts = fronts * HEAD_FRAMES if preview else fronts
            write(out, f"{NAME}-horizontal-front.png", sheet(fronts, HEAD_COLUMNS))
        print("OK tête", kind, flush=True)


def build_outputs(out):
    for d in YAW:
        frames = [render_part("sortie", d, i / OUTPUT_FRAMES, OUTPUT[d], out)[0] for i in range(OUTPUT_FRAMES)]
        write(out, f"{NAME}-{d}-output.png", sheet(frames, OUTPUT_FRAMES))
    print("OK sorties", flush=True)


def build_integrations(out):
    """Plaques d'intégration (terre remuée sous la foreuse) : la forme de l'original en aplat de sa teinte,
    semi-transparent, sans contour, comme les taches au sol des décorations (terrain/decoratives.render_decal)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "terrain"))
    from decoratives import FACTORIO_DATA, render_decal
    for d in YAW:
        file = f"{NAME}-{d}-integration.png"
        orig = cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity", NAME, file), cv2.IMREAD_UNCHANGED)
        write(out, file, render_decal(orig))
    print("OK intégrations", flush=True)


def build_icon(out):
    def whole():
        import bpy
        reset()
        m = mats()
        frame_parts(m)
        head_parts(0.0, m)
        drum(0.0, m)
    save_icon(out, NAME, whole)


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "electric_drill_out"
    which = (args[1] if len(args) > 1 else "toutes")
    parts = ["cadres", "tetes", "sorties", "integrations", "icone"] if which == "toutes" else which.split(",")
    os.makedirs(out, exist_ok=True)
    if "cadres" in parts: build_frames(out)
    if "tetes" in parts: build_heads(out, preview)
    if "sorties" in parts: build_outputs(out)
    if "integrations" in parts: build_integrations(out)
    if "icone" in parts: build_icon(out)
