"""Assembleur (3x3) : modèle de référence du style « punk mais cartoon ».

Usage : python tools/blender/assembler.py <dossier_sortie> [angle_engrenages_deg]

Structure reprise de l'assembleur 1 de Factorio : socle sombre, corps en tronc de pyramide
(quatre panneaux à triangle en relief devant, côtés nervurés), dessus en cuivre rouillé avec
un moteur à gauche, des engrenages au centre et deux engrenages en laiton qui dépassent
du bord arrière. Couleurs mesurées sur l'original (voir style.py).

`build(gear_angle)` est paramétré pour l'animation : chaque image de l'animation
est un rendu avec un angle d'engrenage différent.
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import reset, mat, box, cyl, blob, gear, frustum, tri_plate, render_scene

P = S.PALETTE


def build(gear_angle=0.0):
    reset()
    steel, teal, dark = mat("steel", P["grey"]), mat("teal", P["blue"]), mat("dark", P["dark"])
    rust, copper, brass = mat("rust", P["brown"]), mat("copper", P["orange"]), mat("brass", P["yellow"])
    light = mat("light", P["white"])

    # --- socle sombre ---------------------------------------------------------------------
    box((0, 0, 0.06), (2.72, 2.72, 0.12), dark, 0.03)

    # --- corps : tronc de pyramide (2.6 -> 2.15), hauteur 0.95 ---------------------------------
    z0, h, w0, w1 = 0.12, 0.95, 2.6, 2.15
    frustum(z0, h, w0, w0, w1, w1, steel, bevel=0.03)
    tilt = math.degrees(math.atan((w0 - w1) / 2 / h))
    ym = -(w0 + w1) / 4
    xm = (w0 + w1) / 4
    zm = z0 + h / 2
    zt = z0 + h

    # quatre panneaux avant, chacun avec un triangle en relief
    for x in (-0.9, -0.3, 0.3, 0.9):
        box((x, ym - 0.03, zm), (0.52, 0.05, 0.64), teal, 0.02, rot_x=-tilt)
        tri_plate((x, ym - 0.06, zm - 0.02), 0.3, 0.3, 0.03, tilt, dark)

    # côtés nervurés
    for side, rot in ((-1, tilt), (1, -tilt)):
        for k in range(4):
            box((side * (xm + 0.03), -0.84 + k * 0.56, zm), (0.05, 0.14, 0.6), dark, rot_y=rot)

    # --- dessus : plaque de cuivre rouillé, rebord, mécanisme -----------------------------------
    box((0, 0, zt + 0.03), (1.95, 1.95, 0.06), rust, 0.02)
    for (x, y, sx, sy) in [(0, -1.0, 2.15, 0.14), (0, 1.0, 2.15, 0.14), (-1.0, 0, 0.14, 1.95), (1.0, 0, 0.14, 1.95)]:
        box((x, y, zt + 0.07), (sx, sy, 0.14), steel, 0.03)

    # moteur et tuyauterie à gauche
    box((-0.68, -0.25, zt + 0.22), (0.56, 0.95, 0.34), dark, 0.04)
    box((-0.68, -0.25, zt + 0.42), (0.4, 0.7, 0.06), steel)
    cyl((-0.78, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))
    cyl((-0.55, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))

    # engrenages au centre (tournent avec gear_angle)
    gear((0.22, -0.12, zt + 0.15), 0.5, 0.16, 9, gear_angle, steel, dark)
    gear((0.78, -0.55, zt + 0.15), 0.28, 0.16, 6, -gear_angle * 9 / 6 + 20, light, dark)
    gear((0.82, 0.3, zt + 0.15), 0.24, 0.16, 5, gear_angle * 9 / 5 + 25, steel, dark)

    # deux engrenages en laiton qui dépassent du bord arrière
    gear((-0.2, 0.86, zt + 0.36), 0.4, 0.16, 8, -gear_angle + 10, brass, copper)
    gear((0.4, 0.98, zt + 0.4), 0.3, 0.16, 6, gear_angle * 8 / 6 + 5, copper, dark)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_out"
    angle = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    os.makedirs(out, exist_ok=True)
    build(angle)
    path = render_scene(os.path.join(out, "assembleur.png"), size=512, scale=4.4,
                        pitch_deg=S.PITCH_BUILDING_DEG, cy=0.55)
    print("OK", path)
