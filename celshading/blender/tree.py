"""Arbres de Nauvis en cel-shading : tronc et feuillage en touffes « chou-fleur » (modèle 3D), d'après l'image
de Bastien celshading/concept/cibles/arbre-bastien.jpg (12 octobre) : arbre élancé en étages, dessus clair, dessous
foncé, trait autour de chaque touffe, branches entre les touffes, tronc évasé à racines.

Usage : python celshading/blender/tree.py <dossier_sortie> apercu
          planche de travail de la variante 02-a (original / rendus teints) dans <sortie>/apercu.png
        python celshading/blender/tree.py <dossier_sortie> especes
          planche de travail : la variante a de chaque espèce, originale et refaite, dans <sortie>/especes.png
        python celshading/blender/tree.py <dossier_sortie> <espèce>[,<espèce>...]
          production : toutes les variantes de l'espèce (ex. 02), écrites en base/entity/tree/<espèce>/

Le jeu dessine chaque arbre en calques, cadrés par le prototype (taille et `shift`) : tronc (jusqu'en haut : on le
voit quand le feuillage est abîmé), feuillage en 3 états (plein, abîmé, presque nu) et ses normales, ombre en
4 états (les 3 du feuillage, puis le tronc seul), souche (cadavre « tree-XX-stump »). Le feuillage est teint par le
jeu (couleur tirée au hasard dans `colors`) : il est rendu en tons neutres clairs ; l'aperçu applique la teinte.

Chaque variante est calée sur son original : pied du tronc, hauteur et largeur du feuillage, longueur de l'ombre
sont mesurés sur les fichiers d'origine. Tous les calques sont rendus sur un même canevas centré sur l'entité
(sprites à scale 0,5 : 64 px du fichier par case), puis découpés au cadre de chaque fichier.
"""
import json, math, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import cv2
import numpy as np
from lib import reset, couleur, render_scene, render_shadow, crop_centered, line_color, S

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data/"
DUMP = os.path.join(ROOT, ".cache", "data-raw-dump.json")
TILE_PX = 64                   # px du fichier par case du jeu (sprites à scale 0,5) : place les cadres (`shift`)
PX = 128                       # px du fichier par unité du modèle (1 unité = 2 cases ; échelle de rendu)
CANVAS = 1100                  # canevas carré centré sur l'entité, en px du fichier
SHADOW_CANVAS = 1500           # celui des ombres, qui partent loin à droite
COS = math.cos(math.radians(S.PITCH_BUILDING_DEG))     # une case au sol se voit COS case à l'écran
SIN = math.sin(math.radians(S.PITCH_BUILDING_DEG))     # une hauteur z se voit z x SIN à l'écran
LEAF = "#c2cab2"               # feuillage neutre (ton moyen ; le jeu le teinte)
# tons du feuillage (lib.mat, paliers) : dessous foncé et dessus clair larges et marqués, comme la cible de Bastien ;
# ombre : seuil, puis teinte (vert-bleu foncé une fois teinte par le jeu) ; clair : seuil, puis teinte
LEAF_STEPS = (0.50, 0.78, 0.48, 0.54, 0.72, 1.22, 1.22, 1.05)
BARK = "#a87446"
LINE_PX = 3                    # épaisseur du trait autour des touffes, en px du fichier (128 px par case)
FLAT_NORMAL = (255, 128, 128)  # BGR : normale (0, 0, 1), face à la caméra (comme le mod cartoon)
TRUNK_SHOW = 0.3               # bas du feuillage remonté (unités, à l'écran) : le tronc se voit comme sur l'original
ROOT_BACK = 0.3                # pied reculé (unités au sol) : racines et pied restent dans le cadre du tronc d'origine
# dessin propre à chaque espèce (12 octobre, validé par Bastien) ; les autres : touffes en chou-fleur
# (voir celshading/concept/descriptions/arbres.md)
DESIGNS = {"01": "sapin", "03": "noueux", "04": "elance", "05": "dome", "06": "saule", "07": "masses",
           "08": "parasol", "09": "geant"}
BARK_BY = {"elance": "#b88d66", "parasol": "#c29c74"}          # écorce claire et chaude (04, 08 ; un gris vire au lilas)
FIR_LAYERS = 3                 # étages du sapin (Bastien : trois, plus lisibles en cel-shading)
R_CAP = {"geant": 0.5}         # taille maximale des touffes (unités), 0,42 par défaut
FOOT_BACK = {"geant": 0.6}     # recul du pied (unités au sol) par dessin, ROOT_BACK par défaut
FIR_TRUNK = 0.7                # hauteur de tronc dégagée sous le premier étage du sapin (unités)
# états du feuillage : (part des boules gardées, facteur de rayon)
STATES = [(1.0, 1.0), (0.55, 0.85), (0.25, 0.6)]


# --- mesures sur l'original -----------------------------------------------------------------------------------------

def variations(species):
    d = json.load(open(DUMP))
    return d["tree"][f"tree-{species}"]["variations"], d["corpse"].get(f"tree-{species}-stump", {}).get("animation", [])


def path_of(pic):
    return pic["filename"].replace("__base__/graphics/", "base/graphics/")


def load(pic):
    return cv2.imread(DATA + path_of(pic), cv2.IMREAD_UNCHANGED)


def opaque(pic, frame=0, thr=128):
    """Masque de la partie opaque d'une image du fichier (seuil abaissé si l'image est translucide, comme le saule)
    et position de son coin haut-gauche en px depuis la position de l'entité (x droite, y bas)."""
    im = load(pic)
    w, h = pic["width"], pic["height"]
    a = im[:h, frame * w:(frame + 1) * w, 3]
    if (a > thr).sum() < 200:
        thr = 40
    ox, oy = pic["shift"][0] * TILE_PX - w / 2, pic["shift"][1] * TILE_PX - h / 2
    return a > thr, ox, oy


def extent(pic, frame=0, thr=128):
    """Boîte de la partie opaque d'une image du fichier, en px depuis la position de l'entité (x droite, y bas)."""
    m, ox, oy = opaque(pic, frame, thr)
    ys, xs = np.where(m)
    return xs.min() + ox, xs.max() + ox, ys.min() + oy, ys.max() + oy


def rows(pic):
    """Largeur du feuillage d'origine à chaque hauteur : fonction h -> (gauche, droite), en unités depuis
    l'entité, h en unités à l'écran au-dessus de l'entité (None si rien à cette hauteur)."""
    m, ox, oy = opaque(pic)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))

    def at(h, r):
        y0, y1 = int(-(h + r / 2) * PX - oy), int(-(h - r / 2) * PX - oy)
        band = m[max(0, y0):max(0, y1)]
        cols = np.where(band.any(0))[0] if band.size else []
        if not len(cols):
            return None
        return (cols.min() + ox) / PX, (cols.max() + ox) / PX
    return at


def trunk_radius(pic):
    """Rayon du tronc d'après la largeur du pied de l'original (bas du calque « tronc »), en unités."""
    m, _, _ = opaque(pic)
    ys, _ = np.where(m)
    y1 = ys.max()
    band = m[y1 - max(4, int(0.08 * (y1 - ys.min()))):y1 - 3]
    cols = np.where(band.any(0))[0]
    return min(0.40, max(0.12, (cols.max() - cols.min()) / 2 / PX * 1.1))


def fit(v, seed, design="chou-fleur"):
    """Paramètres du modèle d'une variante, d'après son original (en unités du monde)."""
    l0, l1, t0, t1 = extent(v["leaves"])
    _, _, _, base = extent(v["trunk"])
    _, s1, _, _ = extent(v["shadow"], 0, 40)
    top, bottom = -t0 / PX, -t1 / PX           # haut et bas du feuillage au-dessus de l'entité (unités, à l'écran)
    lift = -base / PX                          # pied du tronc au-dessus de l'entité (unités, à l'écran)
    half = (l1 - l0) / 2 / PX                  # demi-largeur du feuillage (unités)
    r_max = min(R_CAP.get(design, 0.42), half * 0.52)   # taille des touffes : deux côte à côte pour un arbre étroit
    back = FOOT_BACK.get(design, ROOT_BACK)
    p = {
        "seed": seed, "design": design, "base_y": lift / COS + back, "x": (l0 + l1) / 2 / PX,
        "z0": (bottom + r_max * 0.8 + TRUNK_SHOW - lift - back * COS) / SIN,   # recul du pied compensé
        "z1": (top - r_max * 1.25 - lift - back * COS) / SIN,         # à l'écran : on le compense en hauteur
        "width": max(0.05, half - r_max * 1.0), "r": (r_max * 0.8, r_max),
        "screen0": lift + back * COS,          # hauteur à l'écran de z = 0 (pied reculé)
        "top": top,                            # haut du feuillage d'origine (unités, à l'écran)
        "rows": rows(v["leaves"]), "trunk_r": min(trunk_radius(v["trunk"]), max(0.12, half * 0.35)),
    }
    tw, th = v["trunk"]["width"], v["trunk"]["height"]       # cadre du tronc : racines et pied doivent y tenir
    tx, ty = v["trunk"]["shift"][0] * TILE_PX, v["trunk"]["shift"][1] * TILE_PX
    p["room_down"] = (ty + th / 2) / PX + p["screen0"] - 0.03                 # sous le pied, à l'écran
    p["room_side"] = min(p["x"] - (tx - tw / 2) / PX, (tx + tw / 2) / PX - p["x"]) - 0.04
    if design == "saule":                      # le saule est surtout son tronc : on cale le haut sur le calque tronc
        _, _, tt, _ = extent(v["trunk"])
        p["z1"] = (-tt / PX - 0.3 - p["screen0"]) / SIN
        p["height"] = p["z1"] + 0.1
    lw = v["leaves"]["width"]                  # bords du cadre du feuillage (unités) : aucune touffe ne doit en sortir
    lx = v["leaves"]["shift"][0] * TILE_PX
    p["frame_x"] = ((lx - lw / 2) / PX, (lx + lw / 2) / PX)
    p["height"] = p["z1"] + 0.3
    # ombre : chaque point (x, y, z) tombe au sol en x + kx z ; on cale kx sur le bout de l'ombre d'origine
    p["shear"] = (max(0.4, (s1 / PX - p["x"]) / (p["height"] + 0.4)), 0.0)
    return p


# --- modèle -----------------------------------------------------------------------------------------------------

def sphere(loc, r, m, squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=40, ring_count=20)
    o = bpy.context.object
    o.scale = (1, 1, squash)
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def crown_balls(p):
    """Éléments du feuillage (x, y, z, taille) selon le dessin de l'espèce."""
    if p["design"] == "sapin":
        return fir_layers(p)
    if p["design"] == "saule":
        return willow_anchors(p)
    if p["design"] == "elance":
        return zigzag(p)
    if p["design"] == "masses":
        return masses(p)
    if p["design"] == "parasol":
        return parasol(p)
    balls = clumps(p)
    if p["design"] == "noueux":                                 # des trous dans la couronne
        rng = random.Random(p["seed"] + 5)
        balls = balls[:-1]
        drop = set(rng.sample(range(len(balls)), round(len(balls) * 0.45)))
        balls = [b for i, b in enumerate(balls) if i not in drop] + [clumps(p)[-1]]
    return balls


def zigzag(p):
    """Arbre élancé : une touffe par étage, d'un côté puis de l'autre, une au sommet ; étages remontés."""
    rng = random.Random(p["seed"])
    r0, r1 = p["r"]
    z0 = p["z0"] + 0.15
    n = max(4, round((p["z1"] - z0) / (r1 * 1.25)) + 1)
    out = []
    side = rng.choice((-1, 1))
    for i in range(n):
        z = z0 + (p["z1"] - z0) * i / (n - 1)
        span = row_span(p, z, r1) or (p["x"] - r1, p["x"] + r1)
        half = max(0.0, (span[1] - span[0]) / 2 - r1)
        out.append(((span[0] + span[1]) / 2 + side * half * rng.uniform(0.85, 1.0),
                    p["base_y"] + rng.uniform(-0.1, 0.2), z, r1 * rng.uniform(0.85, 0.95)))
        side = -side
    out.append((p["x"], p["base_y"] + 0.1, p["z1"] + r0 * 0.5, r0))
    return out


def masses(p):
    """Arbre en masses : trois amas de touffes à trois hauteurs, alternés gauche / droite."""
    rng = random.Random(p["seed"])
    r0, r1 = p["r"]
    out = []
    side = rng.choice((-1, 1))
    rm = r1 * 0.72                                              # touffes plus petites : les masses se détachent
    for zf in (0.0, 0.5, 1.0):
        z = p["z0"] - 0.1 + (p["z1"] - p["z0"] + 0.1) * zf
        span = row_span(p, z, rm) or (p["x"] - rm, p["x"] + rm)
        cx = (span[0] + span[1]) / 2 + side * max(0.0, (span[1] - span[0]) / 2 - rm * 1.9) * 0.9
        for dx, dz, dy in ((-0.85, 0, 0.1), (0.85, 0, 0.1), (0, 0.65, 0.0), (0, 0.1, -0.3)):
            out.append((cx + dx * rm, p["base_y"] + dy, z + dz * rm, rm * rng.uniform(0.85, 1.0)))
        side = -side
    return out


def parasol(p):
    """Arbre en parasol : un anneau de touffes sur la plus grande largeur de la silhouette, une couche plus petite
    au-dessus."""
    rng = random.Random(p["seed"])
    r0, r1 = p["r"]
    zc = p["z0"] + (p["z1"] - p["z0"]) * 0.55
    span = max((row_span(p, p["z0"] + (p["z1"] - p["z0"]) * f, r1) or (p["x"], p["x"]) for f in (0.3, 0.5, 0.7)),
               key=lambda sp: sp[1] - sp[0])
    left, right = span[0] + r1 * 1.15, span[1] - r1 * 1.15
    n = max(3, round((right - left) / (r1 * 1.4)) + 1)
    out = []
    for k in range(n):                                          # anneau : derrière puis devant
        x = left + (right - left) * k / (n - 1)
        out.append((x, p["base_y"] + 0.3, zc + rng.uniform(-0.08, 0.08), r1 * rng.uniform(0.9, 1.0)))
    for k in range(n - 1):
        x = left + (right - left) * (k + 0.5) / (n - 1)
        out.append((x, p["base_y"] - 0.3, zc - r1 * 0.3, r1 * rng.uniform(0.85, 1.0)))
    for k in range(max(1, n - 2)):                             # couche du dessus
        x = left + (right - left) * (k + 1) / (n - 1) if n > 2 else p["x"]
        out.append((x, p["base_y"], zc + r1 * 1.1, r0 * rng.uniform(0.85, 1.0)))
    return out


def row_span(p, z, r):
    """(gauche, droite) du feuillage d'origine à la hauteur du modèle z, resserré pour rester dans le cadre."""
    row = p["rows"](p["screen0"] + z * SIN, r)
    if row is None:
        return None
    return max(row[0], p["frame_x"][0] + 0.1 * r), min(row[1], p["frame_x"][1] - 0.1 * r)


def fir_layers(p):
    """Sapin : étages en cône empilés (x, y, z du bas de l'étage, rayon), du plus large au plus étroit ; la hauteur
    de chaque étage est dans p["layer_h"]."""
    r0, r1 = p["r"]
    zb = p["z0"] + FIR_TRUNK                                    # étages remontés : le tronc se voit sous le sapin
    T = (p["top"] - 0.04 - p["screen0"]) / SIN                  # la pointe au haut du feuillage d'origine
    n = FIR_LAYERS
    zt = (T + 0.8 * zb / n) / (1 + 0.8 / n)                     # bas du dernier étage (pointe = zt + 0,8 pas)
    step = (zt - zb) / n
    p["layer_h"] = step * 1.7
    widest = max((row_span(p, zb + i * step, r1) or (p["x"], p["x"]) for i in range(n // 2)),
                 key=lambda sp: sp[1] - sp[0])
    R0 = max(0.2, (widest[1] - widest[0]) / 2 * 0.82)          # un peu moins large que l'original : sapin élancé
    cx = (widest[0] + widest[1]) / 2
    # chaque étage nettement plus étroit que celui du dessous : son bord sort de l'ombre portée de l'étage du dessus
    return [(cx, p["base_y"], zb + i * step, R0 * (1 - 0.62 * i / n)) for i in range(n)]


def willow_anchors(p):
    """Saule : bouts des branches arquées, d'où pendent les filaments (x, y, z, rayon de la petite touffe), répartis
    sur la largeur du feuillage d'origine, aux deux tiers de la hauteur."""
    rng = random.Random(p["seed"])
    z = p["z0"] + (p["z1"] - p["z0"]) * 0.85
    span = (p["frame_x"][0] + 0.17, p["frame_x"][1] - 0.17)     # les filaments restent dans le cadre du feuillage
    n = 5
    return [(span[0] + 0.08 + (span[1] - span[0] - 0.16) * k / (n - 1) + rng.uniform(-0.04, 0.04),
             p["base_y"] + rng.uniform(-0.15, 0.2), z + rng.uniform(-0.25, 0.25), 0.07) for k in range(n)]


def clumps(p):
    """Touffes du feuillage (x, y, z, rayon), en étages calés sur la silhouette de l'original : à chaque étage, des
    touffes côte à côte sur la largeur du feuillage d'origine à cette hauteur (deux pour un arbre étroit, plus pour
    un arbre large, une seule à la pointe d'un sapin) ; des touffes devant, entre deux étages, un étage sur deux
    (pas au premier : on doit voir le tronc) ; une au sommet."""
    rng = random.Random(p["seed"])
    r0, r1 = p["r"]
    tiers = max(3, round((p["z1"] - p["z0"]) / (r1 * 2.1)) + 1)
    balls = []
    for i in range(tiers):
        t = i / (tiers - 1)
        z = p["z0"] + (p["z1"] - p["z0"]) * t
        row = p["rows"](p["screen0"] + z * SIN, r1)
        if row is None:
            continue
        left = max(row[0], p["frame_x"][0] + 0.1 * r1) + r1 * 1.15
        right = min(row[1], p["frame_x"][1] - 0.1 * r1) - r1 * 1.15
        rad = r0 + (r1 - r0) * min(1.0, (row[1] - row[0]) / (4 * r1))
        if right - left < r1 * 0.5:                            # étroit : une touffe au milieu
            xs = [(left + right) / 2]
        else:
            n = max(2, round((right - left) / (r1 * 1.5)) + 1)
            xs = [left + (right - left) * k / (n - 1) for k in range(n)]
        for x in xs:
            balls.append((x + rng.uniform(-0.04, 0.04), p["base_y"] + rng.uniform(0, 0.25), z + rng.uniform(-0.1, 0.1),
                          rad * rng.uniform(0.9, 1.05)))
        if i % 2 == 1 and len(xs) > 1:                         # touffes de devant, entre deux du même étage
            side = rng.choice((-1, 1))
            for a, b in zip(xs, xs[1:]):
                balls.append(((a + b) / 2 + side * (b - a) * 0.12, p["base_y"] - 0.35, z + r1 * 0.5,
                              rad * rng.uniform(0.85, 1.0)))
    balls.append((p["x"], p["base_y"] + 0.1, p["z1"] + r0 * 0.4, r0))       # sommet
    return balls


def state_balls(p, state):
    """Touffes d'un état du feuillage : toutes (plein), ou une partie, plus petites (abîmé, presque nu)."""
    keep, k = STATES[state]
    balls = crown_balls(p)
    if keep < 1:
        rng = random.Random(p["seed"] * 31 + state)
        chosen = set(rng.sample(range(len(balls)), max(1, round(len(balls) * keep))))
        balls = [b for i, b in enumerate(balls) if i in chosen]
    return [(x, y, z, r * k) for x, y, z, r in balls]


def clump(loc, r, m, seed, tag):
    """Touffe en chou-fleur : une grosse bosse centrale, une couronne de bosses autour, deux ou trois dessus ;
    dessous aplati. Toutes ses bosses portent le même numéro `tag` (contour autour de la touffe, pas entre ses bosses)."""
    rng = random.Random(seed)
    x, y, z = loc
    parts = [(0, 0, 0, r * 0.78)]
    for k in range(7):
        a = 2 * math.pi * k / 7 + rng.uniform(-0.3, 0.3)
        parts.append((math.cos(a) * r * 0.55, math.sin(a) * r * 0.45, rng.uniform(-0.12, 0.05) * r, r * rng.uniform(0.42, 0.52)))
    for k in range(3):
        a = 2 * math.pi * k / 3 + rng.uniform(0, 1)
        parts.append((math.cos(a) * r * 0.25, math.sin(a) * r * 0.2, r * 0.42, r * rng.uniform(0.38, 0.46)))
    for dx, dy, dz, rr in parts:
        o = sphere((x + dx, y + dy, z + dz), rr, m, squash=0.82)
        o["touffe"] = tag


def aim(dx, dy, dz):
    """Rotation (Euler XYZ) qui oriente l'axe z d'une primitive le long de (dx, dy, dz)."""
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    return (math.acos(dz / L), 0, math.atan2(dx, -dy))


def add_trunk(p, stump=False):
    """Tronc épais, un peu tordu, racines étalées au sol, branches qui montent vers les touffes."""
    bark = couleur("ecorce", BARK_BY.get(p["design"], BARK))
    x0, y0 = p["x"], p["base_y"]
    rng = random.Random(p["seed"])
    tr = p.get("trunk_r", 0.21) * (0.7 if p["design"] == "parasol" else 1.0)
    k = math.sqrt(tr / 0.21)                                    # racines et pied : grossissent moins vite que le tronc
    for deg in (165, 230, 310, 15, 90):                         # racines : grosses, courtes, qui plongent au sol ;
        a = math.radians(deg + rng.uniform(-12, 12))            # celles de devant plus courtes (bas du cadre)
        L = 0.38 * k * rng.uniform(0.85, 1.15) * (1 - 0.45 * max(0.0, -math.sin(a)))
        reach = lambda L: 0.16 * k + L * 0.9                    # bout de la racine, depuis l'axe du tronc
        if "room_side" in p:                                    # elle ne sort pas du cadre du tronc
            L = min(L, (p["room_side"] / max(0.2, abs(math.cos(a))) - 0.16 * k) / 0.9)
            if math.sin(a) < 0:
                L = min(L, (p["room_down"] / (COS * -math.sin(a)) - 0.16 * k) / 0.9)
        if L < 0.08:
            continue
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.13 * k, radius2=0.07 * k, depth=L)
        o = bpy.context.object
        o.data.materials.append(bark)
        o.rotation_euler = aim(math.cos(a), math.sin(a), -0.35)
        o.location = (x0 + math.cos(a) * (0.16 * k + L * 0.4), y0 + math.sin(a) * (0.16 * k + L * 0.4), 0.08 * k)
        bpy.ops.object.shade_smooth()
        o["touffe"] = 0
    h = 0.42 if stump else p["z1"] * 0.85            # le tronc monte dans le feuillage, de plus en plus fin
    lean = rng.uniform(-0.08, 0.08) if p["design"] != "saule" else 0.35 * h / 2   # le saule penche à droite
    if p["design"] == "noueux" and not stump:                   # fourche en Y : deux grosses branches
        fz = p["z0"] * 0.6
        for side in (-1, 1):
            tx, tz = x0 + side * p["width"] * 0.9, p["z1"] * 0.8
            L = math.sqrt((tx - x0) ** 2 + (tz - fz) ** 2)
            bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=tr * 0.7, radius2=0.06, depth=L,
                                            location=((x0 + tx) / 2, y0, (fz + tz) / 2))
            o = bpy.context.object
            o.rotation_euler = aim(tx - x0, 0, tz - fz)
            o.data.materials.append(bark)
            bpy.ops.object.shade_smooth()
            o["touffe"] = 52 + (side > 0)
        h = fz + 0.2
    if p["design"] == "geant" and not stump:                    # géant : trois troncs massifs qui s'écartent
        for j, (dx, dy) in enumerate(((-0.55, 0.1), (0.05, -0.2), (0.6, 0.15))):
            bx, by = x0 + dx * tr, y0 + dy * tr
            tx, ty, tz = x0 + dx * tr * 2.4, y0 + dy * tr * 1.5, p["z0"] + 0.25
            L = math.sqrt((tx - bx) ** 2 + (ty - by) ** 2 + tz ** 2)
            bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=tr * 0.62, radius2=tr * 0.3, depth=L,
                                            location=((bx + tx) / 2, (by + ty) / 2, tz / 2))
            o = bpy.context.object
            o.rotation_euler = aim(tx - bx, ty - by, tz)
            o.data.materials.append(bark)
            bpy.ops.object.shade_smooth()
            o["touffe"] = 50 + j                                # un trait autour de chaque tronc
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=tr, radius2=tr * 0.9 if stump else 0.05, depth=h,
                                    location=(x0 + lean / 2, y0, h / 2))
    o = bpy.context.object
    o.rotation_euler = aim(lean, 0, h)
    o.data.materials.append(bark)
    bpy.ops.object.shade_smooth()
    o["touffe"] = 0
    if p["design"] != "geant" or stump:                         # pied évasé (le géant a ses trois troncs)
        flare = min(tr * 1.3, p.get("room_down", 9) / COS, p.get("room_side", 9))
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=flare, radius2=tr * 0.9, depth=0.22 * k,
                                        location=(x0, y0, 0.11 * k))
        o = bpy.context.object
        o.data.materials.append(bark)
        bpy.ops.object.shade_smooth()
        o["touffe"] = 0
    cx, cy, z = x0 + lean, y0, h
    if stump:                                                   # coupe claire sur le dessus
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=tr * 0.88, depth=0.02, location=(cx, cy, z + 0.01))
        o = bpy.context.object
        o.data.materials.append(couleur("coupe", "#e0bc84"))
        o["touffe"] = 0
        return
    if p["design"] == "saule":                                  # branches nues arquées : montée, puis retombée
        for bx, by, bz, r in crown_balls(p):
            sz = z * 0.75
            sx = x0 + lean * sz / h
            ax, az = (sx + bx) / 2, bz + 0.55
            for (ux, uy, uz), (vx, vy, vz), r1 in (((sx, y0, sz), (ax, by, az), 0.06), ((ax, by, az), (bx, by, bz), 0.04)):
                L = math.sqrt((vx - ux) ** 2 + (vy - uy) ** 2 + (vz - uz) ** 2)
                bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r1, radius2=r1 * 0.6, depth=L,
                                                location=((ux + vx) / 2, (uy + vy) / 2, (uz + vz) / 2))
                o = bpy.context.object
                o.rotation_euler = aim(vx - ux, vy - uy, vz - uz)
                o.data.materials.append(bark)
                o["touffe"] = 0
                o = sphere((vx, vy, vz), r1 * 0.6, bark)        # coude arrondi
                o["touffe"] = 0
        return
    for i, (bx, by, bz, r) in enumerate(crown_balls(p)):        # une branche vers chaque touffe
        sz = max(0.5, min(z, bz - r * 0.9 - 0.2))          # départ sur le tronc, un peu sous la touffe
        sx, sy = x0 + lean * sz / h, y0
        dx, dy, dz = bx - sx, by - sy, bz - sz
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.06 * max(1, k * 0.8), radius2=0.03, depth=L,
                                        location=(sx + dx / 2, sy + dy / 2, sz + dz / 2))
        o = bpy.context.object
        o.rotation_euler = aim(dx, dy, dz)
        o.data.materials.append(bark)
        o["touffe"] = 0


def add_leaves(p, state):
    leaf = couleur("feuillage", LEAF, paliers=LEAF_STEPS)
    for i, (x, y, z, r) in enumerate(state_balls(p, state)):
        if p["design"] == "sapin":                              # étage en cône, cerné à part
            D = p["layer_h"] * STATES[state][1]
            bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r, radius2=0, depth=D, location=(x, y, z + D / 2),
                                            end_fill_type="NOTHING")   # sans disque dessous : il fausserait le lissage
            o = bpy.context.object
            o.data.materials.append(leaf)
            bpy.ops.object.shade_smooth()
            o.visible_shadow = False                            # pas d'ombre portée d'un étage sur l'autre :
            o["touffe"] = i + 1                                 # chacun clair à gauche, ombré à droite
        elif p["design"] == "saule":
            willow_strands((x, y, z), r, leaf, p, p["seed"] * 7 + i, i + 1)
        elif p["design"] == "dome":                             # boules lisses (première variante)
            o = sphere((x, y, z), r * 1.1, leaf, squash=0.88)
            o["touffe"] = i + 1
        else:
            clump((x, y, z), r, leaf, p["seed"] * 7 + i, i + 1)


def willow_strands(loc, r, m, p, seed, tag):
    """Saule : une petite touffe et, dessous, des filaments qui pendent (cônes fins, pointe en bas)."""
    rng = random.Random(seed)
    x, y, z = loc
    o = sphere((x, y, z), r, m, squash=0.8)
    o["touffe"] = tag
    span = p["z1"] - p["z0"]
    for k in range(12):
        dx, dy = rng.uniform(-0.13, 0.13), rng.uniform(-0.08, 0.1)
        L = span * rng.uniform(0.4, 0.8)
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.025, radius2=0.008, depth=L,
                                        location=(x + dx + dx * 0.15, y + dy, z - L / 2))
        o = bpy.context.object
        o.rotation_euler = aim(dx * 0.3, 0, -1)
        o.data.materials.append(m)
        bpy.ops.object.shade_smooth()
        o["touffe"] = tag


# --- rendu ------------------------------------------------------------------------------------------------------

def touffe_ids(path, size):
    """Rendu « identifiant » de la scène courante (caméra déjà posée par render_scene) : chaque objet en aplat d'une
    valeur propre à son numéro de touffe (propriété « touffe »), sans anticrénelage. Renvoie la carte des numéros
    (-1 hors de l'objet)."""
    import lib
    sc = bpy.context.scene
    flats = {}
    for o in sc.objects:
        if o.type != "MESH":
            continue
        t = int(o.get("touffe", 0))
        if t not in flats:
            flats[t] = lib._flat(f"id-{t}", "ShaderNodeEmission", (t + 1) / 64)
        for i in range(len(o.data.materials)):
            o.data.materials[i] = flats[t]
    filt = sc.render.filter_size
    sc.render.filter_size = 0.01
    lib._render(path, size, "Raw", depth="16")
    sc.render.filter_size = filt
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED).astype(np.float32)
    os.remove(path)
    ids = np.round(im[:, :, 2] / 65535 * 64).astype(np.int32) - 1
    ids[im[:, :, 3] < 32768] = -1
    return ids


def outline_ids(im, ids, hex_, px):
    """Trait de `px` px (à la taille de `im`) le long des frontières entre numéros de touffe et autour de l'objet,
    à la couleur de contour de la matière ; `ids` est rendu à une taille multiple de `im`."""
    k = ids.shape[0] // im.shape[0]
    edge = np.zeros(ids.shape, bool)
    edge[:-1] |= ids[:-1] != ids[1:]
    edge[1:] |= ids[:-1] != ids[1:]
    edge[:, :-1] |= ids[:, :-1] != ids[:, 1:]
    edge[:, 1:] |= ids[:, :-1] != ids[:, 1:]
    r = max(1, round(px * k / 2))
    line = cv2.dilate(edge.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2))
    line = cv2.resize(line.astype(np.float32), (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA)
    lc = [round(255 * (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))
          for c in line_color(S._lin(hex_))]
    a = im[:, :, 3:4] / 255.0
    la = line[:, :, None]
    out = im.astype(np.float32)
    out[:, :, :3] = (out[:, :, :3] * a * (1 - la) + np.array(lc[::-1]) * la) / np.maximum(a * (1 - la) + la, 1e-6)
    out[:, :, 3] = np.maximum(im[:, :, 3], line * 255)
    return np.clip(out, 0, 255).astype(np.uint8)


def canvas(tmp, build, line=None):
    """Rend la scène (`build()`) sur le canevas centré sur l'entité, avec un trait autour de chaque touffe (et de
    l'objet) à la teinte de la matière `line` (#rrggbb)."""
    reset()
    build()
    render_scene(tmp, size=CANVAS, scale=CANVAS / PX, pitch_deg=S.PITCH_BUILDING_DEG, outline=False)
    im = cv2.imread(tmp, cv2.IMREAD_UNCHANGED)
    ss = S.SUPERSAMPLE
    ids = touffe_ids(tmp + ".id.png", (CANVAS * ss, CANVAS * ss))
    return outline_ids(im, ids, line, LINE_PX)


def cut(im, pic):
    """Cadre d'un fichier (taille et shift du prototype) dans le canevas."""
    return crop_centered(im, (pic["width"], pic["height"]), (pic["shift"][0] * TILE_PX, pic["shift"][1] * TILE_PX))


def write(out, pic, im):
    p = os.path.join(out, path_of(pic).replace("graphics/", ""))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cv2.imwrite(p, im)
    return p


def render_variation(out, v, stump, p):
    """Tous les fichiers d'une variante. Renvoie (feuillages des 3 états, tronc), découpés à leur cadre."""
    tmp = os.path.join(out, "_calque.png")
    trunk = cut(canvas(tmp, lambda: add_trunk(p), BARK), v["trunk"])
    write(out, v["trunk"], trunk)
    leaves, normals = [], []
    for s in range(3):
        im = canvas(tmp, lambda: add_leaves(p, s), LEAF)
        leaves.append(cut(im, v["leaves"]))
        if "normal" in v:                                       # le saule (06) n'en a pas
            n = cut(im, v["normal"])
            n[:, :, :3] = FLAT_NORMAL
            normals.append(n)
    write(out, v["leaves"], np.hstack(leaves))
    if normals:
        write(out, v["normal"], np.hstack(normals))
    shadows = []
    for s in range(4):
        def build(s=s):
            reset()
            add_trunk(p)
            if s < 3:
                add_leaves(p, s)
        big = render_shadow(build, tmp, (SHADOW_CANVAS, SHADOW_CANVAS), SHADOW_CANVAS / PX, p["shear"])
        shadows.append(cut(big, v["shadow"]))
    write(out, v["shadow"], np.hstack(shadows))
    if stump:
        write(out, stump, cut(canvas(tmp, lambda: add_trunk(p, stump=True), BARK), stump))
    if os.path.exists(tmp):
        os.remove(tmp)
    return leaves, trunk


def produce(out, species):
    vs, stumps = variations(species)
    stump_of = {re.search(r"-([a-z])-stump", s["filename"]).group(1): s for s in stumps}
    for i, v in enumerate(vs):
        letter = re.search(r"-([a-z])-trunk", v["trunk"]["filename"]).group(1)
        p = fit(v, seed=int(species) * 100 + i, design=DESIGNS.get(species, "chou-fleur"))
        render_variation(out, v, stump_of.get(letter), p)
        print("OK", species, letter, {k: round(x, 2) for k, x in p.items() if isinstance(x, float)})


# --- aperçu ---------------------------------------------------------------------------------------------------------

TINTS = [(191, 255, 111), (209, 200, 152), (252, 255, 133)]   # premières couleurs du prototype tree-02 (RGB)


def tint(im, rgb):
    out = im.copy()
    out[:, :, :3] = (im[:, :, :3].astype(np.float32) * np.array(rgb[::-1]) / 255).astype(np.uint8)
    return out


def over(dst, src, x, y):
    h, w = src.shape[:2]
    a = src[:, :, 3:4] / 255.0
    d = dst[y:y + h, x:x + w]
    d[:, :, :3] = (src[:, :, :3] * a + d[:, :, :3] * (1 - a)).astype(np.uint8)
    d[:, :, 3] = np.maximum(d[:, :, 3], src[:, :, 3])


def compose(layers, size=(260, 480), foot=None):
    """Calques (image, pic du prototype) posés autour de la position de l'entité, à l'échelle des fichiers."""
    c = np.zeros((size[1], size[0], 4), np.uint8)
    foot = foot or (size[0] // 2, 400)
    for im, pic in layers:
        h, w = im.shape[:2]
        over(c, im, round(foot[0] + pic["shift"][0] * TILE_PX - w / 2), round(foot[1] + pic["shift"][1] * TILE_PX - h / 2))
    return c


def apercu(out):
    """Planche de travail (mesures à l'œil) ; ce qu'on montre à Bastien, c'est la vue en jeu."""
    vs, _ = variations("02")
    v = vs[0]
    leaves, trunk = render_variation(os.path.join(out, "_apercu"), v, None, fit(v, seed=200))
    w = v["leaves"]["width"]
    cells = [("original", compose([(load(v["trunk"]), v["trunk"]),
                                   (tint(load(v["leaves"])[:, :w], TINTS[0]), v["leaves"])]))]
    for name, t in (("vert", TINTS[0]), ("gris (jeu)", TINTS[1]), ("automne A", (255, 150, 60)),
                    ("automne B", (255, 120, 45)), ("automne C", (255, 185, 80))):
        cells.append((name, compose([(trunk, v["trunk"]), (tint(leaves[0], t), v["leaves"])])))
    cells.append(("abime", compose([(trunk, v["trunk"]), (tint(leaves[1], TINTS[0]), v["leaves"])])))
    grass = (58, 104, 92)                                      # BGR, sol d'herbe neutre des planches
    W, H = 260, 480
    rows = 40 + H + 20 + H // 2 + 20 + H // 4 + 10
    sheet = np.full((rows, W * len(cells), 3), (38, 32, 30), np.uint8)
    for i, (name, im) in enumerate(cells):
        bg = np.full((H, W, 3), grass, np.float32)
        a = im[:, :, 3:4] / 255.0
        big = (im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
        sheet[40:40 + H, i * W:(i + 1) * W] = big
        y = 60 + H
        for k in (2, 4):                                       # zoom 2 et zoom 1 du jeu (32 px par case)
            small = cv2.resize(big, (W // k, H // k), interpolation=cv2.INTER_AREA)
            x = i * W + (W - W // k) // 2
            sheet[y:y + H // k, x:x + W // k] = small
            y += H // k + 20
        cv2.putText(sheet, name, (i * W + 8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (90, 214, 255), 2)
    path = os.path.join(out, "apercu.png")
    cv2.imwrite(path, sheet)
    print("OK", path)


SPECIES = ["01", "02", "03", "04", "05", "06", "07", "08", "09"]


def apercu_especes(out, species=SPECIES):
    """Planche de travail : la variante a de chaque espèce, originale puis refaite, teinte de sa première couleur."""
    d = json.load(open(DUMP))
    cells = []
    for sp in species:
        v = variations(sp)[0][0]
        rgb = d["tree"][f"tree-{sp}"]["colors"][0]
        t = (rgb["r"], rgb["g"], rgb["b"])
        p = fit(v, seed=int(sp) * 100, design=DESIGNS.get(sp, "chou-fleur"))
        leaves, trunk = render_variation(os.path.join(out, "_especes"), v, None, p)
        w = v["leaves"]["width"]
        cells.append(compose([(load(v["trunk"]), v["trunk"]), (tint(load(v["leaves"])[:, :w], t), v["leaves"])],
                             size=(360, 480)))
        cells.append(compose([(trunk, v["trunk"]), (tint(leaves[0], t), v["leaves"])], size=(360, 480)))
    W, H = 360, 480
    sheet = np.full((H * 2 + 20, W * len(species), 3), (38, 32, 30), np.uint8)
    for i, im in enumerate(cells):
        bg = np.full((H, W, 3), (58, 104, 92), np.float32)
        a = im[:, :, 3:4] / 255.0
        sheet[(i % 2) * (H + 20):(i % 2) * (H + 20) + H, (i // 2) * W:(i // 2 + 1) * W] = \
            (im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8)
        if i % 2 == 0:
            cv2.putText(sheet, species[i // 2], ((i // 2) * W + 8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (90, 214, 255), 2)
    path = os.path.join(out, "especes.png")
    cv2.imwrite(path, sheet)
    print("OK", path)


if __name__ == "__main__":
    out, cmd = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if cmd == "apercu":
        apercu(out)
    elif cmd == "especes":
        apercu_especes(out, sys.argv[3].split(",") if len(sys.argv) > 3 else SPECIES)
    else:
        for sp in cmd.split(","):
            produce(out, sp)
