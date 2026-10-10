"""Poteaux électriques en pixel art : poteau en bois (petit), pylône rouillé (moyen), grand pylône en acier, sous-station.

Chaque poteau est décrit en 3D (pieds, croisillons, bras, isolateurs) puis projeté pour 4 rotations (0, 45, 90, 135 degrés,
comme les 4 variantes du jeu). Projection : x' = X cos t - Y sin t ; y' = X sin t + Y cos t ; écran = (x', y' / 2 - Z).
Les ombres sont la même géométrie projetée au sol, étirée vers la droite (soleil en haut à gauche).
Les points d'attache des câbles (3 isolateurs : cuivre, rouge, vert) sont calculés pour chaque variante : ils servent à
régénérer les `connection_points` du prototype (voir export_mod.py).

1 px d'art = 2 px de jeu : les images sont exportées x4 et affichées à l'échelle 0,5.
Usage : python pixel/pillow/poles.py <dossier_sortie>   (aperçu)
"""
import math, os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, hx

ANGLES = [0, 45, 90, 135]

WOOD = (hx("4a2f26"), hx("7a4a30"), hx("b07a42"), hx("dca565"))        # contour, ombre, moyen, lumière
RUST = (P["maroon"], hx("a8503a"), P["orange_dark"], P["tan"])
STEEL = (hx("2b3a54"), P["steel"], P["steel_mid"], P["steel_light"])
BLUE = (P["blue_out"], P["blue_dark"], P["blue"], P["blue_light"])

SPECS = {
    "small-electric-pole": dict(size=(24, 52), tile=1, kind="wood", H=42, base=1.4, top=1.4, trunk=1.6,
                                arms=[(40, 6.5)], tip=(0, 43), ramp=WOOD, braces=0, canvas_pad=6),
    "medium-electric-pole": dict(size=(30, 64), tile=1, kind="lattice", H=52, base=6.0, top=1.6,
                                 arms=[(46, 7.0)], tip=(0, 53), ramp=RUST, braces=3),
    "big-electric-pole": dict(size=(52, 80), tile=2, kind="lattice", H=66, base=12.0, top=2.6,
                              arms=[(58, 16.0), (40, 16.0)], tip=(0, 67), ramp=STEEL, braces=4),
    "substation": dict(size=(46, 76), tile=2, kind="substation", H=60, base=10.0, top=2.2,
                       arms=[(54, 12.0)], tip=(0, 61), ramp=STEEL, braces=5, box=(12, 22)),
}


def proj(spec, theta, X, Y, Z):
    t = math.radians(theta)
    xp = X * math.cos(t) - Y * math.sin(t)
    yp = X * math.sin(t) + Y * math.cos(t)
    return xp, yp * 0.5 - Z, yp


def line(d, a, b, c):
    d.line([(round(a[0]), round(a[1])), (round(b[0]), round(b[1]))], fill=c, width=1)


def thick(d, a, b, c, w=2):
    for k in range(w):
        d.line([(round(a[0]), round(a[1]) + k), (round(b[0]), round(b[1]) + k)], fill=c)


def insulator(d, x, y):
    """Isolateur : pastille de 2 x 3 px, blanc dessus."""
    x, y = int(round(x)), int(round(y))
    d.rectangle((x, y - 3, x + 1, y - 1), fill=P["cyan_light"])
    d.point((x, y - 3), P["white"])
    d.rectangle((x, y, x + 1, y), fill=P["steel_dark"])


def render(name, k):
    """Image (art) du poteau pour la variante k, son ombre, et les points d'attache (relatifs au pied, en px d'art)."""
    spec = SPECS[name]
    W, H = spec["size"]
    cx, gy = W // 2, H - 6                                  # pied du poteau dans l'image
    th = ANGLES[k]
    out_c, dark, mid, light = spec["ramp"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def P3(X, Y, Z):
        sx, sy, depth = proj(spec, th, X, Y, Z)
        return (cx + sx, gy + sy), depth

    b, t, h = spec["base"], spec["top"], spec["H"]
    pts_ins = []
    if spec["kind"] == "wood":
        # fût : deux tons, pied en acier
        trunk = spec["trunk"]
        for dx, c in ((-1, light), (0, mid), (1, dark)):
            line(d, (cx + dx, gy - 2), (cx + dx, gy - h + 2), c)
        line(d, (cx - 2, gy - 2), (cx - 2, gy - h + 2), out_c)
        line(d, (cx + 2, gy - 2), (cx + 2, gy - h + 2), out_c)
        d.rectangle((cx - 3, gy - 3, cx + 3, gy), fill=P["steel"])
        d.rectangle((cx - 3, gy - 3, cx + 3, gy - 3), fill=P["steel_light"])
        d.rectangle((cx - 3, gy, cx + 3, gy), fill=P["steel_dark"])
    else:
        legs_b = [(sx_ * b, sy_ * b) for sx_ in (-1, 1) for sy_ in (-1, 1)]
        legs_t = [(sx_ * t, sy_ * t) for sx_ in (-1, 1) for sy_ in (-1, 1)]
        n = spec["braces"]
        zs = [i * h / max(1, n) for i in range(n + 1)]
        def width_at(z):
            f = z / h
            return b + (t - b) * f
        # arrière d'abord (plus sombre), puis l'avant
        faces = [((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))]
        def face_depth(f):
            (a1, a2), (b1, b2) = f
            return sum(P3(sx_ * b, sy_ * b, 0)[1] for sx_, sy_ in f) / 2
        faces.sort(key=face_depth)
        for fi, f in enumerate(faces):
            col = dark if fi < 2 else mid
            for i in range(n):
                z0, z1 = zs[i], zs[i + 1]
                w0, w1 = width_at(z0), width_at(z1)
                a0 = P3(f[0][0] * w0, f[0][1] * w0, z0)[0]; a1 = P3(f[0][0] * w1, f[0][1] * w1, z1)[0]
                c0 = P3(f[1][0] * w0, f[1][1] * w0, z0)[0]; c1 = P3(f[1][0] * w1, f[1][1] * w1, z1)[0]
                line(d, a0, c1, col); line(d, c0, a1, col)          # croisillons en X
                if i % 2 == 1:
                    line(d, a1, c1, col)                              # traverse, un niveau sur deux
            # montants de la face
            for (sx_, sy_) in f:
                line(d, P3(sx_ * b, sy_ * b, 0)[0], P3(sx_ * t, sy_ * t, h)[0], light if fi >= 2 else mid)
        if spec["kind"] == "substation":
            bw, bh = spec["box"]
            # boîtier en bas : face avant, dessus et flanc éclairé
            d.rectangle((cx - bw, gy - bh, cx + bw - 1, gy), fill=BLUE[0])
            d.rectangle((cx - bw + 1, gy - bh + 1, cx + bw - 2, gy - 1), fill=BLUE[2])
            d.rectangle((cx - bw + 1, gy - bh + 1, cx + bw - 2, gy - bh + 3), fill=BLUE[3])
            d.rectangle((cx - bw + 1, gy - 4, cx + bw - 2, gy - 1), fill=BLUE[1])
            for gx in range(cx - bw + 4, cx + bw - 3, 4):
                d.rectangle((gx, gy - bh + 7, gx + 1, gy - 6), fill=BLUE[1])           # ailettes
            d.rectangle((cx - bw - 2, gy - bh + 5, cx - bw, gy - 5), fill=STEEL[2])    # cylindres latéraux
            d.rectangle((cx + bw - 1, gy - bh + 5, cx + bw + 1, gy - 5), fill=STEEL[2])
    # bras et isolateurs
    arms = spec["arms"]
    for (z, L) in arms:
        a, _ = P3(-L, 0, z); c, _ = P3(L, 0, z)
        thick(d, a, c, mid, 2 if spec["kind"] != "wood" else 2)
        d.line([(round(a[0]), round(a[1])), (round(c[0]), round(c[1]))], fill=light)
        # extrémités des bras : isolateurs
        for (X, tag) in ((-L, "L"), (L, "R")):
            p, _ = P3(X, 0, z)
            pts_ins.append((tag, z, p))
    tip, _ = P3(0, 0, spec["tip"][1])
    pts_ins.append(("T", spec["tip"][1], tip))
    # le fût porte un isolateur central en haut
    # tri des points d'attache : cuivre = pointe, rouge = gauche du bras haut, vert = droite du bras haut
    top_arm = max(a[0] for a in arms)
    left = [p for tg, z, p in pts_ins if tg == "L" and z == top_arm][0]
    right = [p for tg, z, p in pts_ins if tg == "R" and z == top_arm][0]
    attach = {"copper": tip, "red": left, "green": right}
    for key in ("red", "green", "copper"):
        x, y = attach[key]
        insulator(d, x - 0.5, y)
    # ombre : géométrie projetée au sol, étirée vers la droite
    sw, sh = W + int(0.6 * H), 22
    sgx, sgy = cx, sh // 2 + 3
    shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    def S3(X, Y, Z):
        sx, sy, depth = proj(spec, th, X, Y, Z)
        return (sgx + sx + 0.6 * Z, sgy + (sy + Z) * 0.9 + 0.12 * Z)       # y' seul (sans la hauteur) + léger décalage
    if spec["kind"] == "wood":
        thick(sd, S3(0, 0, 0), S3(0, 0, h), (0, 0, 0, 255), 2)
    else:
        for sx_ in (-1, 1):
            for sy_ in (-1, 1):
                line(sd, S3(sx_ * b, sy_ * b, 0), S3(sx_ * t, sy_ * t, h), (0, 0, 0, 255))
        n = spec["braces"]
        for i in (0, n // 2, n):
            z = i * h / n
            w = b + (t - b) * z / h
            pts = [S3(sx_ * w, sy_ * w, z) for sx_, sy_ in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1))]
            for a_, c_ in zip(pts, pts[1:]):
                line(sd, a_, c_, (0, 0, 0, 255))
    for (z, L) in arms:
        thick(sd, S3(-L, 0, z), S3(L, 0, z), (0, 0, 0, 255), 2)
    shadow_attach = {key: S3(*{"copper": (0, 0, spec["tip"][1]),
                                "red": (-arms[0][1], 0, arms[0][0]),
                                "green": (arms[0][1], 0, arms[0][0])}[key]) for key in attach}
    rel = {key: (p[0] - cx, p[1] - gy - 3.0) for key, p in attach.items()}    # isolateur : sommet, 3 px au-dessus du point
    rel_sh = {key: (p[0] - sgx, p[1] - sgy) for key, p in shadow_attach.items()}
    return img, shadow, rel, rel_sh, (cx, gy), (sgx, sgy)


def sheets(name):
    """Planche des 4 variantes + ombres + données de cadrage pour le Lua."""
    W, H = SPECS[name]["size"]
    frames, shadows, rels, rel_shs, anchor, sanchor = [], [], [], [], None, None
    for k in range(4):
        img, sh, rel, rel_sh, anchor, sanchor = render(name, k)
        frames.append(img); shadows.append(sh); rels.append(rel); rel_shs.append(rel_sh)
    sheet = Image.new("RGBA", (W * 4, H), (0, 0, 0, 0))
    for k, f in enumerate(frames):
        sheet.alpha_composite(f, (W * k, 0))
    sw, sh_ = shadows[0].size
    ssheet = Image.new("RGBA", (sw * 4, sh_), (0, 0, 0, 0))
    for k, f in enumerate(shadows):
        ssheet.alpha_composite(f, (sw * k, 0))
    # décalage du sprite : le pied doit tomber sur le centre de l'entité (1 px d'art = 2 px de jeu)
    info = dict(
        picture=dict(width=W * 4 // 4 * 4, height=H * 4, shift=((W / 2 - anchor[0]) * 2, (H / 2 - anchor[1]) * 2)),
        shadow=dict(width=sw * 4, height=sh_ * 4, shift=((sw / 2 - sanchor[0]) * 2, (sh_ / 2 - sanchor[1]) * 2)),
        rel=[{k_: (v[0] * 2, v[1] * 2) for k_, v in r.items()} for r in rels],
        rel_shadow=[{k_: (v[0] * 2, v[1] * 2) for k_, v in r.items()} for r in rel_shs],
    )
    return sheet, ssheet, info


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    canvas = Image.new("RGBA", (1500, 1000), hx("7fb65a"))
    y = 5
    for name in SPECS:
        sheet, ssheet, info = sheets(name)
        sc = 5
        big = sheet.resize((sheet.width * sc, sheet.height * sc), Image.NEAREST)
        canvas.alpha_composite(big.resize((min(big.width, 1400), big.height * min(big.width, 1400) // big.width), Image.NEAREST), (5, y))
        y += min(big.height, 300) + 10
    canvas.save(f"{o}/poles_preview.png")
