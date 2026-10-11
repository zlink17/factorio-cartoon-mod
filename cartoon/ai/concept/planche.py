"""Planches de comparaison des variantes ComfyUI : en grand, et à la taille du jeu sur une plateforme.

Chaque génération est remise au cadre du sprite (guide-cadre.txt) et détourée par la silhouette de l'original.
Usage : python planche.py <guides> <sortie.png> <image> [<image>...]
"""
import sys
import os
from PIL import Image, ImageDraw, ImageFont

GUIDES, OUT, FILES = sys.argv[1], sys.argv[2], sys.argv[3:]
D = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data/space-age/graphics/entity/thruster/"
W, H, PX = 264, 542, 64
ox, oy, bw, bh = map(int, open(f"{GUIDES}/guide-cadre.txt").read().split())
mask = Image.open(f"{GUIDES}/guide-masque.png").convert("L")
orig = Image.open(D + "thruster-1.png").convert("RGBA").crop((0, 0, W, H))
bckg = Image.open(D + "thruster-bckg.png").convert("RGBA")


def to_sprite(path):
    g = Image.open(path).convert("RGB").resize(mask.size, Image.LANCZOS)
    g.putalpha(mask)
    return g.crop((ox, oy, ox + bw, oy + bh)).resize((W, H), Image.LANCZOS)


def monde(sprite, n=2):
    tw, th = 4 * n + 1, 9
    c = Image.new("RGBA", (tw * PX, th * PX), (8, 10, 22, 255))
    d = ImageDraw.Draw(c)
    for tx in range(tw):
        for ty in range(4):
            d.rectangle((tx * PX, ty * PX, tx * PX + PX - 1, ty * PX + PX - 1), fill=(96, 98, 104), outline=(78, 80, 86))
    cy = 4 * PX - 2.5 * PX
    for i in range(n):
        cx = (0.5 + 4 * i + 2) * PX
        c.alpha_composite(bckg, (round(cx + 0.0625 * PX - bckg.width / 2), round(cy + 0.734375 * PX - bckg.height / 2)))
        c.alpha_composite(sprite, (round(cx + 0.046875 * PX - W / 2), round(cy + 1.78125 * PX - H / 2)))
    return c.resize((c.width // 2, c.height // 2), Image.LANCZOS)   # zoom 1 du jeu : 32 px par case


sprites = [orig] + [to_sprite(f) for f in FILES]
names = ["original"] + [os.path.splitext(os.path.basename(f))[0] for f in FILES]
LABEL = 40
font = ImageFont.load_default(size=30)
cell_w = max(W, monde(orig).width) + 12
top = Image.new("RGBA", (cell_w * len(sprites), LABEL + H + monde(orig).height + 24), (30, 32, 38, 255))
d = ImageDraw.Draw(top)
for i, s in enumerate(sprites):
    d.text((i * cell_w + cell_w // 2, 6), names[i], font=font, fill=(255, 214, 90), anchor="mt")
    top.alpha_composite(s, (i * cell_w + (cell_w - W) // 2, LABEL + 6))
    m = monde(s)
    top.alpha_composite(m, (i * cell_w + (cell_w - m.width) // 2, LABEL + H + 18))
top.save(OUT)
