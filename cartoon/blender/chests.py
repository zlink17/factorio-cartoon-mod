"""Coffres en bois, en fer et en acier (wooden-chest, iron-chest, steel-chest) : sprite, ombre, icône.

Usage : python cartoon/blender/chests.py <dossier_sortie> [coffre[,coffre...]|tous]
        coffre = bois, fer, acier

Écrit, aux chemins de l'original (base/entity/<coffre>/ et base/icons/) :
  <coffre>.png           le coffre, rendu à 64 px par case et découpé au cadre du prototype
  <coffre>-shadow.png    son ombre portée, noire unie (le jeu la rend semi-transparente)
  <coffre>.png (icône)   64 px + mipmaps
Les restes sont laissés d'origine (lot 3.9). Le coffre en fer sert aussi à simple-entity-with-owner, le coffre en
acier à bottomless-chest et simple-entity-with-force (mêmes fichiers).

Les trois coffres de l'original ont la même silhouette, qui ne suit pas un cube : face avant de 34 px de haut, dessus
de 35 px. Le modèle est donc une caisse haute et peu profonde (`H`, entre `Y_FRONT` et `Y_BACK`), posée vers l'avant
de sa case, qui donne ces proportions avec la caméra des bâtiments.
  bois  : cadre de planches claires autour du dessus et de la face avant, planches en retrait (joints peints par
          une texture, pas en relief : sinon un contour par planche) ;
  fer   : caisse de fer rouillé sombre sur un socle, couvercle en tronc de pyramide gris rosé, loquet devant ;
  acier : tôle nervurée (nervures peintes : claires dessus, sombres devant), cadre et coins rouille, poignée laiton.
"""
import os, sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import box, crop_centered, entity_path, hull, load, mat, render_scene, render_shadow, reset, save_icon

P = S.PALETTE
PX_PER_TILE = 64
CANVAS = 256
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.02                             # petit objet, beaucoup d'arêtes : contour un peu plus fin

# silhouette commune (cases), calée sur les trois originaux : bas de la face avant, haut de la face avant et arrière
# du dessus à -0,484, +0,047 et +0,6 case au-dessus du centre de la case
Y_FRONT, Y_BACK, H = -0.56, 0.075, 1.06

# cadres de l'original (taille, décalage en px = shift x 64) : sprite, puis ombre
CHESTS = {
    "bois": ("wooden-chest", ((62, 72), (1.0, -4.0)), ((104, 40), (20.0, 13.0))),
    "fer": ("iron-chest", ((66, 76), (-1.0, -1.0)), ((110, 50), (21.0, 12.0))),
    "acier": ("steel-chest", ((64, 80), (-0.5, -1.0)), ((110, 46), (24.5, 16.0))),
}


def mat_face(name, base, uv, stripes=None, rects=()):
    """Comme lib.mat (trois tons selon l'orientation de la face), avec un motif peint sur une face plane, en
    coordonnées du monde (`uv` = deux axes parmi "X", "Y", "Z", ceux du plan de la face) :
      stripes = (axe "u" ou "v", période, fraction, couleur, phase) : bandes de `couleur` sur une fraction de
                chaque période (joints de planches, nervures) ;
      rects   = [((u0, u1, v0, v1), couleur), ...] appliqués dans l'ordre : hors du rectangle, la couleur
                remplace la précédente (cadre, joint autour du cadre).
    Pas de relief, donc pas de contour par planche ou par nervure."""
    m = mat(name, (1, 1, 1))
    nt = m.node_tree
    n = nt.nodes
    mix = next(x for x in n if x.bl_idname == "ShaderNodeMix")
    geo = n.new("ShaderNodeNewGeometry")
    pos = n.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], pos.inputs[0])
    u, v = pos.outputs[uv[0]], pos.outputs[uv[1]]

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

    def blend(fac, under, color):
        node = n.new("ShaderNodeMix"); node.data_type = "RGBA"
        nt.links.new(fac, node.inputs[0])
        if isinstance(under, tuple):
            node.inputs[6].default_value = (*under, 1)
        else:
            nt.links.new(under, node.inputs[6])
        node.inputs[7].default_value = (*color, 1)
        return node.outputs[2]

    col = base
    if stripes:
        axis, pitch, ratio, color, phase = stripes
        t = op("FRACT", op("ADD", op("DIVIDE", u if axis == "u" else v, pitch), phase))
        col = blend(op("LESS_THAN", t, ratio), col, color)
    for (u0, u1, v0, v1), color in rects:
        outside = op("MAXIMUM", op("MAXIMUM", op("LESS_THAN", u, u0), op("GREATER_THAN", u, u1)),
                     op("MAXIMUM", op("LESS_THAN", v, v0), op("GREATER_THAN", v, v1)))
        col = blend(outside, col, color)
    if isinstance(col, tuple):
        mix.inputs[6].default_value = (*col, 1)
    else:
        nt.links.new(col, mix.inputs[6])
    return m


def paint(o, top, front, side):
    """Un matériau par face d'un objet, selon son orientation : dessus, face avant, autres faces."""
    me = o.data
    me.materials.clear()
    for m in (top, front, side):
        me.materials.append(m)
    for p in me.polygons:
        p.material_index = 0 if p.normal.z > 0.5 else 1 if p.normal.y < -0.5 else 2
    return o


def beam(x0, x1, y0, y1, z0, z1, m):
    """Pavé entre deux coins (cases)."""
    return box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), m)


def build_wood():
    """Une seule caisse : cadre clair peint autour du dessus et de la face avant, planches (plus sombres devant,
    comme l'original, pour lire le volume)."""
    reset()
    w, t, j = 0.47, 0.1, 0.025                # demi-largeur, largeur du cadre, joint entre cadre et planches
    yf, yb = Y_FRONT, Y_BACK
    frame, wood, gap = P["chest_wood_frame"], P["chest_wood"], P["chest_wood_gap"]
    zb, zt = 0.12, H - 0.13                   # traverses du bas et du haut de la face avant
    n = 4                                     # planches par face
    top = mat_face("wood_top", wood, "XY", ("v", (yb - yf - 2 * t) / n, 0.22, gap, 0.5 - (yf + t) * n / (yb - yf - 2 * t)),
                   [((-w + t, w - t, yf + t, yb - t), gap), ((-w + t - j, w - t + j, yf + t - j, yb - t + j), frame)])
    front = mat_face("wood_front", P["chest_wood_dark"], "XZ", ("v", (zt - zb) / n, 0.22, gap, 0.5 - zb * n / (zt - zb)),
                     [((-w + t, w - t, zb, zt), gap), ((-w + t - j, w - t + j, zb - j, zt + j), frame)])
    side = mat("wood_side", frame)
    paint(beam(-w, w, yf, yb, 0, H, side), top, front, side)


def build_iron():
    """Caisse de fer sombre sur un socle à rivets, couvercle gris rosé à pans coupés, plaque et loquet."""
    reset()
    body = mat("iron_body", P["chest_iron_body"])
    lid = mat("iron_lid", P["chest_iron_lid"])
    plate = mat("iron_plate", P["chest_iron_plate"])
    dark = mat("iron_dark", P["dark"])
    light = mat("iron_light", P["white"])
    yf, yb = Y_FRONT, Y_BACK
    zl = 0.9                                                        # bas du couvercle
    straps = mat_face("iron_straps", P["chest_iron_body"], "XZ", None, [((-0.4, 0.4, -1, 2), P["chest_iron_plate"])])
    paint(beam(-0.47, 0.47, yf, yb, 0, zl, body), body, straps, body)   # caisse, montants clairs devant
    rivets = mat_face("iron_rivets", P["dark"], "XZ", ("u", 0.16, 0.34, P["chest_iron_lid"], 0.33),
                      [((-1, 1, 0.05, 0.14), P["dark"])])
    paint(beam(-0.495, 0.495, yf - 0.02, yb, 0, 0.19, dark), dark, rivets, dark)   # socle à rivets
    hull([(-0.5, yf - 0.02, zl), (0.5, yf - 0.02, zl), (0.5, yb, zl), (-0.5, yb, zl)],          # couvercle : pans
         [(-0.4, yf, H), (0.4, yf, H), (0.4, yb - 0.04, H), (-0.4, yb - 0.04, H)], lid)       # coupés sur les côtés
    beam(-0.33, 0.33, yf + 0.09, yb - 0.12, H, H + 0.015, plate)    # plaque du couvercle
    beam(-0.14, 0.14, yf + 0.04, yf + 0.2, H, H + 0.04, dark)       # loquet : platine sombre, poignée claire
    beam(-0.11, 0.11, yf + 0.06, yf + 0.13, H + 0.04, H + 0.1, light)


def build_steel():
    """Une seule caisse de tôle nervurée (claire dessus, sombre devant), cadre peint (gris dessus, rouille devant),
    coins rouille en saillie, poignée laiton."""
    reset()
    w, t = 0.495, 0.08
    yf, yb = Y_FRONT, Y_BACK
    rust, rib = P["chest_steel_frame"], P["chest_steel_rib"]
    zb, zt = 0.1, H - 0.15
    top = mat_face("steel_top", P["chest_steel"], "XY", ("u", 0.14, 0.42, rib, 0.2),
                   [((-w + t, w - t, yf + t, yb - t), P["chest_steel_rim"])])
    front = mat_face("steel_front", P["chest_steel_front"], "XZ", ("u", 0.14, 0.3, P["dark"], 0.15),
                     [((-w + t, w - t, zb, zt), rust)])
    side = mat("steel_side", rust)
    paint(beam(-w, w, yf, yb, 0, H, side), top, front, side)
    caps = mat("steel_caps", rust)
    c = 0.13
    for x0 in (-w - 0.005, w - c + 0.005):                          # coins du dessus, en saillie
        for y0 in (yf - 0.005, yb - c + 0.005):
            beam(x0, x0 + c, y0, y0 + c, H, H + 0.04, caps)
    beam(-0.13, 0.13, yf - 0.04, yf, zt - 0.32, zt - 0.14, mat("steel_brass", P["yellow"]))   # poignée


BUILDERS = {"bois": build_wood, "fer": build_iron, "acier": build_steel}


def render(out, key):
    name, sprite_cell, shadow_cell = CHESTS[key]
    build = BUILDERS[key]
    path = os.path.join(out, f"_{name}.png")
    build()
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE)
    cv2.imwrite(entity_path(out, name), crop_centered(load(path), *sprite_cell))
    shadow = render_shadow(build, path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR)
    cv2.imwrite(entity_path(out, name, f"{name}-shadow.png"), crop_centered(shadow, *shadow_cell))
    save_icon(out, name, build)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "chests_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    keys = list(CHESTS) if which == "tous" else which.split(",")
    os.makedirs(out, exist_ok=True)
    for k in keys:
        render(out, k)
        print("OK", CHESTS[k][0])
