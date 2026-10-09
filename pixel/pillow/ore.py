"""Minerais en pixel art : planche 8 x 8 (rangée = étape de richesse, colonne = variante), cellules de 32 px d'art.

Rangée 0 = le plus gros tas, rangée 7 = quelques cailloux. Les tas sont tirés au hasard avec une graine fixe
(même résultat à chaque export). Usage : python pixel/pillow/ore.py <dossier_sortie>   (aperçu de la planche)
"""
import math, os, random, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import hx
from pixutil import autoshade

CELL = 32
ROCKS = [10, 9, 8, 7, 5, 4, 3, 2]            # nombre de cailloux par étape
SIZE = [(3.2, 5.0), (3.0, 4.8), (2.8, 4.4), (2.6, 4.0), (2.5, 3.6), (2.2, 3.2), (2.0, 2.8), (1.8, 2.4)]

# contour, ombre, moyen, lumière
RAMPS = {
    "iron-ore": ("2f4466", "4f78a0", "8cc0dc", "d6f4fa"),
    "copper-ore": ("6e2540", "b0503f", "ee8c4c", "ffd08a"),
    "coal": ("1d2236", "30384f", "505a78", "8892b0"),
    "stone": ("6b4a3a", "a67c52", "d6a96c", "f4dc9e"),
    "uranium-ore": ("22563a", "3da04a", "7ee05c", "daff90"),
}


def rock(rng, cx, cy, rx):
    ry = rx * 0.8
    m = Image.new("L", (CELL, CELL), 0)
    px = m.load()
    jit = [rng.uniform(0.85, 1.15) for _ in range(8)]
    for y in range(CELL):
        for x in range(CELL):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            a = (math.atan2(dy, dx) % (2 * math.pi)) / (2 * math.pi) * 8
            k = jit[int(a) % 8]
            if (dx / (rx * k)) ** 2 + (dy / (ry * k)) ** 2 <= 1:
                px[x, y] = 255
    return m


def cell(kind, stage, variation):
    rng = random.Random(f"{kind}-{stage}-{variation}")
    ramp = [hx(c) for c in RAMPS[kind]]
    img = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    spots = []
    lo, hi = SIZE[stage]
    spread = 5 + (7 - stage) * 0.0 + (8 - ROCKS[stage]) * 0.15 + 3.5
    tries = 0
    while len(spots) < ROCKS[stage] and tries < 400:
        tries += 1
        a, r = rng.uniform(0, 2 * math.pi), spread * math.sqrt(rng.random())
        x, y = 16 + r * math.cos(a), 16 + r * math.sin(a) * 0.8
        rx = rng.uniform(lo, hi) / 2 + 0.6
        if all(math.hypot(x - sx, (y - sy) * 1.2) > (rx + sr) * 0.85 for sx, sy, sr in spots):
            spots.append((x, y, rx))
    # ombres au sol (aplat translucide en bas à droite), puis cailloux triés de haut en bas
    shadow = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for x, y, rx in spots:
        sd.ellipse((x - rx + 1.5, y - rx * 0.4 + 1.5, x + rx + 1.5, y + rx * 0.9 + 1.5), fill=(30, 20, 30, 80))
    img.alpha_composite(shadow)
    for x, y, rx in sorted(spots, key=lambda s: s[1]):
        shaded = autoshade(rock(rng, x, y, rx), ramp)
        img.alpha_composite(shaded)
        # reflet
        top = [(px_, py_) for py_ in range(CELL) for px_ in range(CELL)
               if shaded.getpixel((px_, py_)) == ramp[3]]
        if top and rx > 2.2:
            tx, ty = min(top, key=lambda p: p[0] + p[1])
            img.putpixel((tx, ty), hx("ffffff") if kind != "coal" else ramp[3])
    # poussière : quelques pixels de ton foncé autour du tas
    for _ in range(ROCKS[stage] + 3):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(5, 12)
        x, y = int(16 + r * math.cos(a)), int(16 + r * math.sin(a) * 0.8)
        if 0 <= x < CELL and 0 <= y < CELL and img.getpixel((x, y))[3] == 0:
            img.putpixel((x, y), (*ramp[1][:3], 150))
    return img


def sheet(kind):
    out = Image.new("RGBA", (CELL * 8, CELL * 8), (0, 0, 0, 0))
    for s in range(8):
        for v in range(8):
            out.alpha_composite(cell(kind, s, v), (CELL * v, CELL * s))
    return out


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    kinds = list(RAMPS)
    prev = Image.new("RGBA", (CELL * 8 * 3, CELL * 8 * 2 + 0), hx("c8a060"))
    for i, k in enumerate(kinds):
        s = sheet(k)
        prev.alpha_composite(s, ((i % 3) * CELL * 8, (i // 3) * CELL * 8))
    prev.resize((prev.width * 2, prev.height * 2), Image.NEAREST).save(f"{o}/ore_preview.png")
