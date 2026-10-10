"""Souterrains et répartiteurs en pixel art (16 px par case, x4 à l'export), aux couleurs des convoyeurs.

Souterrain : planche 4 x 4 de cellules de 48 px d'art (le jeu y lit 192 px) ; colonnes = nord, est, sud, ouest ;
rangées = sortie, entrée, sortie en insertion latérale, entrée en insertion latérale. Le capot couvre la moitié de la case
du côté enterré.
Répartiteur : 4 orientations, 32 images chacune (planche 8 x 4). Deux piliers et une cloison laissent voir les deux
tapis ; un rail à engrenages traverse le milieu et deux capots à chevrons coiffent l'entrée.

Usage : python pixel/pillow/belt_structures.py <dossier_sortie>   (aperçu)
"""
import math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, BELT
from pixutil import autoshade
import belt

STEEL = (P["steel_dark"], P["steel"], P["steel_mid"], P["steel_light"])
FLOW = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


def plate_color(a, b, tier):
    """Plaque à chevrons : `a` avance dans le sens du flux, `b` va en travers (période 4)."""
    light, dark = BELT[tier]
    c = abs((b % 4) - 1.5)
    ph = (a + (1 if c > 1 else 0)) % 4
    return light if ph == 1 else dark if ph == 0 else belt.BASE[tier]


def rect_mask(size, rects):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for x0, y0, x1, y1 in rects:
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    return m


def paint_plate(img, rect, flow, tier, inset=1):
    """Remplit l'intérieur d'un rectangle (x0, y0, x1, y1) avec la plaque à chevrons orientée selon `flow`."""
    x0, y0, x1, y1 = rect
    for y in range(y0 + inset, y1 - inset):
        for x in range(x0 + inset, x1 - inset):
            if flow == (0, -1):
                a, b = (y1 - 1 - y), x
            elif flow == (0, 1):
                a, b = (y - y0), x
            elif flow == (1, 0):
                a, b = (x - x0), y
            else:
                a, b = (x1 - 1 - x), y
            img.putpixel((x, y), plate_color(a, b, tier))


def with_shadow(img, mask, offset=(3, 2)):
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste((20, 15, 30, 85), offset, mask)
    out.alpha_composite(img)
    return out


# ---------------------------------------------------------------- souterrain
def underground_cell(direction, entering, tier):
    """Cellule de 48 x 48 px d'art ; la case occupe [16, 32[. Capot de 10 px sur le côté enterré, plus 2 px de face avant."""
    fx, fy = FLOW[direction]
    ahead = entering                 # entrée : capot devant (sens du flux) ; sortie : capot derrière
    s = 1 if ahead else -1
    hood = [16, 16, 32, 32]
    if fx:
        hood[0], hood[2] = (22, 32) if fx * s > 0 else (16, 26)
    else:
        hood[1], hood[3] = (22, 32) if fy * s > 0 else (16, 26)
    x0, y0, x1, y1 = hood
    mask = rect_mask((48, 48), [(x0, y0, x1, y1 + 2)])
    img = autoshade(mask, STEEL)
    paint_plate(img, (x0, y0, x1, y1), (fx, fy), tier, inset=2)
    for x in range(x0 + 1, x1 - 1):                       # face avant (hauteur du capot)
        img.putpixel((x, y1), P["steel"])
        img.putpixel((x, y1 + 1), P["steel_dark"])
    return with_shadow(img, mask)


def underground_sheet(tier):
    out = Image.new("RGBA", (48 * 4, 48 * 4), (0, 0, 0, 0))
    for col, direction in enumerate("NESW"):
        for row, entering in enumerate((False, True, False, True)):
            if row >= 2 and direction in "NS":
                continue
            out.alpha_composite(underground_cell(direction, entering, tier), (48 * col, 48 * row))
    return out


# ---------------------------------------------------------------- répartiteur
def gear_mask(size, cx, cy, r, teeth, ph):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    for i in range(teeth):
        a = 2 * math.pi * (i + ph) / teeth
        x, y = round(cx + (r + 0.6) * math.cos(a)), round(cy + (r + 0.6) * math.sin(a))
        d.rectangle((x - 1, y - 1, x, y), fill=255)
    return m


def splitter_frame(direction, phase, tier):
    """Une image du répartiteur. Les pièces sont définies pour le nord (32 x 16) puis tournées."""
    k = "NESW".index(direction)
    horizontal = direction in "NS"
    fw, fh = (40, 22) if horizontal else (22, 40)
    ox, oy = (4, 3) if horizontal else (3, 4)

    def tr(x, y):                       # point local (nord, 32 x 16) -> point de l'image
        if k == 0:
            return x + ox, y + oy
        if k == 2:
            return 32 - x + ox, 16 - y + oy
        if k == 1:
            return 16 - y + ox, x + oy
        return y + ox, 32 - x + oy

    def tr_rect(x0, y0, x1, y1):
        (ax, ay), (bx, by) = tr(x0, y0), tr(x1, y1)
        return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)

    posts = [tr_rect(*r) for r in ((0, 0, 2, 16), (30, 0, 32, 16), (15, 0, 17, 16))]
    rail = tr_rect(2, 8, 30, 11)
    caps = [tr_rect(2, 0, 15, 5), tr_rect(17, 0, 30, 5)]
    size = (fw, fh)
    shape = rect_mask(size, posts + [rail] + caps)

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    img.alpha_composite(autoshade(rect_mask(size, posts), STEEL))
    img.alpha_composite(autoshade(rect_mask(size, [rail]), STEEL))
    flow = FLOW[direction]
    for cap in caps:
        img.alpha_composite(autoshade(rect_mask(size, [cap]), STEEL))
        paint_plate(img, cap, flow, tier, inset=1)
    # deux engrenages sur le rail, en sens inverses ; 2 dents par boucle (6 dents) pour que la boucle se referme
    for n, (gx, gy) in enumerate(((8.5, 9.5), (23.5, 9.5))):
        cx, cy = tr(gx, gy)
        ph = (2 * phase) * (1 if n == 0 else -1)
        g = autoshade(gear_mask(size, cx, cy, 2.6, 6, ph), (P["steel_dark"], P["steel"], P["orange"], P["tan"]))
        img.alpha_composite(g)
        img.putpixel((round(cx), round(cy)), P["steel_dark"])
    return with_shadow(img, shape)


def splitter_sheet(direction, tier):
    frames = [splitter_frame(direction, i / 32, tier) for i in range(32)]
    w, h = frames[0].size
    out = Image.new("RGBA", (w * 8, h * 4), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.alpha_composite(f, (w * (i % 8), h * (i // 8)))
    return out


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    prev = Image.new("RGBA", (48 * 4 * 3 * 3, 48 * 4 * 3 + 260), P["grass"])
    for i, tier in enumerate(("yellow", "red", "blue")):
        u = underground_sheet(tier)
        prev.alpha_composite(u.resize((u.width * 3, u.height * 3), Image.NEAREST), (i * 48 * 4 * 3, 0))
        for j, d in enumerate("NESW"):
            f = splitter_frame(d, 0.0, tier)
            prev.alpha_composite(f.resize((f.width * 3, f.height * 3), Image.NEAREST), (i * 576 + j * 140, 48 * 4 * 3 + 5 + (0 if d in "NS" else 0)))
    prev.save(f"{o}/belt_struct_preview.png")
