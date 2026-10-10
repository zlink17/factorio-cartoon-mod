"""Démo : rend plusieurs objets en style toon (projection façon Factorio).

Projection : le sol n'est pas raccourci (une case reste carrée à l'écran), les
bâtiments sont alignés sur la grille (aucune rotation), vus de face avec le dessus
visible. La hauteur est décalée vers le haut de l'écran (tan(PITCH) par unité).
Les convoyeurs sont vus directement du dessus (PITCH = 0).

Usage : python cartoon/blender/sprites_demo.py <dossier_sortie>
"""
import math, os, sys
import bpy
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_out"
SIZE = 256
os.makedirs(OUT, exist_ok=True)


from lib import reset, mat, box, cyl, blob, render_scene


ORANGE, YELLOW = S.PALETTE["orange"], S.PALETTE["yellow"]
BLUE, WHITE = S.PALETTE["blue"], S.PALETTE["white"]
GREY, DARK = S.PALETTE["grey"], S.PALETTE["dark"]
BROWN, RED = S.PALETTE["brown"], S.PALETTE["red"]
ORE = S.PALETTE["ore_iron"]


def assembler():
    box((0, 0, 0.15), (3, 3, 0.3), mat("b", BLUE))
    box((0, 0, 0.9), (2.6, 2.6, 1.2), mat("o", ORANGE), 0.15)
    box((0, 0, 1.52), (2.0, 2.0, 0.08), mat("y", YELLOW))
    cyl((0, 0, 1.65), 0.7, 0.15, mat("w", WHITE), 8)
    cyl((0, 0, 1.66), 0.25, 0.2, mat("y2", YELLOW))


def furnace():
    box((0, 0, 0.9), (2.4, 2.4, 1.8), mat("g", GREY), 0.15)
    box((0, -1.22, 0.7), (1.2, 0.1, 0.9), mat("d", DARK))
    box((0, -1.26, 0.55), (0.9, 0.05, 0.4), mat("r", RED))
    cyl((0.6, 0.6, 2.2), 0.3, 1.0, mat("br", BROWN))


def chest():
    box((0, 0, 0.5), (2.0, 1.4, 1.0), mat("br", BROWN), 0.1)
    box((0, 0, 1.15), (2.1, 1.5, 0.3), mat("y", YELLOW), 0.08)
    box((0, -0.76, 0.85), (0.3, 0.08, 0.35), mat("d", DARK))


def belt():
    # vu de dessus, horizontal (axe X), non incliné
    box((0, 0, 0.05), (3.0, 1.0, 0.1), mat("g", DARK))
    for i in range(-3, 4):
        box((i * 0.4, 0, 0.12), (0.16, 0.7, 0.04), mat(f"y{i}", YELLOW))
    box((0, 0.5, 0.08), (3.0, 0.1, 0.16), mat("o", ORANGE))
    box((0, -0.5, 0.08), (3.0, 0.1, 0.16), mat("o2", ORANGE))


def pole():
    cyl((0, 0, 1.5), 0.12, 3.0, mat("br", BROWN))
    box((0, 0, 2.7), (1.4, 0.12, 0.12), mat("br2", BROWN))
    for x in (-0.6, 0.6):
        blob((x, 0, 2.85), 0.1, mat("w", WHITE))


def ore():
    m = mat("o", ORE)
    for loc, r in [((0, 0, 0.4), 0.7), ((0.7, 0.2, 0.3), 0.5), ((-0.6, 0.3, 0.25), 0.45), ((0.1, -0.7, 0.3), 0.5)]:
        blob(loc, r, m)


def render(builder, name, scale, pitch_deg, cy=0.0):
    reset()
    builder()
    return render_scene(os.path.join(OUT, f"{name}.png"), SIZE, scale, pitch_deg, cy)


# (nom, fonction, taille de cadrage, inclinaison en degrés, décalage vertical caméra)
ITEMS = [("assembleur", assembler, 4.4, S.PITCH_BUILDING_DEG, 0.9), ("four", furnace, 4.4, S.PITCH_BUILDING_DEG, 0.9),
         ("coffre", chest, 3.4, S.PITCH_BUILDING_DEG, 0.5), ("convoyeur", belt, 3.6, S.PITCH_TOPDOWN_DEG, 0.0),
         ("poteau", pole, 4.4, S.PITCH_BUILDING_DEG, 1.2), ("minerai", ore, 3.0, S.PITCH_BUILDING_DEG, 0.3)]
paths = [render(b, n, s, pt, cy) for n, b, s, pt, cy in ITEMS]

tiles = []
for p in paths:
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    a = im[:, :, 3:4] / 255.0
    bg = np.full(im.shape[:2] + (3,), (90, 90, 90), np.float32)
    tiles.append((im[:, :, :3] * a + bg * (1 - a)).astype(np.uint8))
sheet = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
cv2.imwrite(os.path.join(OUT, "planche.png"), sheet)
print("OK", os.path.join(OUT, "planche.png"))
