"""Palette fermée du mod pixel : une rampe par matière, du plus sombre au plus clair.

[PROVISOIRE] Les teintes de base sont un point de départ ; la palette se fixe sur les images cibles retenues par
Bastien (étape 1 de docs/pixel/plan.md). Pour les régler, changer BASES ou fixer une rampe à la main dans FIXED.

Rampe calculée depuis une couleur de base (au milieu de la rampe) : les tons sombres glissent vers le bleu-violet,
les tons clairs vers le jaune, comme le veut le pixel art ; le plus sombre sert de contour (jamais de noir pur).
"""
import colorsys

import numpy as np

STEPS = 5                      # par rampe : contour, ombre, moyen, clair, lumière
HUE_SHIFT = 12 / 360           # décalage de teinte maximal aux extrémités de la rampe
LIGHTNESS = (0.16, 0.30, 0.0, 0.66, 0.82)    # 0.0 : la base elle-même
COOL, WARM = 250 / 360, 55 / 360             # vers où glissent les ombres et les lumières

BASES = {                      # matière -> couleur de base (ton moyen)
    "acier": "#7f8a96",
    "fer": "#8d9399",
    "cuivre": "#c7713f",
    "laiton": "#c9a23f",
    "rouille": "#8c5a3c",
    "bois": "#8a6440",
    "pierre": "#8f8576",
    "niveau-1": "#7d8c76",     # gris-vert de l'assembleur 1
    "niveau-2": "#4f7aa8",     # bleu
    "niveau-3": "#8a8a4e",     # olive
    "jaune": "#d8b23a",        # convoyeur de base
    "rouge": "#b9473f",
    "bleu": "#3f74c0",
    "vert": "#4f9a52",
    "orange": "#e0812f",       # feu, voyants
    "herbe": "#5e8f45",
    "terre": "#8a6a48",
    "sable": "#c8ae78",
    "eau": "#2f6c9e",
}
FIXED = {}                     # matière -> liste de STEPS couleurs « #rrggbb », prioritaire sur BASES


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _toward(h, target, amount):
    d = (target - h + 0.5) % 1.0 - 0.5            # plus court chemin sur le cercle des teintes
    return (h + d * amount) % 1.0


def ramp(base):
    r, g, b = (v / 255 for v in _hex(base))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    out = []
    for i, target_l in enumerate(LIGHTNESS):
        if target_l == 0.0:
            out.append(_hex(base))
            continue
        darker = target_l < l
        amount = abs(target_l - l) / max(l, 1 - l)
        hue = _toward(h, COOL if darker else WARM, min(1.0, amount) * HUE_SHIFT * 6)
        sat = min(1.0, s * (1.15 if darker else 0.9))
        out.append(tuple(round(v * 255) for v in colorsys.hls_to_rgb(hue, target_l, sat)))
    return out


def ramps():
    """{matière: [(r, g, b) * STEPS]}, du plus sombre au plus clair."""
    out = {name: ramp(base) for name, base in BASES.items()}
    out.update({name: [_hex(c) for c in colors] for name, colors in FIXED.items()})
    return out


RAMPS = ramps()
COLORS = np.array([c for r in RAMPS.values() for c in r], dtype=np.int32)          # (N, 3)
OWNER = [(name, i) for name, r in RAMPS.items() for i in range(len(r))]              # couleur -> (matière, rang)


def index_of(rgb):
    """Rang dans COLORS de la couleur de palette la plus proche (distance « redmean », proche de l'œil)."""
    rgb = np.asarray(rgb, dtype=np.int32)
    d = rgb[..., None, :] - COLORS
    rmean = (rgb[..., None, 0] + COLORS[:, 0]) / 2
    dist = (2 + rmean / 256) * d[..., 0] ** 2 + 4 * d[..., 1] ** 2 + (2 + (255 - rmean) / 256) * d[..., 2] ** 2
    return dist.argmin(-1)


def contains(rgb_array):
    """Masque des pixels dont la couleur est exactement dans la palette."""
    flat = rgb_array.reshape(-1, 3).astype(np.int32)
    keys = (COLORS[:, 0] << 16) | (COLORS[:, 1] << 8) | COLORS[:, 2]
    return np.isin((flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2], keys).reshape(rgb_array.shape[:-1])


def swatch(path, cell=16):
    """Planche de la palette (une rampe par ligne) pour la montrer à Bastien."""
    from PIL import Image, ImageDraw
    names = list(RAMPS)
    im = Image.new("RGB", (cell * STEPS + 90, cell * len(names)), (40, 40, 48))
    draw = ImageDraw.Draw(im)
    for y, name in enumerate(names):
        for x, c in enumerate(RAMPS[name]):
            draw.rectangle([x * cell, y * cell, (x + 1) * cell - 1, (y + 1) * cell - 1], fill=c)
        draw.text((cell * STEPS + 6, y * cell + 2), name, fill=(230, 230, 230))
    im.save(path)


if __name__ == "__main__":
    import sys
    swatch(sys.argv[1] if len(sys.argv) > 1 else "palette.png")
