"""Assembleur (3x3) : modèle de référence du style « punk mais cartoon ».

Usage : python tools/blender/assembler.py <dossier_sortie> [phase 0..1]

Structure reprise de l'assembleur 1 de Factorio : socle sombre, corps en tronc de pyramide
(quatre panneaux à triangle en relief devant), dessus en cuivre rouillé avec
un moteur à gauche, des engrenages au centre et deux engrenages en laiton qui dépassent
du bord arrière. Couleurs mesurées sur l'original (voir style.py).

`build(phase)` est paramétré pour l'animation : chaque image est un rendu avec une phase
différente (0 à 1). Voir animate.py pour la planche de 32 images.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import reset, mat, box, cyl, blob, gear, frustum, tri_plate, render_scene

P = S.PALETTE


# Animation : `phase` va de 0 (inclus) à 1 (exclu) sur une boucle complète. Chaque engrenage tourne
# d'un nombre entier de dents sur la boucle, pour que la dernière image enchaîne sur la première.
CENTER_PITCHES = 2      # le grand engrenage central avance de 2 dents par boucle
BRASS_PITCHES = 2       # l'engrenage en laiton avance de 2 dents par boucle
N_FRAMES = 32           # comme l'original (planche de 8 x 4 images)


def build(phase=0.0):
    reset()
    steel, teal, dark = mat("steel", P["grey"]), mat("teal", P["blue"]), mat("dark", P["dark"])
    rust, copper, brass = mat("rust", P["brown"]), mat("copper", P["orange"]), mat("brass", P["yellow"])
    light = mat("light", P["white"])

    # --- socle sombre ---------------------------------------------------------------------
    box((0, 0, 0.06), (2.72, 2.72, 0.12), dark, 0.03)

    # --- corps : tronc de pyramide (2.6 -> 2.15), hauteur 0.95 ---------------------------------
    z0, h, w0, w1 = 0.12, 1.3, 2.6, 2.15
    frustum(z0, h, w0, w0, w1, w1, steel, bevel=0.03)
    tilt = math.degrees(math.atan((w0 - w1) / 2 / h))
    ym = -(w0 + w1) / 4
    xm = (w0 + w1) / 4
    zm = z0 + h / 2
    zt = z0 + h

    # quatre panneaux avant, chacun avec un triangle en relief
    for x in (-0.9, -0.3, 0.3, 0.9):
        box((x, ym - 0.03, zm), (0.52, 0.05, 0.95), teal, 0.02, rot_x=-tilt)
        tri_plate((x, ym - 0.06, zm - 0.04), 0.32, 0.36, 0.03, tilt, dark)

    # --- dessus : plaque de cuivre rouillé, rebord, mécanisme -----------------------------------
    box((0, 0, zt + 0.03), (1.95, 1.95, 0.06), rust, 0.02)
    for (x, y, sx, sy) in [(0, -1.0, 2.15, 0.14), (0, 1.0, 2.15, 0.14), (-1.0, 0, 0.14, 1.95), (1.0, 0, 0.14, 1.95)]:
        box((x, y, zt + 0.07), (sx, sy, 0.14), steel, 0.03)

    # moteur et tuyauterie à gauche
    box((-0.68, -0.25, zt + 0.22), (0.56, 0.95, 0.34), dark, 0.04)
    box((-0.68, -0.25, zt + 0.42), (0.4, 0.7, 0.06), steel)
    cyl((-0.78, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))
    cyl((-0.55, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))

    # engrenages au centre : posés pour que les dents se frôlent sans se traverser
    #   (distance entre centres = rayon pointe 1 + rayon pointe 2 + 0.02, pointe = 1.22 x rayon)
    #   deux engrenages qui s'engrènent tournent en sens inverse, à des vitesses inverses de leurs dents
    big = phase * CENTER_PITCHES * 360 / 9
    gear((0.05, -0.15, zt + 0.15), 0.42, 0.16, 9, big, steel, dark)
    gear((0.73, 0.17, zt + 0.15), 0.18, 0.16, 6, -big * 9 / 6 + 20, light, dark)
    gear((0.60, -0.70, zt + 0.15), 0.2, 0.16, 5, -big * 9 / 5 + 25, steel, dark)

    # deux engrenages en laiton qui dépassent du bord arrière (s'engrènent entre eux)
    bras = phase * BRASS_PITCHES * 360 / 8
    gear((-0.35, 0.9, zt + 0.46), 0.36, 0.16, 8, bras + 10, brass, copper)
    gear((0.43, 0.97, zt + 0.5), 0.26, 0.16, 6, -bras * 8 / 6 + 5, copper, dark)


# Cadre et position de la machine dans le sprite original (assembling-machine-1.png, image 0)
FRAME = (214, 226)
TARGET_BBOX = (25, 2, 188, 199)          # x0, y0, x1, y1 des pixels opaques (alpha > 200)


def measure(path):
    import cv2, numpy as np
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    ys, xs = np.where(im[:, :, 3] > 200)
    return xs.min(), ys.min(), xs.max(), ys.max()


def fit_camera(out, phase=0.0):
    """Cherche l'échelle et le décalage de caméra qui donnent la même emprise que l'original."""
    tw = TARGET_BBOX[2] - TARGET_BBOX[0] + 1
    tcy = (TARGET_BBOX[1] + TARGET_BBOX[3]) / 2
    scale, shift = 3.9, 0.0
    path = os.path.join(out, "_fit.png")
    for _ in range(4):
        build(phase)
        render_scene(path, size=FRAME, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)
        x0, y0, x1, y1 = measure(path)
        w, cy = x1 - x0 + 1, (y0 + y1) / 2
        scale *= w / tw                                  # plus grand si le sprite est trop petit
        shift += (cy - tcy) / max(FRAME) * (-1)          # recentre verticalement
    os.remove(path)
    return scale, shift


def render_phase(path, phase, scale, shift):
    """Rend une image de l'animation avec une caméra déjà calée (identique pour toutes les images)."""
    build(phase)
    return render_scene(path, size=FRAME, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)


def render_fitted(out, phase=0.0, name="assembleur.png"):
    scale, shift = fit_camera(out, phase)
    path = render_phase(os.path.join(out, name), phase, scale, shift)
    return path, scale, shift


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_out"
    phase = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    os.makedirs(out, exist_ok=True)
    path, scale, shift = render_fitted(out, phase)
    print("OK", path, "scale", round(scale, 3), "shift_y", round(shift, 4), "bbox", measure(path))
