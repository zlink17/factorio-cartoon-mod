"""Inserters en pixel art : tige de base, main ouverte / fermée, ombres et plateforme à 4 orientations.

Tout est dessiné à 1 px d'art = 2 px de jeu (comme les assembleurs) : les mains et la tige sont exportées x8 (le jeu
les affiche à l'échelle 0,25), la plateforme x4 (échelle 0,5).
Usage : python pixel/pillow/inserter.py <dossier_sortie>   (aperçu)
"""
import math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, hx
from pixutil import autoshade, silhouette

# contour, ombre, moyen, lumière
RAMPS = {
    "inserter": (P["maroon"], P["orange_dark"], P["orange"], P["tan"]),
    "fast-inserter": (P["blue_out"], P["blue_dark"], P["blue"], P["blue_light"]),
    "long-handed-inserter": (hx("5a2030"), hx("a83a48"), hx("dc6a5e"), hx("ffa898")),
    "burner-inserter": (P["steel_dark"], P["steel"], P["steel_mid"], P["steel_light"]),
}
BASE_SIZE = (4, 17)      # tige : 32 x 136 à x8
HAND_SIZE = (9, 21)      # main : 72 x 168 à x8
PLAT_SIZE = (26, 20)     # plateforme : 104 x 80 à x4


def poly_mask(size, draw):
    m = Image.new("L", size, 0)
    draw(ImageDraw.Draw(m))
    return m


def base_bone(kind):
    ramp = RAMPS[kind]

    def draw(d):
        d.ellipse((0, 0, 3, 3), fill=255)            # articulation du haut
        d.rectangle((0, 3, 3, 12), fill=255)
        d.rectangle((1, 13, 2, 16), fill=255)        # embout du bas
    img = autoshade(poly_mask(BASE_SIZE, draw), ramp)
    img.putpixel((1, 1), P["steel_light"])
    img.putpixel((2, 2), P["steel_dark"])
    return img


def hand(kind, opened):
    ramp = RAMPS[kind]

    def draw(d):
        gap = 0 if opened else 2
        d.rectangle((0 + gap, 0, 1 + gap, 4), fill=255)                # doigts
        d.rectangle((7 - gap - 1 + 1, 0, 8 - gap, 4), fill=255) if False else d.rectangle((7 - gap, 0, 8 - gap, 4), fill=255)
        d.rectangle((0 + (0 if opened else 1), 3, 8 - (0 if opened else 1), 5), fill=255)   # traverse
        d.rectangle((2, 5, 6, 17), fill=255)                           # bras
        d.ellipse((1, 16, 7, 20), fill=255)                            # coude
    img = autoshade(poly_mask(HAND_SIZE, draw), ramp)
    out_c = ramp[0]
    for y in (8, 11, 14):                                              # petites fenêtres sombres du bras
        img.putpixel((4, y), out_c)
        img.putpixel((4, y + 1), out_c)
    img.putpixel((4, 18), P["steel_light"])
    img.putpixel((4, 19), P["steel_dark"])
    return img


def platform(kind, direction):
    """Plateforme en tripode : un moyeu rond, trois pieds (le quatrième côté est libre)."""
    ramp = RAMPS[kind]
    cx, cy = PLAT_SIZE[0] / 2, PLAT_SIZE[1] / 2
    # pieds dans l'orientation 0 (nord) : une patte vers le haut, deux vers le bas ; puis rotation de 90° x direction
    legs0 = [(0, -8.5), (-8.5, 6), (8.5, 6)]
    m = Image.new("L", PLAT_SIZE, 0)
    d = ImageDraw.Draw(m)
    d.ellipse((cx - 5, cy - 4, cx + 4, cy + 3), fill=255)
    for lx, ly in legs0:
        for _ in range(direction):
            lx, ly = -ly, lx                                           # rotation de 90° (horaire)
        tx, ty = cx + lx, cy + ly * 0.85 - 0.5
        d.line([(cx, cy), (tx, ty)], fill=255, width=3)
        d.ellipse((tx - 2, ty - 1.5, tx + 2, ty + 2), fill=255)
    body = autoshade(m, ramp)
    bd = ImageDraw.Draw(body)
    bd.ellipse((cx - 3, cy - 2.5, cx + 2, cy + 1.5), fill=ramp[0])
    bd.ellipse((cx - 2, cy - 1.5, cx + 1, cy + 0.5), fill=P["steel_mid"])
    body.putpixel((int(cx) - 1, int(cy) - 1), P["steel_dark"])
    # ombre au sol, en bas à droite
    shadow = Image.new("RGBA", PLAT_SIZE, (0, 0, 0, 0))
    shadow.paste((20, 15, 30, 85), (3, 2), m)
    shadow.alpha_composite(body)
    return shadow


def sprites(kind):
    """Renvoie les images de l'inserter au format d'export (déjà agrandies)."""
    up = lambda im, k: im.resize((im.width * k, im.height * k), Image.NEAREST)
    base, op, cl = base_bone(kind), hand(kind, True), hand(kind, False)
    plat = Image.new("RGBA", (PLAT_SIZE[0] * 4, PLAT_SIZE[1]), (0, 0, 0, 0))
    for k in range(4):
        plat.alpha_composite(platform(kind, k), (PLAT_SIZE[0] * k, 0))
    return {
        "hand-base": up(base, 8), "hand-open": up(op, 8), "hand-closed": up(cl, 8),
        "platform": up(plat, 4),
        "shadow": {"hand-base": up(silhouette(base, (0, 0, 0, 255)), 8),
                   "hand-open": up(silhouette(op, (0, 0, 0, 255)), 8),
                   "hand-closed": up(silhouette(cl, (0, 0, 0, 255)), 8)},
    }


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    prev = Image.new("RGBA", (4 * 340, 260), hx("c8a060"))
    for i, kind in enumerate(RAMPS):
        s = sprites(kind)
        x = i * 340
        prev.alpha_composite(s["hand-base"], (x + 5, 5))
        prev.alpha_composite(s["hand-open"], (x + 50, 5))
        prev.alpha_composite(s["hand-closed"], (x + 130, 5))
        prev.alpha_composite(s["platform"], (x, 180))
    prev.save(f"{o}/inserter_preview.png")
