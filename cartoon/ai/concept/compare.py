"""Planche : original | image cible | rendu Blender, en grand et en situation (zoom 1).

Usage : compare.py <cible au cadre du sprite> <rendu> <sortie>
"""
import sys
from PIL import Image, ImageDraw, ImageFont
D = "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data/space-age/graphics/entity/thruster/"
W, H, PX = 264, 542, 64
orig = Image.open(D + "thruster-1.png").convert("RGBA").crop((0, 0, W, H))
bckg = Image.open(D + "thruster-bckg.png").convert("RGBA")
cible = Image.open(sys.argv[1]).convert("RGBA")
rendu = Image.open(sys.argv[2]).convert("RGBA")
def monde(s, n=2):
    tw = 4 * n + 1
    c = Image.new("RGBA", (tw * PX, 9 * PX), (8, 10, 22, 255)); d = ImageDraw.Draw(c)
    for tx in range(tw):
        for ty in range(4):
            d.rectangle((tx * PX, ty * PX, tx * PX + PX - 1, ty * PX + PX - 1), fill=(96, 98, 104), outline=(78, 80, 86))
    cy = 1.5 * PX
    for i in range(n):
        cx = (0.5 + 4 * i + 2) * PX
        c.alpha_composite(bckg, (round(cx + 4 - bckg.width / 2), round(cy + 47 - bckg.height / 2)))
        c.alpha_composite(s, (round(cx + 3 - W / 2), round(cy + 114 - H / 2)))
    return c.resize((c.width // 2, c.height // 2), Image.LANCZOS)
items = [("original", orig), ("cible", cible), ("blender", rendu)]
cw = 300; font = ImageFont.load_default(size=26)
out = Image.new("RGBA", (cw * 3, 40 + H + 300), (30, 32, 38, 255)); d = ImageDraw.Draw(out)
for i, (n, s) in enumerate(items):
    d.text((i * cw + cw // 2, 6), n, font=font, fill=(255, 214, 90), anchor="mt")
    out.alpha_composite(s, (i * cw + (cw - W) // 2, 40))
    m = monde(s); out.alpha_composite(m, (i * cw + (cw - m.width) // 2, 40 + H + 10))
out.save(sys.argv[3])
