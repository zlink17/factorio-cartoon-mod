"""Tuyaux (pipe, pipe-to-ground) et couvercles de tuyaux (pipe-covers) : sprites, ombres, icônes.

Usage : python cartoon/blender/pipe.py <dossier_sortie> [tuyau|souterrain|couvercles|assembleurs|icones|tous] [nom...]

Écrit, aux chemins de l'original (base/entity/pipe/, pipe-to-ground/, pipe-covers/ et base/icons/) :
  pipe-<forme>.png              18 formes (droits, coudes, T, croix, bouts, fenêtres) : 128 x 128, la case au centre,
                                ombre portée incluse dans l'image (semi-transparente, comme l'original)
  pipe-straight-vertical-single.png   tuyau isolé (160 x 160)
  pipe-<h|v>-window-background.png    fond sombre des fenêtres (forme de l'original, en aplat)
  pipe-to-ground-<up|down|left|right>.png   tuyau qui plonge dans le sol, ombre incluse
  pipe-cover-<d>.png, pipe-cover-<d>-shadow.png   bouchon d'un raccord libre, ombre séparée (noire unie)
  pipe.png, pipe-to-ground.png (icônes)
Laissés d'origine : visualisations (interface), flux de fluide et vapeur (teintés par le jeu), restes (lot 3.9).

Le tuyau : tube en tôle claire couché sur le sol, brides cuivre aux bords de la case (elles se raccordent à
celles de la case voisine), bouchons à brides concentriques aux bouts. Chaque forme est faite de bras qui vont du
centre au milieu d'un bord de la case (n, e, s, o) ; deux bras opposés font un droit, deux bras voisins un coude
(arc de tube autour du coin). La fenêtre est un cadre posé sur le droit ; le verre reprend le trou translucide
de l'original (le jeu dessine le fluide dessous, dans un cadre fixe).
"""
import functools, math, os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import (FACTORIO_DATA, blob, box, crop_centered, cyl, entity_path, load, mat, render_scene, render_shadow,
                 render_with_shadow, reset, save_icon, target)

P = S.PALETTE
PX_PER_TILE = 64
CELL = 128
SUN_SHEAR = (0.45, 0.02)
SHADOW = (*SUN_SHEAR, 0.55)            # ombre incluse dans l'image : opacité (l'original est à ~0,5)
OUTLINE = 0.02

# dimensions (cases), ajustées sur la silhouette de l'original
DIMS = dict(
    r=0.33,            # rayon du tube
    rf=0.39,           # rayon des brides
    tf=0.1,            # épaisseur des brides (l'ajustement donne 0,065 : trop fin, la bride n'est plus qu'un trait)
    yc=-0.13,          # décalage du tube vers le sud (l'original est dessiné un peu plus bas que la case)
    end=0.6,           # bouts : avancée du bouchon au-delà du centre (fraction de demi-case)
)
ARMS = {"n": (0, 1), "e": (1, 0), "s": (0, -1), "w": (-1, 0)}       # vers le milieu de chaque bord (y : nord)

# formes du jeu -> bras (fichier pipe-<forme>.png)
SHAPES = {
    "straight-horizontal": "ew", "straight-vertical": "ns",
    "corner-up-right": "ne", "corner-up-left": "nw", "corner-down-right": "se", "corner-down-left": "sw",
    "t-up": "new", "t-down": "sew", "t-right": "nse", "t-left": "nsw", "cross": "nesw",
    "ending-up": "n", "ending-down": "s", "ending-right": "e", "ending-left": "w",
    "straight-horizontal-window": "ew", "straight-vertical-window": "ns",
}


def mats():
    return dict(tube=mat("tube", P["pipe"]), flange=mat("flange", P["brown"]), dark=mat("dark", P["dark"]),
                cap=mat("cap", P["pipe_cap"]))


def tube_path(points, r, m):
    """Tube d'un seul maillage le long d'une ligne brisée (raccords sans contour), bouts fermés."""
    import bpy
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 6
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


def disc(center, axis, r, t, m, verts=40):
    """Disque (cylindre court) d'axe horizontal `axis` (x ou y)."""
    return cyl(center, r, t, m, verts=verts, rot=(0, 90, 0) if axis == "x" else (90, 0, 0))


def flange(edge, inward, d, m):
    """Bride contre le bord de la case (`edge` : milieu du bord, `inward` : vers le centre), entièrement dans la
    case : avec celle de la case voisine, elle forme le raccord à deux brides de l'original."""
    dx, dy = inward
    x, y, z = edge
    h = d["tf"] / 2 - 0.015                  # dépasse à peine du bord : couvre le bout du tube (pas de scintillement)
    disc((x + dx * h, y + dy * h, z), "x" if dx else "y", d["rf"], d["tf"], m["flange"])


def cap(center, direction, d, m):
    """Bouchon au bout d'un bras, tourné vers `direction` : bride, puis deux anneaux en retrait (brides
    concentriques de l'original)."""
    dx, dy = direction
    axis = "x" if dx else "y"
    x, y, z = center
    for k, (rr, mm) in enumerate(((d["rf"], m["flange"]), (d["r"] * 0.85, m["cap"]), (d["r"] * 0.45, m["flange"]))):
        off = (d["tf"] / 2) + k * 0.035
        disc((x + dx * off, y + dy * off, z), axis, rr, d["tf"] if k == 0 else 0.04, mm)


def shape(arms, d, m):
    """Tuyau formé des bras `arms` (lettres n, e, s, o), centré sur la case."""
    r, yc = d["r"], d["yc"]
    z = r
    c = np.array((0.0, yc, z))
    vec = {a: np.array((*ARMS[a], 0.0)) * 0.5 for a in arms}
    done = set()
    # droits : bras opposés
    for a, b in (("e", "w"), ("n", "s")):
        if a in arms and b in arms:
            tube_path([tuple(c + vec[b]), tuple(c + vec[a])], r, m["tube"])
            done |= {a, b}
    rest = [a for a in arms if a not in done]
    if len(arms) == 2 and len(rest) == 2:                   # coude : arc autour du coin
        a, b = rest
        corner = c + vec[a] + vec[b]
        pts = []
        for t in np.linspace(0, 1, 13):
            ang = t * math.pi / 2
            pts.append(tuple(corner + (c + vec[a] - corner) * math.cos(ang) + (c + vec[b] - corner) * math.sin(ang)))
        tube_path(pts, r, m["tube"])
    else:
        for a in rest:                                       # bras seuls (T, bouts : d'un seul tenant jusqu'au bouchon)
            start = c - vec[a] * d["end"] if len(arms) == 1 else c
            tube_path([tuple(start), tuple(c + vec[a])], r, m["tube"])
        if len(arms) >= 3:
            blob(tuple(c), r, m["tube"])                     # nœud du T : sphère dans le tube
    for a in arms:                                           # brides aux bords
        flange(tuple(c + vec[a]), (-ARMS[a][0], -ARMS[a][1]), d, m)
    if len(arms) == 1:                                       # bout : bouchon un peu au-delà du centre
        a = arms[0]
        opp = (-ARMS[a][0], -ARMS[a][1])
        cap(tuple(c - vec[a] * d["end"]), opp, d, m)


def build_shape(name, d=None):
    d = d or DIMS
    reset()
    m = mats()
    if name == "straight-vertical-single":
        r, yc = d["r"], d["yc"]
        tube_path([(0, yc - 0.32, r), (0, yc + 0.32, r)], r, m["tube"])
        cap((0, yc + 0.32, r), (0, 1), d, m)
        cap((0, yc - 0.32, r), (0, -1), d, m)
        return
    shape(SHAPES[name], d, m)


def original(rel):
    return cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity", rel), cv2.IMREAD_UNCHANGED)


def glass(sprite, rel):
    """Verre de la fenêtre : le trou translucide de l'original (le jeu dessine le fluide dessous), en aplat clair."""
    o = original(rel)
    a = o[:, :, 3]
    ys, xs = np.nonzero(a > 200)
    hole = np.zeros(a.shape, np.uint8)
    y0, y1, x0, x1 = ys.min() + 3, ys.max() - 3, xs.min() + 6, xs.max() - 6       # sans les brides
    hole[y0:y1, x0:x1] = a[y0:y1, x0:x1] < 200
    hole = cv2.morphologyEx(hole, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(hole)
    keep = lab == (1 + int(np.argmax(st[1:, 4])))                                   # la plus grande ouverture
    out = sprite.copy()
    k = np.ones((3, 3), np.uint8)
    frame = cv2.dilate(keep.astype(np.uint8), k, iterations=3).astype(bool) & ~keep
    edge = cv2.dilate(frame.astype(np.uint8), k).astype(bool) & ~frame & ~keep
    rgb = lambda c: [round(v * 255) for v in c[::-1]]
    out[frame & (out[:, :, 3] > 0), :3] = rgb([v ** (1 / 2.2) for v in P["brown"]])     # cadre cuivre
    out[edge & (out[:, :, 3] > 0), :3] = rgb([v ** (1 / 2.2) for v in S.OUTLINE_COLOR[:3]])
    out[keep, :3] = (232, 238, 236)                                                  # verre
    out[keep, 3] = 45
    return out


def flat(im, color):
    a = im[:, :, 3] > 40
    out = np.zeros_like(im)
    out[a, :3] = color
    out[a, 3] = 255
    return out


def render_pipe(name, out, size=CELL):
    path = os.path.join(out, "_pipe.png")
    _, im = render_with_shadow(lambda: build_shape(name), path, size, size / PX_PER_TILE, SHADOW,
                               outline_units=OUTLINE)
    if name.endswith("window"):
        im = glass(im, f"pipe/pipe-{name}.png")
    return im


def write_pipes(out, only=None):
    for name in list(SHAPES) + ["straight-vertical-single"]:
        if only and name not in only:
            continue
        size = 160 if name == "straight-vertical-single" else CELL
        cv2.imwrite(entity_path(out, "pipe", f"pipe-{name}.png"), render_pipe(name, out, size))
        print("OK", name, flush=True)
    for k in ("horizontal", "vertical"):
        f = f"pipe-{k}-window-background.png"
        cv2.imwrite(entity_path(out, "pipe", f), flat(original(f"pipe/{f}"), (36, 34, 32)))


# --- tuyau souterrain ----------------------------------------------------------------------------------------
# direction du fichier -> (bord du raccord en surface, distance parcourue depuis ce bord avant de plonger).
# Mesuré sur l'original : le tuyau traverse presque la case vers le haut, moins vers les côtés, et plonge juste
# derrière sa bride vers le bas.
UNDERGROUND = {"up": ("n", 0.62), "down": ("s", 0.22), "left": ("w", 0.52), "right": ("e", 0.52)}


def build_underground(which, d=None):
    d = d or DIMS
    reset()
    m = mats()
    r, yc = d["r"], d["yc"]
    a, reach = UNDERGROUND[which]
    edge = np.array((ARMS[a][0] * 0.5, yc + ARMS[a][1] * 0.5, r))
    inward = -np.array((*ARMS[a], 0.0))
    knee = edge + inward * max(0.0, reach - r)
    pts = [tuple(edge)]
    for t in np.linspace(0, 1, 10):                          # coude qui plonge dans le sol
        ang = t * math.pi / 2
        pts.append(tuple(knee + inward * r * math.sin(ang) + np.array((0, 0, -r * (1 - math.cos(ang))))))
    pts.append(tuple(knee + inward * r + np.array((0, 0, -0.4))))
    tube_path(pts, r, m["tube"])
    flange(tuple(edge), tuple(inward[:2]), d, m)
    foot = knee + inward * r
    cyl((foot[0], foot[1], 0.02), d["rf"], 0.04, m["flange"], verts=40)          # collerette au sol


def write_underground(out):
    path = os.path.join(out, "_ptg.png")
    for which in UNDERGROUND:
        _, im = render_with_shadow(lambda: build_underground(which), path, CELL, CELL / PX_PER_TILE, SHADOW,
                                   outline_units=OUTLINE)
        cv2.imwrite(entity_path(out, "pipe-to-ground", f"pipe-to-ground-{which}.png"), im)
        print("OK souterrain", which, flush=True)


# --- couvercles : dessinés sur la case voisine d'un raccord libre, bouchon contre le bord partagé ---------------
COVERS = {"north": "s", "south": "n", "east": "w", "west": "e"}   # direction du raccord -> bord partagé


def build_cover(direction, d=None):
    """Bouchon seul, posé contre le bord partagé, tourné vers la case voisine (l'original ne dessine rien dans
    l'entité)."""
    d = d or DIMS
    reset()
    m = mats()
    a = COVERS[direction]
    edge = (ARMS[a][0] * 0.5, d["yc"] + ARMS[a][1] * 0.5, d["r"])
    cap(edge, (-ARMS[a][0], -ARMS[a][1]), d, m)


def write_covers(out):
    path = os.path.join(out, "_cover.png")
    for direction in COVERS:
        build_cover(direction)
        render_scene(path, size=CELL, scale=CELL / PX_PER_TILE, outline_units=OUTLINE)
        cv2.imwrite(entity_path(out, "pipe-covers", f"pipe-cover-{direction}.png"), load(path))
        sh = render_shadow(lambda: build_cover(direction), path, CELL, CELL / PX_PER_TILE, SUN_SHEAR)
        cv2.imwrite(entity_path(out, "pipe-covers", f"pipe-cover-{direction}-shadow.png"), sh)
        print("OK couvercle", direction, flush=True)


# --- raccords des assembleurs 2 et 3 : tube qui sort de la paroi, cadre à la couleur du niveau, bride -----------
# Dessinés par le jeu au raccord (pipe_picture) ; pour chaque direction : vers l'extérieur, position de la paroi et
# du bout du tube le long de cet axe (cases, depuis l'origine de l'image), ajustées sur l'original. Au nord, le
# raccord sort de la paroi arrière, cachée par la machine : pas de cadre, et le tube s'enfonce vers la machine
# (le cadre de l'image le coupe) : on n'en voit que la bride et le dessus, comme l'original.
TIERS = {2: ("assembling-machine-2", "steel_blue"), 3: ("assembling-machine-3", "olive")}
OUTWARD = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "W": (-1, 0)}
MACHINE_PIPE = {"N": (-1.0, -0.5), "E": (-0.9, -0.5), "S": (-1.2, -0.7), "W": (-0.8, -0.5)}


@functools.lru_cache(None)
def machine_cells():
    """Taille et décalage (px) des images de raccord des assembleurs, par direction (identiques pour 2 et 3)."""
    import json
    dump = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".cache", "data-raw-dump.json")
    pp = json.load(open(dump))["assembling-machine"]["assembling-machine-2"]["fluid_boxes"][0]["pipe_picture"]
    long = {"N": "north", "E": "east", "S": "south", "W": "west"}
    return {k: ((pp[v]["width"], pp[v]["height"]), (pp[v]["shift"][0] * PX_PER_TILE, pp[v]["shift"][1] * PX_PER_TILE))
            for k, v in long.items()}


def build_machine_pipe(direction, tier, d=None, place=None):
    d = d or DIMS
    reset()
    m = mats()
    frame = mat("frame", P[TIERS[tier][1]])
    wall, end = place or MACHINE_PIPE[direction]
    u = np.array((*OUTWARD[direction], 0.0))
    c = np.array((0.0, d["yc"], d["r"]))
    tube_path([tuple(c + u * (wall - 0.1)), tuple(c + u * end)], d["r"], m["tube"])
    flange(tuple(c + u * end), tuple(-u[:2]), d, m)
    axis = "x" if u[0] else "y"
    if direction == "N":           # paroi arrière : le cadre est tourné vers le nord, caché par la machine
        return
    size = (0.08, 0.8, 0.8) if axis == "x" else (0.8, 0.08, 0.8)
    box(tuple(c + u * wall + np.array((0, 0, 0.05))), size, frame)                    # cadre sur la paroi
    disc(tuple(c + u * (wall + 0.05)), axis, d["rf"] * 1.05, 0.06, m["flange"])       # collerette


def write_machine_pipes(out):
    path = os.path.join(out, "_mp.png")
    for tier, (name, _) in TIERS.items():
        for direction in OUTWARD:
            build_machine_pipe(direction, tier)
            render_scene(path, size=2 * CELL, scale=2 * CELL / PX_PER_TILE, outline_units=OUTLINE)
            im = crop_centered(load(path), *machine_cells()[direction])
            cv2.imwrite(entity_path(out, name, f"{name}-pipe-{direction}.png"), im)
        print("OK raccords", name, flush=True)


def write_icons(out):
    save_icon(out, "pipe", lambda: build_shape("straight-vertical-single"))   # tuyau court à bouchons (original)
    save_icon(out, "pipe-to-ground", lambda: build_underground("left"))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "pipe_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    only = sys.argv[3:] or None
    os.makedirs(out, exist_ok=True)
    if which in ("tuyau", "tous"):
        write_pipes(out, only)
    if which in ("souterrain", "tous"):
        write_underground(out)
    if which in ("couvercles", "tous"):
        write_covers(out)
    if which in ("assembleurs", "tous"):
        write_machine_pipes(out)
    if which in ("icones", "tous"):
        write_icons(out)
