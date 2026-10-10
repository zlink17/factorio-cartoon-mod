"""Convoyeurs en pixel art, vus directement du dessus (16 px par case, x4 à l'export).

Planche de Factorio : une cellule de 128 px (32 px d'art) par image, la case au centre ; une rangée par pièce,
une colonne par image d'animation. Rangées : 0-3 droites (E, O, N, S), 4-11 virages, 12-19 capuchons de début/fin.
Une image avance d'un demi-pixel d'art, donc le décalage est (image // 2) : la boucle se referme sur un nombre
entier de motifs (pas de 8 px).

Usage : python pixel/pillow/belt.py <dossier_sortie>      (aperçu de la planche basique)
"""
import math, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from palette import P, BELT, hx

CELL = 32           # px d'art par cellule ; la case occupe [8, 24[
T = 16              # px d'art par case
PITCH = 8           # pas des chevrons
# Couleur du fond du tapis, par niveau : brun (basique), bordeaux (rapide), marine (express)
BASE = {"yellow": hx("6b5638"), "red": hx("6e3446"), "blue": hx("33507a")}
LIGHT = (-1 / math.sqrt(2), -1 / math.sqrt(2))   # direction vers la lumière (haut gauche)

# (coin, vecteur coin -> milieu du bord d'entrée, vecteur coin -> milieu du bord de sortie)
CURVES = [
    ((16, 0), (0, 1), (-1, 0)),     # est -> nord
    ((16, 0), (-1, 0), (0, 1)),     # nord -> est
    ((0, 0), (0, 1), (1, 0)),       # ouest -> nord
    ((0, 0), (1, 0), (0, 1)),       # nord -> ouest
    ((16, 16), (-1, 0), (0, -1)),   # sud -> est
    ((16, 16), (0, -1), (-1, 0)),   # est -> sud
    ((0, 16), (1, 0), (0, -1)),     # sud -> ouest
    ((0, 16), (0, -1), (1, 0)),     # ouest -> sud
]
STRAIGHT = [(1, 0), (-1, 0), (0, -1), (0, 1)]   # est, ouest, nord, sud


def shade(depth, normal):
    """Couleur d'un pixel de rail selon sa profondeur depuis le bord extérieur et son orientation."""
    lit = normal[0] * LIGHT[0] + normal[1] * LIGHT[1] > 0.2
    if depth < 1:
        return P["steel_dark"]
    if depth < 2:
        return P["steel_light"] if lit else P["steel"]
    return P["steel_mid"] if lit else P["steel"]


def surface(s, lat, off, tier):
    """Petits chevrons (7 px de haut, 2 px d'épaisseur) centrés sur l'axe du convoyeur, avec une ombre derrière."""
    light, dark = BELT[tier]
    if abs(lat) <= 3.2:
        ph = (s + abs(lat) - off) % PITCH
        if ph < 2:
            return light
        if ph >= 7:
            return dark
    return BASE[tier]


def straight_pixel(x, y, flow, off, tier):
    px, py = x + 0.5, y + 0.5
    if flow[0]:
        s = px if flow[0] > 0 else T - px
        lat, normal = py - 8, (0, 1 if py > 8 else -1)
    else:
        s = py if flow[1] > 0 else T - py
        lat, normal = px - 8, (1 if px > 8 else -1, 0)
    if abs(lat) >= 5:
        return shade(8 - abs(lat), normal)
    return surface(s, lat, off, tier)


def curve_pixel(x, y, curve, off, tier):
    (cx, cy), a, b = curve
    px, py = x + 0.5 - cx, y + 0.5 - cy
    r = math.hypot(px, py)
    if r > T:
        return None
    ang = math.acos(max(-1.0, min(1.0, (px * a[0] + py * a[1]) / r)))
    s = ang / (math.pi / 2) * T            # 16 px de bout en bout : le motif se raccorde aux cases voisines
    if r >= 13:
        return shade(T - r, (px / r, py / r))
    if r < 3:
        return shade(r, (-px / r, -py / r))
    return surface(s, r - 8, off, tier)


def piece(row, frame, tier):
    off = frame // 2
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    for y in range(T):
        for x in range(T):
            if row < 4:
                c = straight_pixel(x, y, STRAIGHT[row], off, tier)
            elif row < 12:
                c = curve_pixel(x, y, CURVES[row - 4], off, tier)
            else:
                c = None
            if c:
                img.putpixel((x, y), c)
    if row >= 12:
        return cap_piece(row, frame, tier)
    return img


# Bouts de ligne (rangées 12 à 19), comme dans le mod cartoon : une bande de tapis au bord aval de la case, prolongée
# d'un rouleau en acier qui dépasse de 2 px. Les chevrons avancent vers l'extérieur (sens du flux) ; les rangées paires
# (12, 14, 16, 18) sont animées, les impaires fixes. Rangées : haut (nord), droite (est), bas (sud), gauche (ouest).
CAP_FLOW = [(0, -1), (0, -1), (1, 0), (1, 0), (0, 1), (0, 1), (-1, 0), (-1, 0)]
CAP_PAD = 2
CAP_BAND = 3          # largeur de la bande de tapis, dans la case
CAP_ROLLER = 2        # largeur du rouleau, hors de la case


END_CAPS = False      # décidé avec Bastien : pas de bout de ligne visible (les rangées 12 à 19 restent transparentes)


def cap_piece(row, frame, tier):
    """Image de 20 x 20 : la case plus 2 px de marge ; (i, j) correspond au pixel (i - 2, j - 2) de la case."""
    if not END_CAPS:
        return Image.new("RGBA", (T + 2 * CAP_PAD, T + 2 * CAP_PAD), (0, 0, 0, 0))
    flow = CAP_FLOW[row - 12]
    off = (frame // 2) if row % 2 == 0 else 0
    img = Image.new("RGBA", (T + 2 * CAP_PAD, T + 2 * CAP_PAD), (0, 0, 0, 0))
    for y in range(-CAP_PAD, T + CAP_PAD):
        for x in range(-CAP_PAD, T + CAP_PAD):
            px, py = x + 0.5, y + 0.5
            s = {(1, 0): px, (-1, 0): T - px, (0, -1): T - py, (0, 1): py}[flow]
            across = py if flow[0] else px
            if not 0 <= across < T:
                continue
            if T - CAP_BAND <= s < T:
                img.putpixel((x + CAP_PAD, y + CAP_PAD), straight_pixel(x, y, flow, off, tier))
            elif T <= s < T + CAP_ROLLER:
                c = shade(s - T, flow)
                if s - T >= 1 and int(across) % 4 == 1:
                    c = P["steel_light"]                       # rivets du rouleau
                img.putpixel((x + CAP_PAD, y + CAP_PAD), c)
    return img


def sheet(tier, frames):
    out = Image.new("RGBA", (CELL * frames, CELL * 20), (0, 0, 0, 0))
    for row in range(20):
        for f in range(frames):
            pad = CAP_PAD if row >= 12 else 0
            out.alpha_composite(piece(row, f, tier), (CELL * f + 8 - pad, CELL * row + 8 - pad))
    return out


if __name__ == "__main__":
    o = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(o, exist_ok=True)
    s = sheet("yellow", 16)
    s.save(f"{o}/belt_sheet.png")
    # aperçu : image 0 de chaque rangée, x6, sur fond de sol
    prev = Image.new("RGBA", (5 * 20 * 6, 4 * 20 * 6), P["sand"])
    for r in range(20):
        cell = s.crop((0, CELL * r + 4, CELL, CELL * r + 28)).crop((4, 0, 28, 24))
        prev.alpha_composite(cell.resize((24 * 6, 24 * 6), Image.NEAREST), ((r % 5) * 144 - 0, (r // 5) * 144))
    prev.save(f"{o}/belt_preview.png")
