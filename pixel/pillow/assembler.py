"""Assembleur 3x3 en pixel art, dessiné à la main (en code) à 16 px par case puis agrandi x4 (64 px par case).

Usage : python pixel/pillow/assembler.py <dossier_sortie>
Écrit : assembler.png (1x), assembler_hr.png (x4, plus-proche-voisin), assembler_shadow.png, preview.png.
"""
import math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P

W, H = 56, 68
SCALE = 4
N_FRAMES = 32       # comme l'original : planche de 8 x 4 images
GEAR_PITCHES = 2    # dents parcourues par chaque engrenage sur la boucle (entier, pour que la boucle se referme)


def put(d, pts, c):
    for x, y in pts:
        d.point((x, y), P[c])


def dither(d, box, a, b):
    """Damier 1 px entre deux couleurs."""
    x0, y0, x1, y1 = box
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            d.point((x, y), P[a if (x + y) % 2 == 0 else b])


def gear(d, cx, cy, r, teeth, ph, body, light, dark, hub, thick=2):
    """Engrenage vu à ~30° (ellipse écrasée), avec épaisseur. `ph` = avance en dents (0..1 = une boucle)."""
    ry = r * 0.85
    def ring(y, tooth_c, disc_c, outline):
        for i in range(teeth):
            a = 2 * math.pi * (i + ph) / teeth
            x, yy = round(cx + (r + 1) * math.cos(a)), round(y + (ry + 1) * math.sin(a))
            d.rectangle((x - 1, yy - 1, x + 1, yy + 1), fill=outline)
        d.ellipse((cx - r - 1, y - ry - 1, cx + r + 1, y + ry + 1), fill=outline)
        for i in range(teeth):
            a = 2 * math.pi * (i + ph) / teeth
            x, yy = round(cx + (r + 1) * math.cos(a)), round(y + (ry + 1) * math.sin(a))
            d.rectangle((x - 1, yy - 1, x, yy), fill=tooth_c)
        d.ellipse((cx - r, y - ry, cx + r, y + ry), fill=disc_c)
    for t in range(thick, 0, -1):
        ring(cy + t, P[dark], P[dark], P[dark])
    ring(cy, P[body], P[body], P[dark])
    d.arc((cx - r + 1, cy - ry + 1, cx + r - 1, cy + ry - 1), 180, 280, fill=P[light])
    d.ellipse((cx - r // 2, cy - r // 2 * 0.85, cx + r // 2, cy + r // 2 * 0.85), fill=P[dark])
    d.ellipse((cx - r // 2 + 1, cy - r // 2 * 0.85 + 1, cx + r // 2 - 1, cy + r // 2 * 0.85 - 1), fill=P[hub])
    d.point((cx, cy), P[dark])


def thick_line(d, p0, p1, w, c, outline):
    d.line([p0, p1], fill=P[outline], width=w + 2)
    d.line([p0, p1], fill=P[c], width=w)


def arm(d, base, phase, offset, reach=(75, 25)):
    """Bras articulé à deux segments qui va chercher une pièce (boucle sur `phase`)."""
    s = 2 * math.pi * (phase + offset)
    a1 = math.radians(200 + 15 * math.sin(s))
    a2 = math.radians(reach[0] + reach[1] * math.sin(s + 1.2))
    e = (base[0] + 9 * math.cos(a1), base[1] + 9 * math.sin(a1))
    h = (e[0] + 8 * math.cos(a2), e[1] + 8 * math.sin(a2))
    thick_line(d, base, e, 3, "steel_light", "steel_dark")
    thick_line(d, e, h, 3, "steel_mid", "steel_dark")
    d.ellipse((base[0] - 3, base[1] - 3, base[0] + 3, base[1] + 3), fill=P["steel_dark"])
    d.ellipse((base[0] - 2, base[1] - 2, base[0] + 2, base[1] + 2), fill=P["steel_mid"])
    d.point((base[0] - 1, base[1] - 1), P["white"])
    d.ellipse((e[0] - 2, e[1] - 2, e[0] + 2, e[1] + 2), fill=P["steel_dark"])
    d.point((round(e[0]), round(e[1])), P["tan"])
    hx_, hy_ = round(h[0]), round(h[1])
    d.rectangle((hx_ - 2, hy_ - 1, hx_ + 2, hy_ + 1), fill=P["orange_dark"])
    d.rectangle((hx_ - 2, hy_ + 1, hx_ - 1, hy_ + 3), fill=P["steel_dark"])
    d.rectangle((hx_ + 1, hy_ + 1, hx_ + 2, hy_ + 3), fill=P["steel_dark"])


def cyl(d, cx, yt, yb, rx, body, light, dark, out):
    """Cylindre vertical vu à ~30° : flancs, base et disque supérieur elliptiques (couleurs = noms de P)."""
    ry = max(1, round(rx * 0.5))
    d.ellipse((cx - rx - 1, yb - ry - 1, cx + rx + 1, yb + ry + 1), fill=P[out])
    d.rectangle((cx - rx - 1, yt, cx + rx + 1, yb), fill=P[out])
    d.ellipse((cx - rx, yb - ry, cx + rx, yb + ry), fill=P[dark])
    d.rectangle((cx - rx, yt, cx + rx, yb), fill=P[body])
    d.rectangle((cx - rx, yt, cx - rx, yb), fill=P[light])
    d.rectangle((cx + rx, yt, cx + rx, yb), fill=P[dark])
    d.ellipse((cx - rx - 1, yt - ry - 1, cx + rx + 1, yt + ry + 1), fill=P[out])
    d.ellipse((cx - rx, yt - ry, cx + rx, yt + ry), fill=P[light])


def floor_shadow(d, box):
    """Ombre portée sur le plateau (aplat plus sombre, bord tramé)."""
    d.rectangle(box, fill=P["orange_dark"])


def piston(d, x, phase, offset=0.0, slim=False):
    """Piston vertical posé sur le plateau : fourreau fixe, tige et tête qui coulissent (`slim` : version fine)."""
    s = math.sin(2 * math.pi * (phase + offset))
    hy = 20 + round(3 * s)
    rs, rh = (2, 2) if slim else (3, 4)
    d.ellipse((x - rs, 34, x + rs + 3, 38), fill=P["orange_dark"])
    cyl(d, x, 29, 35, rs, "steel", "steel_light", "steel_dark", "steel_dark")
    d.rectangle((x - (not slim), hy + 4, x + (not slim), 29), fill=P["steel_dark"])
    d.point((x, hy + 6), P["white"])
    cyl(d, x, hy, hy + 4, rh, "steel_mid", "steel_light", "steel", "steel_dark")
    d.point((x - 1, hy), P["white"])


def draw_assembler(phase=0.0, tier=2):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = lambda n: P[f"w{tier}_{n}"]
    pn = lambda n: P[f"p{tier}_{n}"]

    # engrenages en laiton qui dépassent du bord arrière (tournent à l'envers)
    for cx in (15, 40):
        gear(d, cx, 8, 5, 8, -GEAR_PITCHES * phase, "tan", "cyan_light", "maroon", "orange", thick=2)

    # silhouette en tronc de pyramide : dessus étroit, pans latéraux visibles qui s'évasent vers le bas
    d.polygon([(8, 10), (47, 10), (52, 23), (52, 59), (3, 59), (3, 23)], fill=w("out"))
    d.polygon([(7, 12), (7, 46), (4, 58), (4, 24)], fill=w("mid"))              # flanc gauche, éclairé
    d.line([(5, 26), (5, 57)], fill=w("light"))
    d.polygon([(48, 12), (48, 46), (51, 58), (51, 24)], fill=w("dark"))          # flanc droit, dans l'ombre
    d.line([(50, 26), (50, 57)], fill=w("mid"))
    for y in range(34, 57, 2):
        d.point((4, y), w("dark"))                                               # tramage du bas du flanc gauche

    # dessus du rebord : surface claire
    d.rectangle((7, 10, 48, 47), fill=w("out"))
    d.rectangle((8, 11, 47, 46), fill=w("light"))
    d.rectangle((46, 11, 47, 46), fill=w("mid"))
    put(d, [(9, 12), (10, 12)], "white")

    # cuvette : mur arrière intérieur visible, flancs, plancher en cuivre rouillé
    d.rectangle((10, 13, 45, 43), fill=w("out"))
    d.rectangle((11, 14, 44, 18), fill=w("dark"))
    for x in range(13, 43, 6):
        d.rectangle((x, 16, x + 3, 16), fill=w("mid"))
    d.rectangle((11, 18, 44, 18), fill=w("out"))
    d.rectangle((11, 19, 44, 42), fill=P["orange"])
    d.rectangle((11, 19, 12, 42), fill=P["orange_dark"])
    d.rectangle((43, 19, 44, 42), fill=P["tan"])
    d.rectangle((13, 19, 42, 20), fill=P["orange_dark"])
    for box in ((14, 39, 28, 42), (32, 38, 42, 42)):
        dither(d, box, "orange", "orange_dark")
    put(d, [(19, 40), (20, 40), (40, 22), (30, 21)], "red")

    # objets du plateau, dessinés sur un calque décalé vers l'avant pour les centrer sur le plancher
    main, layer = d, Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # moteur : boîtier (dessus clair, face avant, ombre au sol) surmonté de deux bobines
    floor_shadow(d, (14, 32, 21, 37))
    d.rectangle((11, 24, 18, 36), fill=P["steel_dark"])
    d.rectangle((12, 25, 17, 27), fill=P["steel_light"])
    d.rectangle((12, 28, 17, 35), fill=P["steel"])
    d.rectangle((12, 28, 12, 35), fill=P["steel_mid"])
    d.rectangle((13, 30, 16, 34), fill=pn("out"))
    d.rectangle((14, 31, 15, 33), fill=pn("mid"))
    blink = (phase * 2) % 1 < 0.5
    d.rectangle((14, 31, 15, 33), fill=P["cyan"] if blink else pn("dark"))
    d.point((14, 31), P["cyan_light"] if blink else pn("mid"))
    for x in (13, 16):
        cyl(d, x, 19, 25, 1, "orange", "tan", "red", "maroon")

    # piston, grand engrenage monté sur un axe (ombre au sol)
    if tier >= 3:   # deux vérins fins, en alternance
        piston(d, 22, phase, 0.0, slim=True)
        piston(d, 27, phase, 0.5, slim=True)
    else:
        piston(d, 24, phase, 0.0)
    d.ellipse((30, 35, 41, 38), fill=P["orange_dark"])
    gear(d, 34, 30, 5, 10, GEAR_PITCHES * phase, "steel_mid", "white", "steel_dark", "orange", thick=3)

    # bras articulés sur leur socle (niveau 2 : un, niveau 3 : deux)
    if tier >= 2:
        d.ellipse((38, 26, 46, 29), fill=P["orange_dark"])
        cyl(d, 42, 21, 26, 2, "steel", "steel_light", "steel_dark", "steel_dark")
        arm(d, (42, 21), phase, 0.0)
    if tier >= 3:
        d.ellipse((38, 36, 46, 39), fill=P["orange_dark"])
        cyl(d, 42, 31, 36, 2, "steel", "steel_light", "steel_dark", "steel_dark")
        arm(d, (42, 31), phase, 0.5, reach=(55, 10))   # plus bas sur le plateau : débattement réduit
    d = main
    img.alpha_composite(layer, (0, 4))

    # lèvre avant du rebord puis paroi avant évasée avec ses quatre panneaux triangulaires
    d.rectangle((10, 43, 45, 43), fill=w("out"))
    d.rectangle((8, 47, 47, 47), fill=w("mid"))
    d.polygon([(7, 48), (48, 48), (52, 59), (3, 59)], fill=w("out"))
    d.polygon([(8, 49), (47, 49), (51, 58), (4, 58)], fill=w("mid"))
    d.rectangle((8, 49, 47, 50), fill=w("dark"))
    d.line([(8, 51), (4, 58)], fill=w("light"))
    d.line([(47, 51), (51, 58)], fill=w("dark"))
    d.line([(4, 58), (51, 58)], fill=w("dark"))
    for i in range(4):
        x0 = 7 + 11 * i
        d.polygon([(x0, 57), (x0 + 9, 57), (x0 + 4, 52)], fill=pn("out"))
        d.polygon([(x0 + 4, 53), (x0 + 4, 56), (x0 + 7, 56)], fill=pn("dark"))
        d.polygon([(x0 + 4, 53), (x0 + 4, 56), (x0 + 2, 56)], fill=pn("mid"))
        d.point((x0 + 4, 53), P["white"])

    # pieds sombres
    d.rectangle((5, 59, 50, 63), fill=w("out"))
    d.rectangle((6, 60, 49, 62), fill=P["steel_dark"])
    d.rectangle((6, 60, 49, 60), fill=P["steel"])
    put(d, [(8, 61), (47, 61), (19, 61), (35, 61)], "steel_light")
    return img


def shadow_of(img):
    a = img.getchannel("A").point(lambda v: 255 if v else 0)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste((0, 0, 0, 110), (6, 5), a)
    return out


def preview(spr, sh):
    bg = Image.new("RGBA", (W + 16, H + 16), P["grass_light"])
    d = ImageDraw.Draw(bg)
    for x, y in ((6, 10), (60, 20), (14, 66), (66, 62)):
        d.point((x, y), P["white"]); d.point((x + 1, y), P["white"])
    # l'ombre du style de référence est un aplat vert plus foncé
    flat = Image.new("RGBA", sh.size, P["grass_shade"])
    flat.putalpha(sh.getchannel("A").point(lambda v: 255 if v else 0))
    bg.alpha_composite(flat, (8, 8))
    bg.alpha_composite(spr, (8, 8))
    return bg.resize((bg.width * SCALE, bg.height * SCALE), Image.NEAREST)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    tier = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    spr = draw_assembler(0.0, tier)
    sh = shadow_of(spr)
    spr.save(f"{out}/assembler.png")
    spr.resize((W * SCALE, H * SCALE), Image.NEAREST).save(f"{out}/assembler_hr.png")
    sh.save(f"{out}/assembler_shadow.png")
    preview(spr, sh).save(f"{out}/preview.png")
    frames = [draw_assembler(i / N_FRAMES, tier) for i in range(N_FRAMES)]
    sheet = Image.new("RGBA", (W * 8, H * 4), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.alpha_composite(fr, (W * (i % 8), H * (i // 8)))
    sheet.save(f"{out}/assembler_sheet.png")
    sheet.resize((sheet.width * SCALE, sheet.height * SCALE), Image.NEAREST).save(f"{out}/assembler_sheet_hr.png")
    gif = []
    for fr in frames:
        bg = Image.new("RGBA", (W + 16, H + 16), P["grass_light"])
        flat = Image.new("RGBA", fr.size, P["grass_shade"])
        flat.putalpha(shadow_of(fr).getchannel("A").point(lambda v: 255 if v else 0))
        bg.alpha_composite(flat, (8, 8)); bg.alpha_composite(fr, (8, 8))
        gif.append(bg.resize((bg.width * 3, bg.height * 3), Image.NEAREST).convert("RGB"))
    gif[0].save(f"{out}/anim.gif", save_all=True, append_images=gif[1:], duration=60, loop=0)
