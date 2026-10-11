"""Chaudière (boiler) : sprites des 4 directions, ombres, flammes, pièce « patch » de l'est, icône.

Usage : python cartoon/blender/boiler.py <dossier_sortie> [direction[,direction...]|toutes]
        direction = N, E, S, W

Écrit, aux chemins de l'original (base/entity/boiler/ et base/icons/) :
  boiler-<D>-idle.png     la chaudière, au cadre du prototype de la direction D
  boiler-<D>-shadow.png   son ombre portée, noire unie
  boiler-<D>-fire.png     64 images de flammes (8 par ligne), dessinées en aplats dans la grille du foyer
  boiler-E-patch.png      bande de notre sprite de l'est que le jeu redessine par-dessus le tuyau raccordé
  boiler.png (icône)      64 px + mipmaps
Les halos lumineux (boiler-<D>-light) et les restes sont laissés d'origine.

La chaudière (3 x 2 cases ; nord = sortie de vapeur au fond) : corps gris-vert en voûte (pavé coiffé d'un demi-
cylindre) sur un socle sombre, grille du foyer sur la face avant, réservoirs latéraux qui portent les raccords d'eau
(à gauche et à droite, sur la rangée avant, comme les connexions de fluide du prototype), dôme de vapeur au fond,
cheminée à l'arrière gauche (au point d'où le jeu fait sortir la fumée), tuyauterie cuivre. Modèle construit vers le
nord puis tourné pour chaque direction (comme la foreuse à charbon).
"""
import math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
import pipe as PIPE
from lib import (box, crop_centered, cyl, entity_path, load, mat, render_scene, render_shadow, reset,
                 save_icon)

P = S.PALETTE
NAME = "boiler"
PX_PER_TILE = 64
CANVAS = 512
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.022
YAW = {"N": 0, "E": -90, "S": 180, "W": 90}   # rotation du modèle (degrés, autour de z)
# cadres de l'original (taille, décalage en px = shift x 64) : sprite, ombre, flammes
FRAMES = {
    "N": (((269, 221), (-2.5, 10.5)), ((274, 164), (41.0, 18.0)), ((26, 26), (0.0, -17.0))),
    "E": (((216, 301), (-6.0, 2.5)), ((184, 194), (60.0, 19.0)), ((28, 28), (-19.0, -44.0))),
    "S": (((260, 192), (8.0, 26.0)), ((311, 131), (59.5, 31.5)), ((26, 16), (-2.0, -53.0))),
    "W": (((196, 273), (3.0, 15.5)), ((206, 218), (39.0, 13.0)), ((30, 29), (26.0, -46.5))),
}
PATCH = ((6, 36), (67.0, -27.0))                 # boiler-E-patch : cadre et décalage
FIRE_FRAMES, FIRE_COLUMNS = 64, 8

# dimensions (cases), ajustées sur la silhouette de l'original dans les quatre directions
DIMS = dict(
    R=0.87, L=2.0, yc=0.0, zc=0.9,         # tambour central couché le long des 3 cases : rayon, longueur, centre (y, z)
    rt=0.5, yt=-0.425, zt=0.6,             # réservoirs latéraux (porteurs des raccords d'eau) : rayon, centre (y, z)
    down=0.33,                             # décalage de tout le dessin vers le bas de l'écran (comme les originaux)
    chim=2.625,                            # hauteur de la cheminée
    tank_end=1.08,                         # bout des réservoirs (le tuyau du raccord en sort jusqu'au bord, à 1,5)
)
# bornes de l'ajustement : au-delà, tambour et réservoirs se fondent en un seul cylindre et la silhouette en
# gradins (tambour haut au centre, réservoirs bas aux bouts) disparaît
BOUNDS = dict(L=(1.3, 2.0), rt=(0.3, 0.5), zt=(0.3, 0.6))


def within(d):
    return all(lo <= d[k] <= hi for k, (lo, hi) in BOUNDS.items())


def grate_place(direction, d=None):
    """Position de la grille du foyer sur le tambour (abscisse le long de l'axe, angle depuis le sommet vers
    l'avant) pour que, une fois le modèle tourné, elle se projette au centre du cadre des flammes de l'original.
    Les flammes du jeu ne sont dessinées que dans ce cadre, et l'original ne place pas sa grille au même endroit du
    tambour d'une direction à l'autre (comme les hublots de la foreuse humide) : on la place donc par direction."""
    d = d or DIMS
    (_, _), (fx, fy) = FRAMES[direction][2]
    target = np.array([fx, -fy]) / PX_PER_TILE                   # écran, en cases : x à droite, y vers le haut
    yaw = math.radians(YAW[direction])
    p = math.radians(S.PITCH_BUILDING_DEG)
    best = None
    for ang in np.arange(0, 61, 1.0):
        a = math.radians(ang)
        for x in np.arange(-0.6, 0.61, 0.01):
            y, z = d["yc"] - d["R"] * math.sin(a), d["zc"] + d["R"] * math.cos(a)
            xw, yw = x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw)
            scr = np.array([xw, yw * math.cos(p) + z * math.sin(p) - d["down"]])
            err = float(np.hypot(*(scr - target)))
            if best is None or err < best[0]:
                best = (err, float(x), float(ang))
    return best[1], best[2]


def _painted(name, base, alt, mask_fn):
    """Comme lib.mat (trois tons selon l'orientation de la face), couleur `alt` là où `mask_fn(op, xyz)` vaut 1,
    `base` ailleurs. xyz : coordonnées propres à l'objet (le motif tourne avec lui). Motif peint, sans relief :
    pas de contour (à cette taille, fentes ou rivets en relief se noient dans les contours)."""
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

    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"
    nt.links.new(mask_fn(op, (sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"])), col.inputs[0])
    col.inputs[6].default_value = (*base, 1)
    col.inputs[7].default_value = (*alt, 1)
    nt.links.new(col.outputs[2], mix.inputs[6])
    return m


def mat_grate():
    """Platine de la grille : cuivre, trois fentes de suie le long de sa hauteur."""
    def slots(op, xyz):
        x, _, z = xyz
        t = op("FRACT", op("MULTIPLY", op("ADD", x, 0.5), 3))                  # 3 colonnes sur la largeur
        return op("MULTIPLY", op("MULTIPLY", op("GREATER_THAN", t, 0.22), op("LESS_THAN", t, 0.78)),
                  op("LESS_THAN", op("ABSOLUTE", z), 0.36))
    return _painted("grate", P["brown"], P["furnace_soot"], slots)


def mat_riveted(name, base, rivet, rings, count, radius, size=0.035):
    """Tôle d'un cylindre (axe z de l'objet) avec des rangées de rivets clairs : `count` rivets sur le tour, à
    chaque abscisse de `rings`."""
    step = 2 * math.pi * radius / count                                       # écart entre rivets (cases)

    def dots(op, xyz):
        x, y, z = xyz
        u = op("FRACT", op("MULTIPLY", op("ARCTAN2", y, x), count / (2 * math.pi)))
        du = op("MULTIPLY", op("ABSOLUTE", op("SUBTRACT", u, 0.5)), step)
        on = op("LESS_THAN", du, size)
        ring = None
        for z0 in rings:
            r = op("LESS_THAN", op("ABSOLUTE", op("SUBTRACT", z, z0)), size)
            ring = r if ring is None else op("MAXIMUM", ring, r)
        return op("MULTIPLY", on, ring)
    return _painted(name, base, rivet, dots)


def tube(points, r, m):
    """Tuyau d'un seul maillage le long d'une ligne brisée (raccords sans contour), bouts fermés."""
    import bpy
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, q in zip(sp.points, points):
        p.co = (*q, 1)
    o = bpy.data.objects.new("tube", cu)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    o.data.materials.append(m)
    return o


def arc(x, yc, zc, rr, a0, a1, n=8):
    """Points d'un arc autour de l'axe du tambour (plan x constant), angles depuis le sommet vers l'avant."""
    return [(x, yc - rr * math.sin(math.radians(a)), zc + rr * math.cos(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


def build(direction="N", d=None):
    import bpy
    from mathutils import Matrix
    reset()
    d = d or DIMS
    body = mat("body", P["boiler_body"])
    dark = mat("dark", P["dark"])
    copper = mat("copper", P["brown"])
    R, L, yc, zc = d["R"], d["L"], d["yc"], d["zc"]
    rt, yt, zt = d["rt"], d["yt"], d["zt"]
    box((0, yc, 0.07), (2.6, 2 * R * 0.9, 0.14), dark)                        # socle
    drum = mat_riveted("drum", P["boiler_body"], P["white"], (-(L / 2 - 0.24), L / 2 - 0.24, 0.42), 20, R)
    cyl((0, yc, zc), R, L, drum, verts=40, rot=(0, 90, 0))                     # tambour riveté
    for s in (-1, 1):
        cyl((s * (L / 2 - 0.1), yc, zc), R + 0.03, 0.08, copper, verts=40, rot=(0, 90, 0))   # cerclages
        # réservoir latéral, raccord d'eau sur la rangée avant (y = -0,5 dans Blender) et sa bride
        te = d["tank_end"]
        cyl((s * (L / 2 + te) / 2, yt, zt), rt, te - L / 2 + 0.1, body, verts=32, rot=(0, 90, 0))
        cyl((s * te, yt, zt), rt + 0.03, 0.06, copper, verts=32, rot=(0, 90, 0))
    brass = mat("brass", P["yellow"])
    # trappe du foyer sur le tambour : cadre laiton, platine cuivre aux trois fentes peintes (dans le cadre des
    # flammes du jeu)
    gx, ga = grate_place(direction, d)
    a = math.radians(ga)
    for rr, size, m in ((R, (0.6, 0.06, 0.64), brass), (R + 0.03, (0.42, 0.06, 0.46), mat_grate())):
        box((gx, yc - rr * math.sin(a), zc + rr * math.cos(a)), size, m, rot_x=ga - 90)   # face selon le rayon
    # dôme de vapeur au fond (sortie vers le nord) : bride, soupape à chapeau laiton ; décalé à gauche pour ne
    # pas cacher la grille, vue par-dessus le tambour au sud
    xd, yd = -0.42, yc + R * 0.5
    zd = zc + R * math.sqrt(1 - 0.25)
    cyl((xd, yd, zd + 0.05), 0.28, 0.5, body, verts=24)
    cyl((xd, yd, zd + 0.3), 0.34, 0.07, copper, verts=24)
    cyl((xd, yd, zd + 0.42), 0.08, 0.2, body, verts=12)
    cyl((xd, yd, zd + 0.53), 0.12, 0.05, brass, verts=12)
    # porte du foyer en saillie, en bas devant : caisson sombre, porte cuivre, poignée laiton
    yf = yc - R - 0.02
    box((0, yf + 0.1, 0.32), (0.72, 0.3, 0.5), dark)
    box((0, yf - 0.06, 0.32), (0.5, 0.03, 0.36), copper)
    box((0, yf - 0.09, 0.38), (0.26, 0.03, 0.06), brass)
    # manomètre sur le réservoir droit : cadran clair cerclé de cuivre
    cyl((1.0, yt - rt - 0.01, zt + 0.12), 0.2, 0.05, copper, verts=20, rot=(90, 0, 0))
    cyl((1.0, yt - rt - 0.04, zt + 0.12), 0.15, 0.03, mat("dial", P["white"]), verts=20, rot=(90, 0, 0))
    # cheminée à l'arrière gauche (la fumée du jeu sort à son sommet)
    chim = mat("chimney", P["grey"])
    cyl((-1.12, 0.5, d["chim"] / 2), 0.13, d["chim"], chim, verts=16)
    cyl((-1.12, 0.5, d["chim"] - 0.05), 0.17, 0.1, copper, verts=16)
    cyl((0.55, yc, zc), R + 0.03, 0.08, copper, verts=40, rot=(0, 90, 0))      # cerclage du foyer
    # gros tuyaux cuivre : des réservoirs, autour du tambour par l'avant, jusqu'au dôme
    for s in (-1, 1):
        x = s * 0.66
        tube([(s * 0.9, yt - rt * 0.4, zt + rt * 0.9)] + arc(x, yc, zc, R + 0.09, 100, 0)
             + [(xd + s * 0.3, yd - 0.1, zc + R + 0.09), (xd + s * 0.24, yd, zd + 0.2)], 0.075, copper)
    tube([(-1.0, yt, zt + rt - 0.05), (-1.0, 0.3, 1.5), (-1.08, 0.45, 1.5)], 0.07, copper)   # vers la cheminée
    bpy.context.view_layer.update()          # matrices à jour (sinon le dernier objet perd son échelle)
    rot = Matrix.Rotation(math.radians(YAW[direction]), 4, "Z")
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world
    connectors(direction, d)


# raccords du prototype pour le nord (cases, y vers le sud comme dans le jeu) : position, direction vers l'extérieur
CONNECTIONS = [((-1, 0.5), (-1, 0)), ((1, 0.5), (1, 0)), ((0, -0.5), (0, -1))]   # eau, eau, vapeur
STUB = 0.75                                  # longueur de l'embout, du bord de la case vers l'intérieur


def connectors(direction, d=None):
    """Embouts des raccords : le tube et la bride du tuyau (pipe.py), au bord de la case, posés dans le repère du
    monde après la rotation : à l'écran, ils tombent exactement sur ceux d'un tuyau voisin. Le tuyau est dessiné
    `pipe.DIMS["yc"]` plus au sud que sa case, la chaudière `down` plus bas à l'écran : on décale l'embout d'autant."""
    d = d or DIMS
    pd, m = PIPE.DIMS, PIPE.mats()
    k = {"N": 0, "E": 1, "S": 2, "W": 3}[direction]
    dy = pd["yc"] + d["down"]                # le sol est étiré en y par render_scene : 1 case au sol = 1 case à l'écran
    for (px, py), (vx, vy) in CONNECTIONS:
        for _ in range(k):                   # quart de tour horaire dans le repère du jeu
            px, py, vx, vy = -py, px, -vy, vx
        out = np.array((vx, -vy, 0.0))       # repère de Blender : y vers le nord
        edge = np.array((px, -py + dy, pd["r"])) + out * 0.5
        PIPE.tube_path([tuple(edge), tuple(edge - out * STUB)], pd["r"], m["tube"])
        PIPE.flange(tuple(edge), (-vx, vy), pd, m)


def camera_shift(d=None):
    """Décalage de caméra (fraction du canevas) qui descend le dessin de `down` cases à l'écran."""
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


# --- flammes (procédural 2D) -------------------------------------------------------------------------------
FIRE_TONES = ("#c8402a", "#f08a2c", "#ffd44a")   # haut des fentes, milieu, cœur (comme le four)


def _srgb(lin):
    return np.array([(12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055) * 255 for v in lin])


def slot_mask(big, direction):
    """Fentes de la grille visibles dans le cadre des flammes : pixels de suie (à l'un des trois tons), dans le
    cadre. Renvoie le masque au format du cadre."""
    cell = crop_centered(big, *FRAMES[direction][2]).astype(np.float32)
    bgr = cell[..., 2::-1][..., ::-1]
    near = np.zeros(cell.shape[:2], bool)
    for tone in (S.SHADE_SIDE, S.SHADE_FRONT, S.SHADE_TOP):
        c = _srgb([v * tone for v in P["furnace_soot"]])[::-1]          # BGR
        near |= np.abs(cell[..., :3] - c).max(2) < 14
    return near & (cell[..., 3] > 200)


def fire_frame(mask, i):
    """Une image : chaque colonne de fente brûle du bas vers le haut, cœur jaune, flamme orange, haut rouge ; la
    hauteur des flammes ondule en boucle (FIRE_FRAMES images), décalée d'une colonne à l'autre."""
    h, w = mask.shape
    img = np.zeros((h, w, 4), np.uint8)
    tones = [np.array([int(c[k:k + 2], 16) for k in (5, 3, 1)]) for c in FIRE_TONES]
    t = 2 * math.pi * i / FIRE_FRAMES
    for x in range(w):
        ys = np.nonzero(mask[:, x])[0]
        if not len(ys):
            continue
        y0, y1 = ys.min(), ys.max() + 1
        level = 0.62 + 0.2 * math.sin(2 * t + x * 0.9) + 0.1 * math.sin(5 * t + x * 2.3)
        for y in ys:
            frac = (y1 - y) / max(1, y1 - y0)                     # 0 en bas de la fente, 1 en haut
            k = 2 if frac < level * 0.55 else 1 if frac < level else 0
            img[y, x, :3] = tones[k]
            img[y, x, 3] = 255
    return img


def render_direction(direction, out):
    path = os.path.join(out, "_boiler.png")
    build(direction)
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
    big = load(path)
    sprite_cell, shadow_cell, fire_cell = FRAMES[direction]
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{direction}-idle.png"), crop_centered(big, *sprite_cell))
    shadow = render_shadow(lambda: build(direction), path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR,
                           shift_y=camera_shift())
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{direction}-shadow.png"), crop_centered(shadow, *shadow_cell))
    if direction == "E":
        cv2.imwrite(entity_path(out, NAME, f"{NAME}-E-patch.png"), crop_centered(big, *PATCH))
    mask = slot_mask(big, direction)
    frames = [fire_frame(mask, i) for i in range(FIRE_FRAMES)]
    cv2.imwrite(entity_path(out, NAME, f"{NAME}-{direction}-fire.png"), np.vstack(
        [np.hstack(frames[r:r + FIRE_COLUMNS]) for r in range(0, FIRE_FRAMES, FIRE_COLUMNS)]))
    print(direction, "grille", grate_place(direction), "fentes :", int(mask.sum()), "px", flush=True)
    return big


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "boiler_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    os.makedirs(out, exist_ok=True)
    for d in (FRAMES if which == "toutes" else which.split(",")):
        render_direction(d, out)
        print("OK", d, flush=True)
    if which == "toutes":
        save_icon(out, NAME, lambda: build("N"))
