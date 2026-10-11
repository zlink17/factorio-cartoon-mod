"""Pompe côtière (offshore-pump) : planches animées des 4 directions, ombres, pieds, partie immergée, vitres et
fenêtres de fluide, icône.

Usage : python cartoon/blender/offshore_pump.py <dossier_sortie> [direction[,direction...]|toutes] [--apercu]
        direction = N, E, S, W ; --apercu : une seule image par planche (réglages)

Écrit, aux chemins de l'original (base/entity/offshore-pump/ et base/icons/) :
  offshore-pump_<D>.png             32 images (8 par ligne) : la pompe, pistons en marche
  offshore-pump_<D>-shadow.png      32 ombres, noires unies
  offshore-pump_<D>-legs.png        pieds posés sur la berge (calque du sol, dessiné sous la pompe)
  offshore-pump_<D>-underwater.png  bas du réservoir sous l'eau (dessiné sous la surface de l'eau)
  offshore-pump_<D>-fluid.png       eau dans les fenêtres des cylindres : forme de l'original, en aplats (le jeu
                                    la teinte de la couleur du fluide)
  offshore-pump_<D>-glass.png       reflets des vitres, en aplats
  offshore-pump.png (icône)         64 px + mipmaps
Le reflet dans l'eau (fichier technique) et les restes (lot 3.9) sont laissés d'origine.

La pompe (1 x 2 cases ; nord = l'eau au nord, sortie au sud) : réservoir jaune à deux lobes plongé dans l'eau,
deux cylindres couchés à fenêtres (pistons qui vont et viennent), gaines orange annelées du réservoir aux
cylindres et des cylindres à la sortie, bride claire de la sortie face au tuyau, pieds sur la berge, flasques à
engrenages sur les côtés. Modèle construit vers le nord puis tourné pour chaque direction.
"""
import functools, math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import (FACTORIO_DATA, box, crop_centered, cyl, entity_path, gear, load, mat, render_scene, render_shadow,
                 reset, rod, save_icon, sheet)

P = S.PALETTE
NAME = "offshore-pump"
PX_PER_TILE = 64
CANVAS = 384
N_FRAMES, COLUMNS = 32, 8
SUN_SHEAR = (0.45, 0.02)
OUTLINE = 0.02
YAW = {"N": 0, "E": -90, "S": 180, "W": 90}   # rotation du modèle (degrés, autour de z)
LONG = {"N": "North", "E": "East", "S": "South", "W": "West"}
LAYERS = ("sprite", "shadow", "legs", "underwater", "fluid", "glass")


@functools.lru_cache(None)
def proto_cells():
    """Taille et décalage (px) de chaque calque, par direction, lus dans le dump des prototypes."""
    import json
    dump = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".cache", "data-raw-dump.json")
    gs = json.load(open(dump))["offshore-pump"][NAME]["graphics_set"]
    cells = {}
    for d, long in LONG.items():
        sprite, shadow = gs["animation"][long.lower()]["layers"]
        src = dict(sprite=sprite, shadow=shadow, legs=gs["base_pictures"][long.lower()],
                   underwater=gs["underwater_pictures"][long.lower()], fluid=gs["fluid_animation"][long.lower()],
                   glass=gs["glass_pictures"][long.lower()])
        cells[d] = {k: ((v["width"], v["height"]), (v["shift"][0] * PX_PER_TILE, v["shift"][1] * PX_PER_TILE))
                    for k, v in src.items()}
    return cells


# dimensions (cases), ajustées sur la silhouette de l'original dans les quatre directions
DIMS = dict(
    down=0.1,                       # décalage de tout le dessin vers le bas de l'écran
    yt=1.15, rt=0.32, xt=0.24, zt=0.92,   # réservoir : centre y, rayon d'un lobe, écart des lobes, hauteur du bord
    xk=0.24, rk=0.24, zk=0.53, yk0=-0.15, yk1=0.85,   # cylindres jointifs : écart, rayon, axe, bouts
    yf=-0.49, rf=0.44,              # bride de sortie : position, rayon
)


def hose(points, r, m_a, m_b, ring=0.09):
    """Gaine annelée d'un seul maillage le long d'une ligne brisée : anneaux de deux couleurs peints (pas de
    contour par anneau)."""
    import bpy
    cu = bpy.data.curves.new("hose", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    pts = _dense(points, ring / 3)
    sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        p.co = (*q, 1)
    o = bpy.data.objects.new("hose", cu)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    o.data.materials.append(m_a)
    o.data.materials.append(m_b)
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    tree = np.array(pts)
    for f in o.data.polygons:
        k = int(np.argmin(np.linalg.norm(tree - np.array(f.center), axis=1)))
        f.material_index = int(cum[k] / ring) % 2
    return o


def _dense(points, step):
    out = [np.array(points[0], float)]
    for a, b in zip(points, points[1:]):
        a, b = np.array(a, float), np.array(b, float)
        n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * (i / n) for i in range(1, n + 1)]
    return [tuple(p) for p in out]


def bezier(p0, p1, p2, n=10):
    """Points d'une courbe de Bézier quadratique (coudes des gaines)."""
    p0, p1, p2 = (np.array(p, float) for p in (p0, p1, p2))
    return [tuple((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2) for t in np.linspace(0, 1, n)]


def mats():
    return dict(
        tank=mat("tank", P["pump_tank"]), rim=mat("rim", P["pump_yellow"]), dark=mat("dark", P["dark"]), iron=mat("iron", P["dark_grey"]),
        frame=mat("frame", P["iron"]), copper=mat("copper", P["brown"]), pipe=mat("pipe", P["engine_pipe"]),
        hose=mat("hose", P["pump_hose"]), hose_dark=mat("hose_dark", P["pump_hose_dark"]),
        piston=mat("piston", P["white"]), brass=mat("brass", P["yellow"]), rust=mat("rust", P["engine_rust"]),
    )


def legs(m, d):
    """Pieds posés sur la berge, de chaque côté des cylindres (calque du sol)."""
    out = []
    for s in (-1, 1):
        x = s * (d["xk"] + d["rk"] + 0.16)
        out.append(box((x, (d["yk0"] + d["yk1"]) / 2, 0.03), (0.1, d["yk1"] - d["yk0"], 0.06), m["rust"]))
        for y in (d["yk0"] + 0.05, d["yk1"] - 0.05):
            out.append(rod((x, y, 0.05), (s * (d["xk"] + d["rk"] * 0.6), y, d["zk"] - 0.05), 0.045, m["rust"], 8))
    return out


def under(m, d):
    """Bas du réservoir, sous la surface de l'eau (z < 0)."""
    out = []
    for s in (-1, 1):
        out.append(cyl((s * d["xt"], d["yt"], -0.3), d["rt"] * 0.95, 0.6, m["tank"], verts=32))
    return out


@functools.lru_cache(None)
def _fluid_mask(direction):
    """Union, sur toutes les images, des fenêtres de fluide de l'original (cadre de la direction)."""
    (w, h), _ = proto_cells()[direction]["fluid"]
    im = original(f"{NAME}_{LONG[direction]}-fluid.png")
    a = np.zeros((h, w), bool)
    for r in range(0, im.shape[0], h):
        for c in range(0, im.shape[1], w):
            a |= im[r:r + h, c:c + w, 3] > 60
    return a


def window_span(direction, d=None):
    """Étendue des fenêtres le long des cylindres (y du modèle, de y0 à y1), d'après les fenêtres de fluide de
    l'original : le jeu dessine l'eau teintée dans ce cadre fixe, par-dessus la pompe, et l'original ne place pas
    ses fenêtres au même endroit d'une direction à l'autre (comme les hublots de la foreuse humide)."""
    d = d or DIMS
    (w, h), (sx, sy) = proto_cells()[direction]["fluid"]
    ys, xs = np.nonzero(_fluid_mask(direction))
    if direction in ("N", "S"):
        z = d["zk"] + d["rk"]
        lo, hi = ys.min() - h / 2 + sy, ys.max() + 1 - h / 2 + sy            # écran, px vers le bas
        p = math.radians(S.PITCH_BUILDING_DEG)
        to_y = lambda v: -(v - d["down"] * PX_PER_TILE + z * PX_PER_TILE * math.sin(p)) / (
            PX_PER_TILE * math.cos(p))
        y0, y1 = sorted((to_y(lo), to_y(hi)))
        if direction == "S":
            y0, y1 = -y1, -y0
    else:
        lo, hi = xs.min() - w / 2 + sx, xs.max() + 1 - w / 2 + sx
        y0, y1 = sorted((lo / PX_PER_TILE, hi / PX_PER_TILE) if direction == "E"
                        else (-hi / PX_PER_TILE, -lo / PX_PER_TILE))
    return max(y0, d["yk0"] + 0.06), min(y1, d["yk1"] - 0.06)


def body(m, d, phase, direction):
    """La pompe hors de l'eau : réservoir, cylindres et pistons, gaines, sortie, flasques."""
    xk, rk, zk, yk0, yk1 = d["xk"], d["rk"], d["zk"], d["yk0"], d["yk1"]
    yt, rt, xt, zt = d["yt"], d["rt"], d["xt"], d["zt"]
    # réservoir à deux lobes : corps brun sombre, large bord jaune, fond sombre où plongent les gaines
    for s in (-1, 1):
        cyl((s * xt, yt, zt / 2), rt, zt, m["tank"], verts=32)
        cyl((s * xt, yt, zt - 0.11), rt + 0.03, 0.26, m["rim"], verts=32)
        cyl((s * xt, yt, zt - 0.02), rt * 0.72, 0.06, m["dark"], verts=32)
    # cylindres couchés : corps sombre, cerclages, fenêtre sombre sur le dessus, piston clair qui va et vient
    for s, ph in ((-1, 0.0), (1, 0.5)):
        x = s * xk
        cyl((x, (yk0 + yk1) / 2, zk), rk, yk1 - yk0, m["iron"], verts=24, rot=(90, 0, 0))
        for y in (yk0 + 0.04, yk1 - 0.04):
            cyl((x, y, zk), rk + 0.025, 0.07, m["frame"], verts=24, rot=(90, 0, 0))
        w0, w1 = window_span(direction, d)
        box((x, (w0 + w1) / 2, zk + rk - 0.02), (rk * 0.9, w1 - w0, 0.06), m["dark"])
        travel = (w1 - w0 - 0.12) / 2 * math.sin(2 * math.pi * (phase + ph))
        box((x, (w0 + w1) / 2 + travel, zk + rk), (rk * 0.7, 0.1, 0.06), m["piston"])
    # flasques à engrenages sur les côtés
    a = phase * 360
    for s in (-1, 1):
        x = s * (xk + rk + 0.05)
        box((x, (yk0 + yk1) / 2, zk - 0.12), (0.05, yk1 - yk0 - 0.3, 0.2), m["frame"])
        g = gear((0, 0, 0), 0.11, 0.05, 9, s * a, m["brass"])
        g.location = (x + s * 0.06, yk0 + 0.18, zk - 0.08)
        g.rotation_euler = (0, math.radians(90), 0)
    # gaines en arceaux : du réservoir vers le bout nord de chaque cylindre, du bout sud vers le collecteur de
    # sortie (les fenêtres, entre les deux, restent dégagées)
    for s in (-1, 1):
        x = s * xk
        hose(bezier((s * xt, yt, zt - 0.1), (s * xk, yk1 + 0.05, zt + 0.75), (x, yk1 - 0.05, zk + 0.1)),
             0.15, m["hose"], m["hose_dark"])
        hose(bezier((x, yk0 + 0.05, zk + 0.1), (x, yk0 - 0.2, zk + 0.6), (s * 0.12, d["yf"] + 0.3, d["rf"] + 0.15)),
             0.15, m["hose"], m["hose_dark"])
    # sortie : collecteur clair, bride face au tuyau
    rf, yf = d["rf"], d["yf"]
    rod((0, yf + 0.38, rf), (0, yf + 0.03, rf), rf * 0.72, m["pipe"], verts=32)
    cyl((0, yf + 0.03, rf), rf, 0.06, m["frame"], verts=32, rot=(90, 0, 0))       # bride
    cyl((0, yf - 0.005, rf), rf * 0.82, 0.02, m["pipe"], verts=32, rot=(90, 0, 0))  # face claire


def build(direction="N", phase=0.0, part="sprite", d=None):
    """Scène d'une direction : `part` = sprite (la pompe), legs, underwater, ou all (icône, ombre)."""
    import bpy
    from mathutils import Matrix
    reset()
    d = d or DIMS
    m = mats()
    if part in ("sprite", "all"):
        body(m, d, phase, direction)
    if part in ("legs", "all"):
        legs(m, d)
    if part == "underwater":
        under(m, d)
    bpy.context.view_layer.update()          # matrices à jour (sinon le dernier objet perd son échelle)
    rot = Matrix.Rotation(math.radians(YAW[direction]), 4, "Z")
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.matrix_world = rot @ o.matrix_world


def camera_shift(d=None):
    return (d or DIMS)["down"] * PX_PER_TILE / CANVAS


def render(direction, phase, part, path):
    build(direction, phase, part)
    render_scene(path, size=CANVAS, scale=CANVAS / PX_PER_TILE, outline_units=OUTLINE, shift_y=camera_shift())
    return load(path)


def flat(im, levels=2):
    """Calque de l'original (fluide, vitre) en aplats : forme nette (alpha seuillé), gris réduit à `levels` tons."""
    a = im[:, :, 3] > 60
    out = np.zeros_like(im)
    if a.any():
        g = im[:, :, :3].mean(2)
        lo, hi = np.percentile(g[a], 30), np.percentile(g[a], 85)
        tone = np.where(g > (lo + hi) / 2, hi, lo) if levels == 2 else np.full(g.shape, g[a].mean())
        out[a, :3] = tone[a, None]
        out[a, 3] = 255
    return out


def original(file):
    return cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity", NAME, file), cv2.IMREAD_UNCHANGED)


def render_direction(direction, out, cells, preview=False):
    c = cells[direction]
    path = os.path.join(out, "_pump.png")
    pre = f"{NAME}_{LONG[direction]}"
    n = 1 if preview else N_FRAMES
    sprites, shadows = [], []
    for i in range(n):
        ph = i / N_FRAMES
        sprites.append(crop_centered(render(direction, ph, "sprite", path), *c["sprite"]))
        sh = render_shadow(lambda: build(direction, ph, "all"), path, CANVAS, CANVAS / PX_PER_TILE, SUN_SHEAR,
                           shift_y=camera_shift())
        shadows.append(crop_centered(sh, *c["shadow"]))
    if preview:
        sprites, shadows = sprites * N_FRAMES, shadows * N_FRAMES
    cv2.imwrite(entity_path(out, NAME, f"{pre}.png"), sheet(sprites, COLUMNS))
    cv2.imwrite(entity_path(out, NAME, f"{pre}-shadow.png"), sheet(shadows, COLUMNS))
    for part in ("legs", "underwater"):
        cv2.imwrite(entity_path(out, NAME, f"{pre}-{part}.png"), crop_centered(render(direction, 0, part, path),
                                                                                *c[part]))
    cv2.imwrite(entity_path(out, NAME, f"{pre}-fluid.png"), flat(original(f"{pre}-fluid.png")))
    glass = flat(original(f"{pre}-glass.png"), 1)
    glass[:, :, 3] = (glass[:, :, 3] * 0.6).astype(np.uint8)
    cv2.imwrite(entity_path(out, NAME, f"{pre}-glass.png"), glass)


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--apercu" in args
    args = [a for a in args if a != "--apercu"]
    out = args[0] if args else "offshore_pump_out"
    which = args[1] if len(args) > 1 else "toutes"
    os.makedirs(out, exist_ok=True)
    cells = proto_cells()
    for d in (YAW if which == "toutes" else which.split(",")):
        render_direction(d, out, cells, preview)
        print("OK", d, flush=True)
    if which == "toutes":
        save_icon(out, NAME, lambda: build("N", 0.0, "all"))
