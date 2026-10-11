"""Original, image cible et rendu Blender côte à côte : en grand, en zoom x2 (cible et rendu), et à la taille du jeu.

Usage : python tools/concept/compare.py <guides> <cible> <rendu> <sortie.png> [--sol herbe|plateforme|gris]
<cible> : l'image retenue telle que sortie de ComfyUI (taille de la toile) ou déjà au cadre du sprite ;
<rendu> : le sprite produit par le générateur Blender, au cadre de l'original.
Écrit <sortie.png> et <sortie>-zoom.png.
"""
import argparse, json, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, PX, SOLS, sol, to_frame

ap = argparse.ArgumentParser()
ap.add_argument("guides")
ap.add_argument("cible")
ap.add_argument("rendu")
ap.add_argument("out")
ap.add_argument("--sol", choices=sorted(SOLS), default="gris")
a = ap.parse_args()

info = json.load(open(os.path.join(a.guides, "guide-sprite.json")))
W, H = info["frame"]
shift = info.get("shift", [0, 0])
orig = Image.open(os.path.join(DATA, info["sprite"])).convert("RGBA").crop((0, 0, W, H))
cible = Image.open(a.cible).convert("RGBA")
cible = cible if cible.size == (W, H) else to_frame(a.cible, a.guides, info)
rendu = Image.open(a.rendu).convert("RGBA")


def monde(s, n=2):
    step = max(1, round(W / PX))
    tw, th = step * n + 2, max(4, round(H / PX) + 2)
    c = sol(a.sol, tw, th)
    for i in range(n):
        cx, cy = (1 + step * i + step / 2) * PX, th / 2 * PX - shift[1] * PX
        c.alpha_composite(s, (round(cx + shift[0] * PX - W / 2), round(cy + shift[1] * PX - H / 2)))
    return c.resize((c.width // 2, c.height // 2), Image.LANCZOS)


font = ImageFont.load_default(size=26)
items = [("original", orig), ("cible", cible), ("blender", rendu)]
views = [monde(s) for _, s in items]
cw = max(W, views[0].width) + 12
out = Image.new("RGBA", (cw * 3, 40 + H + views[0].height + 20), (30, 32, 38, 255))
d = ImageDraw.Draw(out)
for i, ((n, s), v) in enumerate(zip(items, views)):
    d.text((i * cw + cw // 2, 6), n, font=font, fill=(255, 214, 90), anchor="mt")
    out.alpha_composite(s, (i * cw + (cw - W) // 2, 40))
    out.alpha_composite(v, (i * cw + (cw - v.width) // 2, 40 + H + 10))
out.save(a.out)

z = Image.new("RGBA", (W * 4 + 20, H * 2), (30, 32, 38, 255))
z.alpha_composite(cible.resize((W * 2, H * 2), Image.LANCZOS), (0, 0))
z.alpha_composite(rendu.resize((W * 2, H * 2), Image.LANCZOS), (W * 2 + 20, 0))
zoom = os.path.splitext(a.out)[0] + "-zoom.png"
z.save(zoom)
print(a.out, zoom)
