"""Palette partagée du style pixel art (relevée à l'œil sur l'image de référence krank.love).

Règle : jamais de noir pur ; les ombres glissent vers le bleu/violet, les lumières vers le jaune/cyan.
"""


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


P = {
    # herbe et sol
    "grass_light": hx("a5ef6b"), "grass": hx("7fdc60"), "grass_shade": hx("3dbb5e"), "grass_dark": hx("2a9a55"),
    "sand": hx("ffc873"),
    # acier
    "steel_dark": hx("3f4d66"), "steel": hx("5e7088"), "steel_mid": hx("8aa0b4"), "steel_light": hx("b3c4d2"),
    "white": hx("eef3f6"),
    # bleu (machine niveau 2)
    "blue_out": hx("24407f"), "blue_dark": hx("2f6bc4"), "blue": hx("3c9be8"), "blue_light": hx("78c6f7"),
    "cyan": hx("6fe8f7"), "cyan_light": hx("c4f8fb"),
    # orange / rouge
    "tan": hx("f7c06a"), "orange": hx("f0944f"), "orange_dark": hx("d8643f"), "red": hx("b03a48"), "maroon": hx("6e2540"),
}

# Rampes par niveau d'assembleur, reprenant les couleurs de Factorio / du mod cartoon
# (1 = tôle gris-vert, 2 = acier bleu, 3 = olive). Chaque rampe : contour, ombre, ton moyen, lumière.
TIERS = {
    1: dict(wall=("3f4a45", "62705f", "8d9a82", "bccaa8"), panel=("2d4a66", "3f77a8", "5aa0d4")),
    2: dict(wall=("26405c", "3d6490", "5b8cbb", "93bde0"), panel=("1b2f50", "2f4b78", "4a6fa3")),
    3: dict(wall=("4d531f", "727b2f", "9aa543", "c9d472"), panel=("3a4017", "5a6226", "7c872f")),
}
for _t, _d in TIERS.items():
    for _i, _n in enumerate(("out", "dark", "mid", "light")):
        P[f"w{_t}_{_n}"] = hx(_d["wall"][_i])
    for _i, _n in enumerate(("out", "dark", "mid")):
        P[f"p{_t}_{_n}"] = hx(_d["panel"][_i])
