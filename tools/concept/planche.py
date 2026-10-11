"""Planche de variantes : chaque image porte son identifiant (nom du fichier), en grand et à la taille du jeu.

Usage : python tools/concept/planche.py <guides> <sortie.png> <image> [<image>...] [--sol herbe|plateforme|gris]
                                         [--n 2] [--pixel] [--detour original|fond]

Chaque génération est remise au cadre du sprite original (guide-sprite.json et guide-cadre.txt, écrits par
prepare.py) et détourée par la silhouette de l'original (ou, avec --detour fond, par son propre fond uni). La première colonne est l'original. En bas : `--n` exemplaires
posés côte à côte au zoom 1 du jeu (32 px par case), sur un sol neutre, au décalage (`shift`) du prototype.
--pixel (mod pixel) : en dessous, la même planche ramenée à 16 px d'art par case (common.pixelise).
"""
import argparse, json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, PX, SOLS, pixelise, sol, to_frame

ap = argparse.ArgumentParser()
ap.add_argument("guides")
ap.add_argument("out")
ap.add_argument("images", nargs="+")
ap.add_argument("--sol", choices=sorted(SOLS), default="gris")
ap.add_argument("--n", type=int, default=2, help="exemplaires côte à côte dans la vue « en jeu »")
ap.add_argument("--pixel", action="store_true", help="ajoute la version à 16 px d'art par case")
ap.add_argument("--detour", choices=("original", "fond"), default="original",
                help="détourage : silhouette de l'original, ou fond uni de la génération (variantes libres)")
a = ap.parse_args()

info = json.load(open(os.path.join(a.guides, "guide-sprite.json")))
W, H = info["frame"]
shift = info.get("shift", [0, 0])
orig = Image.open(os.path.join(DATA, info["sprite"])).convert("RGBA").crop((0, 0, W, H))


def monde(sprite):
    """`n` exemplaires côte à côte, espacés de la largeur du sprite arrondie à la case, au zoom 1."""
    step = max(1, round(W / PX))
    tw, th = step * a.n + 2, max(4, round(H / PX) + 2)
    c = sol(a.sol, tw, th)
    for i in range(a.n):
        cx, cy = (1 + step * i + step / 2) * PX, th / 2 * PX - shift[1] * PX
        c.alpha_composite(sprite, (round(cx + shift[0] * PX - W / 2), round(cy + shift[1] * PX - H / 2)))
    return c.resize((c.width // 2, c.height // 2), Image.LANCZOS)


sprites = [orig] + [to_frame(f, a.guides, info, a.detour) for f in a.images]
names = ["original"] + [os.path.splitext(os.path.basename(f))[0] for f in a.images]
rows = [sprites] + ([[pixelise(sp, shift) for sp in sprites]] if a.pixel else [])
LABEL = 40
font = ImageFont.load_default(size=30)
views = [[monde(sp) for sp in row] for row in rows]
cell_w = max(W, views[0][0].width) + 12
row_h = H + views[0][0].height + 24
out = Image.new("RGBA", (cell_w * len(sprites), LABEL + row_h * len(rows)), (30, 32, 38, 255))
d = ImageDraw.Draw(out)
for i, name in enumerate(names):
    d.text((i * cell_w + cell_w // 2, 6), name, font=font, fill=(255, 214, 90), anchor="mt")
for r, (row, row_views) in enumerate(zip(rows, views)):
    y = LABEL + r * row_h
    for i, (sp, v) in enumerate(zip(row, row_views)):
        out.alpha_composite(sp, (i * cell_w + (cell_w - W) // 2, y + 6))
        out.alpha_composite(v, (i * cell_w + (cell_w - v.width) // 2, y + H + 18))
out.save(a.out)
print(a.out)
