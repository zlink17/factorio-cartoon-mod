"""Arbres de Nauvis redessinés en aplats : tronc, feuillage (3 états), carte de normales, souche.

Usage : python cartoon/terrain/trees.py <dossier_sortie> [espèce[,espèce...]|toutes]
        espèce = 01 à 09, ou un arbre mort : dead-dry-hairy-tree, dead-grey-trunk, dead-tree-desert, dry-hairy-tree,
        dry-tree

Comme les buissons touffus (`decoratives.paint_lobes`) : on lit chaque image d'origine pour savoir *où* dessiner,
et on y pose des lobes ronds (feuillage) ou un aplat (tronc, souche), à la même emprise. Les fichiers gardent la
taille et le cadrage de l'original ; leurs dimensions et décalages viennent des prototypes (dump des données).
- feuillage : en tons neutres, car le jeu le teinte (couleur tirée au hasard dans `colors` pour chaque arbre) ;
  une image par état (plein, abîmé, presque nu), lobes posés sur le feuillage d'origine de cet état ;
- normales : plates (face à la caméra) sous notre feuillage : l'éclairage ne dessine pas de relief qui n'est pas là ;
- tronc et souche : aplat brun, bord gauche éclairé, bord droit sombre ;
- ombres (4 images) : celles de l'original, noires et unies, gardées (notre feuillage suit la même silhouette).
Écrit base/entity/tree/<espèce>/<fichier>.png.
"""
import json, os, re, sys, zlib
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decoratives import FACTORIO_DATA, SS, Rng, hx, outlined, paint_lobes

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUMP = os.path.join(ROOT, ".cache", "data-raw-dump.json")
LEAVES = ("#40463c", "#6b7364", "#9ca690")      # tons neutres du feuillage (le jeu les teinte)
BARK = ("#4a3424", "#6b4a32", "#8e6646")
# feuillage par espèce : (forme des lobes, rayon en px du fichier) ; 01 est un conifère, 06 un saule presque nu
LEAF_STYLE = {"01": ("fir", 25), "06": ("flat", None)}   # saule : filaments tombants, en aplat (pas de lobes)
LEAF_DEFAULT = ("disc", 30)
# arbres morts ou secs : une image par variante, ombre comprise
DEAD = ["dead-dry-hairy-tree", "dead-grey-trunk", "dead-tree-desert", "dry-hairy-tree", "dry-tree"]
FLAT_NORMAL = (255, 128, 128)                   # BGR : normale (0, 0, 1), face à la caméra


def variations():
    """{espèce: [variation, ...]} pour les arbres de base (une variation = dict trunk/leaves/normal)."""
    d = json.load(open(DUMP))
    out = {}
    for name, t in d["tree"].items():
        m = re.fullmatch(r"tree-(\d\d)", name)
        if m and t.get("variations"):
            out[m.group(1)] = t["variations"]
    return out


def path_of(pic):
    return pic["filename"].replace("__base__/graphics/", "base/graphics/")


def load(pic):
    return cv2.imread(os.path.join(FACTORIO_DATA, path_of(pic)), cv2.IMREAD_UNCHANGED)


def out_path(out, pic):
    p = os.path.join(out, path_of(pic).replace("graphics/", ""))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def leaves_mask(frame):
    """Feuillage d'origine d'une image : assez opaque, trous comblés, bords lissés."""
    m = (frame[:, :, 3] > 100).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.erode(m, np.ones((2, 2), np.uint8))


def render_bark(orig, tones=BARK, body=None, keep_shadow=False):
    """Tronc ou souche : silhouette lissée de l'original ; ses trois tons viennent de la luminosité de l'original,
    lissée puis répartie en tiers (sombre, moyen, clair) : on garde ainsi les troncs multiples, creux et racines.
    `body` : masque de la silhouette (défaut : alpha > 90). `keep_shadow` : recopie l'ombre intégrée de l'original
    (pixels presque noirs) sous notre dessin, pour les arbres morts dont l'ombre est dans le sprite."""
    h, w = orig.shape[:2]
    H, W = h * SS, w * SS
    if body is None:
        body = orig[:, :, 3] > 90
    a = cv2.resize(body.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    m = (cv2.GaussianBlur(a, (0, 0), SS * 0.8) > 0.5).astype(np.uint8)
    cols = [hx(t) for t in tones]
    lum = cv2.cvtColor(orig[:, :, :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
    lum = cv2.GaussianBlur(cv2.resize(lum, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), SS * 2.5)
    inside = lum[m > 0]
    color = np.zeros((H, W, 3), np.float32)
    if inside.size:
        lo, hi = np.percentile(inside, (35, 75))
        color[m > 0] = cols[1]
        color[(m > 0) & (lum < lo)] = cols[0]
        color[(m > 0) & (lum > hi)] = cols[2]
    im = outlined(color, m, tuple(int(c * 0.55) for c in cols[0]), w, h)
    if keep_shadow:
        sh = (orig[:, :, :3].max(2) < 35) & (orig[:, :, 3] > 0) & (im[:, :, 3] == 0)
        im[sh] = orig[sh]
    return im


def render_leaves(orig, frames, seed, style=LEAF_DEFAULT):
    """Feuillage : une image par état, côte à côte. Renvoie (image BGRA, masques par image à la taille du fichier)."""
    h, W = orig.shape[:2]
    w = W // frames
    cols = [hx(t) for t in LEAVES]
    out_col = tuple(int(c * 0.55) for c in cols[0])
    sheet = np.zeros((h, W, 4), np.uint8)
    masks = []
    for k in range(frames):
        frame = orig[:, k * w:(k + 1) * w]
        if style[0] == "flat":
            im = render_bark(frame, LEAVES, body=frame[:, :, 3] > 100)
            sheet[:, k * w:(k + 1) * w] = im
            masks.append(im[:, :, 3])
            continue
        color, m = paint_lobes(leaves_mask(frame), style[1], cols, Rng(seed + k), step_k=1.0, density=0.35,
                               shape=style[0], dark_edge=0.45)
        im = outlined(color, m, out_col, w, h)
        sheet[:, k * w:(k + 1) * w] = im
        masks.append(im[:, :, 3])
    return sheet, masks


def render_normal(leaves_pic, normal_pic, masks):
    """Normales plates sous notre feuillage, recalées du cadre du feuillage vers celui des normales (décalages)."""
    lw, lh = leaves_pic["width"], leaves_pic["height"]
    nw, nh = normal_pic["width"], normal_pic["height"]
    frames = normal_pic.get("frame_count", 1)
    dx = (normal_pic["shift"][0] - leaves_pic["shift"][0]) * 64 + (lw - nw) / 2
    dy = (normal_pic["shift"][1] - leaves_pic["shift"][1]) * 64 + (lh - nh) / 2
    sheet = np.zeros((nh, nw * frames, 4), np.uint8)
    for k in range(min(frames, len(masks))):
        a = cv2.warpAffine(masks[k], np.float32([[1, 0, -dx], [0, 1, -dy]]), (nw, nh))  # normale(x) = feuillage(x+dx)
        sheet[:, k * nw:(k + 1) * nw, :3] = FLAT_NORMAL
        sheet[:, k * nw:(k + 1) * nw, 3] = a
    return sheet


def build_species(species, var_list, out):
    for v in var_list:
        trunk = v["trunk"]
        cv2.imwrite(out_path(out, trunk), render_bark(load(trunk)))
        leaves = v["leaves"]
        sheet, masks = render_leaves(load(leaves), leaves.get("frame_count", 1),
                                     zlib.crc32(leaves["filename"].encode()), LEAF_STYLE.get(species, LEAF_DEFAULT))
        cv2.imwrite(out_path(out, leaves), sheet)
        if "normal" in v:
            cv2.imwrite(out_path(out, v["normal"]), render_normal(leaves, v["normal"], masks))
        stump = trunk["filename"].replace("-trunk.png", "-stump.png")
        if os.path.exists(os.path.join(FACTORIO_DATA, path_of({"filename": stump}))):
            pic = {"filename": stump}
            cv2.imwrite(out_path(out, pic), render_bark(load(pic)))


def build_dead(name, out):
    """Arbres morts ou secs : bois en aplat, ombre intégrée de l'original conservée."""
    d = json.load(open(DUMP))
    for pic in d["tree"][name]["pictures"]:
        orig = load(pic)
        body = (orig[:, :, 3] > 90) & (orig[:, :, :3].max(2) >= 35)
        cv2.imwrite(out_path(out, pic), render_bark(orig, body=body, keep_shadow=True))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "trees_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    var = variations()
    for sp in (sorted(var) + DEAD if which == "toutes" else which.split(",")):
        if sp in DEAD:
            build_dead(sp, out)
        else:
            build_species(sp, var[sp], out)
        print("OK", sp, flush=True)
