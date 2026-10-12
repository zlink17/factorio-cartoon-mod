"""Arbres de Nauvis en cel-shading : tronc et feuillage en touffes « chou-fleur » (modèle 3D), d'après l'image
de Bastien celshading/concept/cibles/arbre-bastien.jpg (12 octobre) : arbre élancé en étages, dessus clair, dessous
foncé, trait autour de chaque touffe, branches entre les touffes, tronc évasé à racines.

Usage : python celshading/blender/tree.py <dossier_sortie> apercu
          planche de travail de la variante 02-a (original / rendus teints) dans <sortie>/apercu.png
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


def extent(pic, frame=0, thr=128):
    """Boîte de la partie opaque d'une image du fichier, en px depuis la position de l'entité (x droite, y bas)."""
    im = load(pic)
    w, h = pic["width"], pic["height"]
    a = im[:h, frame * w:(frame + 1) * w, 3]
    ys, xs = np.where(a > thr)
    ox, oy = pic["shift"][0] * TILE_PX - w / 2, pic["shift"][1] * TILE_PX - h / 2
    return xs.min() + ox, xs.max() + ox, ys.min() + oy, ys.max() + oy


def fit(v, seed):
    """Paramètres du modèle d'une variante, d'après son original (en unités du monde)."""
    l0, l1, t0, t1 = extent(v["leaves"])
    _, _, _, base = extent(v["trunk"])
    _, s1, _, _ = extent(v["shadow"], 0, 40)
    top, bottom = -t0 / PX, -t1 / PX           # haut et bas du feuillage au-dessus de l'entité (unités, à l'écran)
    lift = -base / PX                          # pied du tronc au-dessus de l'entité (unités, à l'écran)
    half = (l1 - l0) / 2 / PX                  # demi-largeur du feuillage (unités)
    r_max = half * 0.52                        # deux touffes côte à côte remplissent la largeur
    p = {
        "seed": seed, "base_y": lift / COS + ROOT_BACK, "x": (l0 + l1) / 2 / PX,
        "z0": (bottom + r_max * 0.8 + TRUNK_SHOW - lift - ROOT_BACK * COS) / SIN,   # recul du pied compensé
        "z1": (top - r_max * 1.25 - lift - ROOT_BACK * COS) / SIN,         # à l'écran : on le compense en hauteur
        "width": max(0.05, half - r_max * 1.0), "r": (r_max * 0.8, r_max),
    }
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
    """Touffes du feuillage (x, y, z, rayon), en étages : deux touffes côte à côte par étage (gauche, droite), une
    au centre devant un étage sur deux, une au sommet. Les étages du milieu sont les plus larges."""
    rng = random.Random(p["seed"])
    r0, r1 = p["r"]
    tiers = max(3, round((p["z1"] - p["z0"]) / (r1 * 2.1)) + 1)
    balls = []
    for i in range(tiers):
        t = i / (tiers - 1)
        z = p["z0"] + (p["z1"] - p["z0"]) * t
        bulge = math.sin(math.pi * (0.2 + 0.7 * t))
        rad = r0 + (r1 - r0) * bulge
        spread = p["width"] * (0.55 + 0.45 * bulge)
        side = 1 if i % 2 else -1
        balls.append((p["x"] - spread * rng.uniform(0.8, 1.0), p["base_y"] + rng.uniform(0, 0.25), z + rng.uniform(-0.1, 0.1),
                      rad * rng.uniform(0.9, 1.05)))
        balls.append((p["x"] + spread * rng.uniform(0.8, 1.0), p["base_y"] + rng.uniform(0, 0.25), z + rng.uniform(-0.1, 0.1),
                      rad * rng.uniform(0.9, 1.05)))
        if i % 2 == 1:                                           # touffe de devant, à cheval entre deux étages
                                                                 # (pas au premier : on doit voir le tronc)
            balls.append((p["x"] + side * spread * 0.25, p["base_y"] - 0.35, z + r1 * 0.5, rad * rng.uniform(0.85, 1.0)))
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
    bark = couleur("ecorce", BARK)
    x0, y0 = p["x"], p["base_y"]
    rng = random.Random(p["seed"])
    for deg in (165, 230, 310, 15, 90):                         # racines : grosses, courtes, qui plongent au sol ;
        a = math.radians(deg + rng.uniform(-12, 12))            # celles de devant plus courtes (bas du cadre)
        L = 0.38 * rng.uniform(0.85, 1.15) * (1 - 0.45 * max(0.0, -math.sin(a)))
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.13, radius2=0.07, depth=L)
        o = bpy.context.object
        o.data.materials.append(bark)
        o.rotation_euler = aim(math.cos(a), math.sin(a), -0.35)
        o.location = (x0 + math.cos(a) * (0.16 + L * 0.4), y0 + math.sin(a) * (0.16 + L * 0.4), 0.08)
        bpy.ops.object.shade_smooth()
        o["touffe"] = 0
    h = 0.42 if stump else p["z1"] * 0.85            # le tronc monte dans le feuillage, de plus en plus fin
    lean = rng.uniform(-0.08, 0.08)
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.21, radius2=0.19 if stump else 0.05, depth=h,
                                    location=(x0 + lean / 2, y0, h / 2))
    o = bpy.context.object
    o.rotation_euler = aim(lean, 0, h)
    o.data.materials.append(bark)
    bpy.ops.object.shade_smooth()
    o["touffe"] = 0
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.27, radius2=0.19, depth=0.22, location=(x0, y0, 0.11))
    o = bpy.context.object                                      # pied évasé
    o.data.materials.append(bark)
    bpy.ops.object.shade_smooth()
    o["touffe"] = 0
    cx, cy, z = x0 + lean, y0, h
    if stump:                                                   # coupe claire sur le dessus
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.19, depth=0.02, location=(cx, cy, z + 0.01))
        o = bpy.context.object
        o.data.materials.append(couleur("coupe", "#e0bc84"))
        o["touffe"] = 0
        return
    for i, (bx, by, bz, r) in enumerate(crown_balls(p)):        # une branche vers chaque touffe
        sz = max(0.5, min(z, bz - r * 0.9 - 0.2))          # départ sur le tronc, un peu sous la touffe
        sx, sy = x0 + lean * sz / h, y0
        dx, dy, dz = bx - sx, by - sy, bz - sz
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.06, radius2=0.03, depth=L,
                                        location=(sx + dx / 2, sy + dy / 2, sz + dz / 2))
        o = bpy.context.object
        o.rotation_euler = aim(dx, dy, dz)
        o.data.materials.append(bark)
        o["touffe"] = 0


def add_leaves(p, state):
    leaf = couleur("feuillage", LEAF, paliers=LEAF_STEPS)
    for i, (x, y, z, r) in enumerate(state_balls(p, state)):
        clump((x, y, z), r, leaf, p["seed"] * 7 + i, i + 1)


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
        n = cut(im, v["normal"])
        n[:, :, :3] = FLAT_NORMAL
        normals.append(n)
    write(out, v["leaves"], np.hstack(leaves))
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
        p = fit(v, seed=int(species) * 100 + i)
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


def compose(layers, size=(260, 480), foot=(130, 400)):
    """Calques (image, pic du prototype) posés autour de la position de l'entité, à l'échelle des fichiers."""
    c = np.zeros((size[1], size[0], 4), np.uint8)
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


if __name__ == "__main__":
    out, cmd = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if cmd == "apercu":
        apercu(out)
    else:
        for sp in cmd.split(","):
            produce(out, sp)
