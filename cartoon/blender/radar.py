"""Radar : planche des 64 orientations de l'antenne, ombres, plaque d'intégration, icône.

Usage : python cartoon/blender/radar.py <dossier_sortie> [--apercu]
        --apercu : 8 orientations seulement, répétées (réglages)

Écrit, aux chemins de l'original (base/entity/radar/ et base/icons/) :
  radar.png              64 images (8 par ligne) : l'antenne tourne d'un tour, dans le sens horaire vue de dessus,
                         en partant du nord (image 0 : antenne au fond, creux vers nous), comme l'original
  radar-shadow.png       64 ombres, noires unies
  radar-integration.png  terre tassée sous les pieds : forme de l'original en aplat semi-transparent
  radar.png (icône)      64 px + mipmaps
Laissés d'origine : le reflet dans l'eau (fichier technique) et les restes (lot 3.9).

Le radar (3 x 3 cases) : quatre pieds en treillis (poutres claires, ajours peints) qui portent une plateforme
octogonale sombre ; tourelle ronde au centre, tambour à l'arrière droit ; sur la tourelle, un mât qui porte
l'antenne : panneau courbe clair à bord cuivre, creux tourné vers l'axe, bras blanc par-dessus le mât.
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, cyl, load, mat, render_scene, render_shadow, reset, rod, save_icon, sheet, target

P = S.PALETTE
NAME = "radar"
PX_PER_TILE = 64
CANVAS = 576                                    # l'ombre (336 px, décalée de 78) doit tenir dedans
N_DIRS, COLUMNS = 64, 8
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.022
SPRITE = ((196, 254), (2.0, -32.0))          # cadres de l'original (taille, décalage en px = shift x 64)
SHADOW = ((336, 170), (78.0, 12.0))

DIMS = dict(
    zp=0.95,            # dessus de la plateforme
    rp=0.95,            # rayon de la plateforme
    leg=1.45,           # écart des pieds au sol (demi-côté)
    rt=0.55, ht=0.3,    # tourelle
    zd=2.85, hd=1.0,    # antenne : hauteur du centre, hauteur du panneau
    Rd=1.3, span=100,   # rayon de courbure, ouverture (degrés)
    dd=0.15,            # distance de l'antenne à l'axe (l'original tourne presque sur place)
    down=0.17,          # tout le dessin plus bas à l'écran (mesuré sur les pieds de l'original)
)


def mat_truss(name, rgb, hole):
    """Poutre en treillis : ajours triangulaires peints (couleur `hole`) le long de la poutre (axe x de l'objet)."""
    m = mat(name, (1, 1, 1))
    nt = m.node_tree
    n = nt.nodes
    mix = next(x for x in n if x.bl_idname == "ShaderNodeMix")
    tc = n.new("ShaderNodeTexCoord")
    sep = n.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def op(kind, a, b=None):
        node = n.new("ShaderNodeMath"); node.operation = kind
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                node.inputs[i].default_value = x
            else:
                nt.links.new(x, node.inputs[i])
        return node.outputs[0]

    # dents de scie le long de x, comparées à la position en travers (y ou z, le plus grand) : triangles alternés
    t = op("FRACT", op("MULTIPLY", sep.outputs["X"], 4.0))
    saw = op("ABSOLUTE", op("SUBTRACT", op("MULTIPLY", t, 2.0), 1.0))
    across = op("ADD", op("MULTIPLY", sep.outputs["Y"], 1.0), op("MULTIPLY", sep.outputs["Z"], 1.0))
    a = op("ABSOLUTE", across)
    inside = op("MULTIPLY", op("LESS_THAN", a, op("MULTIPLY", saw, 0.32)), op("LESS_THAN", a, 0.3))
    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"
    nt.links.new(inside, col.inputs[0])
    col.inputs[6].default_value = (*rgb, 1)
    col.inputs[7].default_value = (*hole, 1)
    nt.links.new(col.outputs[2], mix.inputs[6])
    return m


def beam(p0, p1, w, t, m):
    """Poutre plate (largeur `w`, épaisseur `t`) entre deux points, sa largeur à l'horizontale."""
    import bpy
    from mathutils import Vector
    a, b = Vector(p0), Vector(p1)
    o = box(tuple((a + b) / 2), ((b - a).length / 2 * 2, w, t), m)
    d = (b - a).normalized()
    o.rotation_euler = d.to_track_quat("X", "Z").to_euler()
    return o


def dish(theta, d, m_dish, m_rim):
    """Panneau courbe de l'antenne : portion de cylindre vertical, côté concave tourné vers l'axe."""
    import bpy, bmesh
    Rd, span, hd, zd, dd = d["Rd"], d["span"], d["hd"], d["zd"], d["dd"]
    bm = bmesh.new()
    n = 16
    rows = []
    for z in (-hd / 2, hd / 2):
        rows.append([bm.verts.new((Rd * math.sin(math.radians(a)), Rd * math.cos(math.radians(a)), z))
                     for a in np.linspace(-span / 2, span / 2, n)])
    for k in range(n - 1):
        bm.faces.new((rows[0][k], rows[0][k + 1], rows[1][k + 1], rows[1][k]))
    me = bpy.data.meshes.new("dish")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("dish", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(m_dish)
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.05
    # panneau à `dd` de l'axe dans la direction theta, creux tourné vers l'axe (centre de courbure de l'autre côté)
    ux, uy = math.sin(theta), math.cos(theta)
    cx, cy = (dd - Rd) * ux, (dd - Rd) * uy
    o.location = (cx, cy, zd)
    o.rotation_euler = (0, 0, -theta)
    for z in (-hd / 2, hd / 2):                        # bords cuivre en haut et en bas
        pts = [(cx + Rd * math.sin(theta + math.radians(a)), cy + Rd * math.cos(theta + math.radians(a)), zd + z)
               for a in np.linspace(-span / 2, span / 2, n)]
        for p, q in zip(pts, pts[1:]):
            rod(p, q, 0.035, m_rim, verts=6)
    return o


def build(i=0, d=None):
    """Scène du radar, antenne dans l'orientation `i` (0..63)."""
    import bpy
    reset()
    d = d or DIMS
    theta = 2 * math.pi * i / N_DIRS                     # angle de l'antenne depuis le nord, sens horaire
    truss = mat_truss("truss", P["radar_truss"], P["dark"])
    deck = mat("deck", P["radar_deck"])
    turret = mat("turret", P["boiler_body"])
    dark = mat("dark", P["dark"])
    zp, rp, L = d["zp"], d["rp"], d["leg"]
    for sx in (-1, 1):                                   # pieds : deux poutres en A par coin
        for sy in (-1, 1):
            top = (sx * rp * 0.7, sy * rp * 0.7, zp - 0.1)
            beam((sx * L, sy * L * 0.7, 0.0), top, 0.3, 0.08, truss)
            beam((sx * L * 0.7, sy * L, 0.0), top, 0.3, 0.08, truss)
            box((sx * L * 0.88, sy * L * 0.88, 0.04), (0.45, 0.45, 0.08), dark)    # semelle
    cyl((0, 0, zp - 0.12), rp, 0.24, deck, verts=8)      # plateforme
    for sx in (-1, 1):                                   # caissons sombres sur les côtés
        box((sx * (rp + 0.12), 0.05, zp + 0.1), (0.45, 1.3, 0.75), dark, bevel=0.03)
    beam((-L, -L * 0.75, 0.45), (L, -L * 0.75, 0.45), 0.2, 0.08, truss)       # traverse avant
    cyl((0.62, 0.55, zp + 0.3), 0.33, 0.6, dark, verts=20)                     # tambour arrière droit
    cyl((0.62, 0.55, zp + 0.62), 0.25, 0.04, mat("cap", P["iron"]), verts=20)
    cyl((0, 0, zp + d["ht"] / 2), d["rt"], d["ht"], turret, verts=28)          # tourelle
    cyl((0, 0, zp + d["ht"] + 0.03), d["rt"] * 0.8, 0.06, mat("ring", P["brown"]), verts=28)
    ux, uy = math.sin(theta), math.cos(theta)
    mast = mat("mast", P["iron"])
    zt = zp + d["ht"]
    box((0, 0, (zt + d["zd"]) / 2), (0.2, 0.2, d["zd"] - zt), mast, rot_z=-math.degrees(theta))   # mât
    box((ux * d["dd"] / 2, uy * d["dd"] / 2, d["zd"]), (0.5, 0.2, 0.3), mast, rot_z=-math.degrees(theta))
    dish(theta, d, mat("dish", P["radar_dish"]), mat("rim", P["brown"]))
    # bras blanc : du panneau, par-dessus le mât, vers l'autre côté
    rod((ux * d["dd"], uy * d["dd"], d["zd"]), (-ux * 0.75, -uy * 0.75, d["zd"] + 0.25), 0.03,
        mat("feed", P["white"]), verts=8)
    bpy.context.view_layer.update()


def camera_shift(d=None):
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


def write(out, preview=False):
    path = os.path.join(out, "_radar.png")
    idx = range(0, N_DIRS, 8) if preview else range(N_DIRS)
    sprites, shadows = [], []
    for i in idx:
        build(i)
        render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
        sprites.append(crop_centered(load(path), *SPRITE))
        sh = render_shadow(lambda: build(i), path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR, shift_y=camera_shift())
        shadows.append(crop_centered(sh, *SHADOW))
    if preview:
        sprites, shadows = [x for x in sprites for _ in range(8)], [x for x in shadows for _ in range(8)]
    cv2.imwrite(target(out, "base/entity/radar/radar.png"), sheet(sprites, COLUMNS))
    cv2.imwrite(target(out, "base/entity/radar/radar-shadow.png"), sheet(shadows, COLUMNS))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "terrain"))
    from decoratives import FACTORIO_DATA, render_decal
    orig = cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity/radar/radar-integration.png"),
                      cv2.IMREAD_UNCHANGED)
    cv2.imwrite(target(out, "base/entity/radar/radar-integration.png"), render_decal(orig))
    save_icon(out, NAME, lambda: build(6))


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "radar_out"
    os.makedirs(out, exist_ok=True)
    write(out, preview)
    print("OK radar", flush=True)
