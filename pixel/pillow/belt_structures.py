"""Souterrains et répartiteurs en pixel art (16 px par case, x4 à l'export), aux couleurs des convoyeurs.

Souterrain : planche 4 x 4 de cellules de 48 px d'art (le jeu y lit 192 px) ; colonnes = nord, est, sud, ouest ;
rangées = sortie, entrée, sortie en insertion latérale, entrée en insertion latérale. Le tapis (animé, dessiné par le
jeu en dessous) s'enfonce dans une rampe tramée de plus en plus sombre, puis passe sous un linteau en acier.
Répartiteur : 4 orientations, 32 images chacune (planche 8 x 4). Poteaux d'extrémité, cloison centrale avec son nez
diviseur, rail à trois engrenages qui tournent, capots à chevrons et voyants qui clignotent.

Usage : python pixel/pillow/belt_structures.py <dossier_sortie>   (aperçu)
"""
import math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, BELT, hx
from pixutil import autoshade
import belt

STEEL = (P["steel_dark"], P["steel"], P["steel_mid"], P["steel_light"])
FLOW = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


def plate_color(a, b, tier, bright=False):
    """Plaque à chevrons : `a` avance dans le sens du flux, `b` va en travers (période 4).
    `bright` : fond aux couleurs du niveau et chevrons sombres (capots) ; sinon fond sombre et chevrons clairs."""
    light, dark = BELT[tier]
    c = abs((b % 4) - 1.5)
    ph = (a + (1 if c > 1 else 0)) % 4
    if bright:
        return dark if ph == 1 else light
    return light if ph == 1 else dark if ph == 0 else belt.BASE[tier]


def rect_mask(size, rects):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for x0, y0, x1, y1 in rects:
        d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    return m


def paint_plate(img, rect, flow, tier, inset=1, bright=False):
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
            img.putpixel((x, y), plate_color(a, b, tier, bright))


def with_shadow(img, mask, offset=(3, 2)):
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste((20, 15, 30, 85), offset, mask)
    out.alpha_composite(img)
    return out


def add_face(img, mask):
    """Hauteur : face avant sur les 2 px sous le bord sud d'une forme (modifie `img` et `mask`)."""
    w, h = mask.size
    src = mask.copy()
    for y in range(h - 1):
        for x in range(w):
            if src.getpixel((x, y)) and not src.getpixel((x, y + 1)):
                for k, c in ((1, P["steel"]), (2, P["steel_dark"])):
                    if y + k < h and not src.getpixel((x, y + k)):
                        img.putpixel((x, y + k), c)
                        mask.putpixel((x, y + k), 255)


# ---------------------------------------------------------------- souterrain
# Capot en voûte (demi-cylindre couché dans le sens du flux) : plaque bombée de la teinte vive du convoyeur du même niveau (chevrons de sa teinte foncée),
# chevrons qui suivent le flux, anneau d'acier à rivets à chaque bout, face avant sombre (hauteur) et ombre portée.
UG_LEN = 13        # longueur du capot dans le sens du flux : bout fermé 3, voûte 5, bouche 5 (px)
UG_WIDTH = 14      # largeur en travers (px)
FACE = 3           # hauteur de la face avant (px)


def tile_coords(direction, x, y):
    """(s, lat) d'un pixel (x, y) de la case : s avance dans le sens du flux (0 à 16), lat va en travers (-8 à 8)."""
    px, py = x + 0.5, y + 0.5
    return {"E": (px, py - 8), "W": (belt.T - px, py - 8), "N": (belt.T - py, px - 8), "S": (py, px - 8)}[direction]


def darken(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f), c[3])


def underground_cell(direction, entering, tier):
    """Cellule de 48 x 48 px d'art ; la case occupe [16, 32[. Le capot est collé du côté enterré."""
    light, dark = BELT[tier]
    base = belt.BASE[tier]
    horiz = direction in "EW"
    img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    hood = Image.new("L", (48, 48), 0)
    s0 = (belt.T - UG_LEN) if entering else 0
    out_n = FLOW[direction] if entering else (-FLOW[direction][0], -FLOW[direction][1])   # normale du bout enterré
    in_n = (-out_n[0], -out_n[1])                                                          # normale du bout côté tapis
    for ty in range(belt.T):
        for tx in range(belt.T):
            s, lat = tile_coords(direction, tx, ty)
            if not (s0 <= s < s0 + UG_LEN and abs(lat) < UG_WIDTH / 2):
                continue
            u = s - s0                                   # 0 à UG_LEN, dans le sens du flux
            d_ug = (UG_LEN - u) if entering else u       # distance au bout enterré
            d_belt = UG_LEN - d_ug
            lat_abs = (ty + 0.5 - 8) if horiz else (tx + 0.5 - 8)    # axe transversal absolu : la lumière vient du haut gauche
            x, y = tx + 16, ty + 16
            hood.putpixel((x, y), 255)
            if abs(lat) > UG_WIDTH / 2 - 1:
                c = P["steel_dark"]                                    # flancs : contour
            elif d_ug < 3:                                             # bout fermé (côté enterré) : mur plein à rivets
                c = belt.shade(d_ug, out_n)
                if d_ug >= 2 and abs(lat) in (1.5, 4.5):
                    c = P["steel_light"]
            elif d_belt < 5:                                           # bouche ouverte côté tapis
                if d_belt < 1:
                    c = belt.shade(d_belt, in_n)                       # lèvre de l'ouverture
                elif abs(lat) >= 4.5:
                    c = belt.shade(1 + (abs(lat) - 4.5), (0, 0)) if abs(lat) < 5.5 else P["steel"]   # piédroits
                else:
                    # intérieur du tunnel : de plus en plus sombre vers le bout fermé, avec le chevron du tapis
                    k = d_belt - 1                                     # 0 (près de la lèvre) à 3 (au fond)
                    f_ = (0.85, 0.6, 0.38, 0.22)[min(3, int(k))]
                    u_tip = (3 if entering else UG_LEN - 2) + 1.5      # pointe du chevron, dans le sens du flux
                    chev = abs(lat) < 2.6 and int(u) == int(u_tip - abs(lat) + 0.5)
                    c = darken(light if chev else belt.BASE[tier], f_ if not chev else max(f_, 0.55))
            else:
                # voûte : plaque de la teinte vive du niveau, chevrons de la teinte foncée ; plus sombre sur le flanc
                # opposé à la lumière
                shade = 1.0 if lat_abs < -3 else 0.88 if lat_abs < 3 else 0.7
                ph = (u + abs(lat) * 0.55) % 6
                c = darken(dark, shade) if ph < 2 else darken(light, shade)
            img.putpixel((x, y), c)
    # hauteur : face avant sur FACE px sous le bord sud du capot
    src = hood.copy()
    for y in range(47):
        for x in range(48):
            if src.getpixel((x, y)) and not src.getpixel((x, y + 1)):
                for k in range(1, FACE + 1):
                    if y + k < 48 and not src.getpixel((x, y + k)):
                        img.putpixel((x, y + k), P["steel"] if k == 1 else P["steel_dark"])
                        hood.putpixel((x, y + k), 255)
    return with_shadow(img, hood)


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
        x, y = round(cx + (r + 0.7) * math.cos(a)), round(cy + (r + 0.7) * math.sin(a))
        d.rectangle((x - 1, y - 1, x, y), fill=255)
    return m


FRAME = {"N": (40, 26), "S": (40, 26), "E": (26, 40), "W": (26, 40)}


def splitter_frame(direction, phase, tier):
    """Une image du répartiteur. Les pièces sont définies pour le nord (32 x 16, le flux monte) puis tournées."""
    k = "NESW".index(direction)
    fw, fh = FRAME[direction]
    ox, oy = (4, 5) if direction in "NS" else (5, 4)
    size = (fw, fh)

    def tr(x, y):                       # point local -> point de l'image
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

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    tall = Image.new("L", size, 0)          # pièces hautes (reçoivent une face avant)
    flat = Image.new("L", size, 0)          # pièces basses (rail, engrenages)
    flow = FLOW[direction]

    def put(mask, high=True, ramp=STEEL):
        img.alpha_composite(autoshade(mask, ramp))
        (tall if high else flat).paste(255, (0, 0), mask)

    # rail transversal, sous tout le reste
    put(rect_mask(size, [tr_rect(4, 7, 28, 11)]), high=False, ramp=(P["steel_dark"], P["steel"], P["steel_mid"], P["steel_light"]))
    # poteaux d'extrémité, cloison centrale et nez diviseur côté entrée
    put(rect_mask(size, [tr_rect(0, 0, 4, 16), tr_rect(28, 0, 32, 16)]))
    nose = Image.new("L", size, 0)
    ImageDraw.Draw(nose).polygon([tr(14, 16), tr(18, 16), tr(16, 20.5)], fill=255)
    wall = rect_mask(size, [tr_rect(14, 3, 18, 16)])
    wall.paste(255, (0, 0), nose)
    put(wall)
    for lx, ly in ((1.5, 1.5), (1.5, 14), (29.5, 1.5), (29.5, 14)):   # rivets des poteaux
        x, y = tr(lx, ly)
        img.putpixel((int(x), int(y)), P["steel_light"])
    # engrenages : un grand au centre, un de chaque côté, sens alternés, 2 dents par boucle (6 ou 8 dents)
    for n, (gx, gy, r, teeth) in enumerate(((9.5, 9, 3.0, 6), (16, 9, 3.6, 8), (22.5, 9, 3.0, 6))):
        cx, cy = tr(gx, gy)
        gm = gear_mask(size, cx, cy, r, teeth, 2 * phase * (-1 if n == 1 else 1) * 6 / teeth)
        put(gm, high=False, ramp=(P["steel_dark"], P["steel_mid"], P["steel_light"], P["white"]))
        hx_, hy_ = round(cx), round(cy)
        for dx in (0, -1):
            for dy in (0, -1):
                img.putpixel((hx_ + dx, hy_ + dy), P["orange"])
        img.putpixel((hx_ - 1, hy_ - 1), P["tan"])
    # capots aux couleurs du niveau côté sortie
    caps = [tr_rect(4, 0, 14, 5), tr_rect(18, 0, 28, 5)]
    put(rect_mask(size, caps))
    for cap in caps:
        paint_plate(img, cap, flow, tier, inset=1, bright=True)
    # voyants sur la cloison : s'allument en alternance
    on = phase < 0.5
    for n, (lx, ly) in enumerate(((15, 4.5), (16, 4.5))):
        x, y = tr(lx, ly)
        img.putpixel((int(x), int(y)), P["cyan_light"] if (n == 0) == on else P["blue_out"])
    add_face(img, tall)
    allmask = Image.new("L", size, 0)
    allmask.paste(255, (0, 0), tall)
    allmask.paste(255, (0, 0), flat)
    return with_shadow(img, allmask)


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
    # souterrains posés sur des convoyeurs animés : lignes vers l'est, le nord, l'ouest et le sud (entrée puis sortie)
    rows = []
    for tier in ("yellow", "red", "blue"):
        parts = []
        for direction, brow in (("E", 0), ("N", 2), ("W", 1), ("S", 3)):
            n = 7
            horiz = direction in "EW"
            line = Image.new("RGBA", (16 * n, 16 * 3) if horiz else (16 * 3, 16 * n), P["grass"])
            for i in range(n):
                line.alpha_composite(belt.piece(brow, 5, tier), (i * 16, 16) if horiz else (16, i * 16))
            fx, fy = FLOW[direction]
            ent, ext = (2, 4) if (fx > 0 or fy > 0) else (4, 2)          # case d'entrée / de sortie sur la ligne
            for idx, entering in ((ent, True), (ext, False)):
                cell = underground_cell(direction, entering, tier)
                line.alpha_composite(cell, (idx * 16 - 16, 0) if horiz else (0, idx * 16 - 16))
            parts.append(line.resize((line.width * 4, line.height * 4), Image.NEAREST))
        wtot = sum(p.width for p in parts) + 20 * len(parts)
        row = Image.new("RGBA", (wtot, max(p.height for p in parts)), P["grass"])
        x = 0
        for p in parts:
            row.paste(p, (x, 0)); x += p.width + 20
        rows.append(row)
    c = Image.new("RGBA", (max(r.width for r in rows), sum(r.height for r in rows)), P["grass"])
    y = 0
    for r in rows:
        c.paste(r, (0, y)); y += r.height
    c.save(f"{o}/ug_all.png")
    # répartiteurs : 4 orientations, 3 niveaux
    prev = Image.new("RGBA", (4 * 150, 3 * 125), P["grass"])
    for i, tier in enumerate(("yellow", "red", "blue")):
        for j, d in enumerate("NESW"):
            f = splitter_frame(d, 0.0, tier)
            prev.alpha_composite(f.resize((f.width * 3, f.height * 3), Image.NEAREST), (j * 150 + 5, i * 125 + 5))
    prev.save(f"{o}/split_preview.png")
