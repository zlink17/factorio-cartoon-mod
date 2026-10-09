"""Assembleur (3x3) : modèle de référence du style « punk mais cartoon ».

Usage : python tools/blender/assembler.py <dossier_sortie> [angle_engrenages_deg]

Forme calée sur l'assembleur 1 de Factorio : socle, corps en tronc de pyramide (parois
inclinées visibles devant et sur les côtés), bac ouvert avec engrenages sur le dessus.

`build(gear_angle)` est paramétré pour l'animation : chaque image de l'animation
est un rendu avec un angle d'engrenage différent (les autres éléments restent fixes
ou bougent via leurs propres paramètres, à ajouter ici).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import reset, mat, box, cyl, blob, gear, frustum, render_scene

P = S.PALETTE


def build(gear_angle=0.0):
    reset()
    steel, dark, orange = mat("steel", P["grey"]), mat("dark", P["dark"]), mat("orange", P["orange"])
    yellow, brown, white = mat("yellow", P["yellow"]), mat("brown", P["brown"]), mat("white", P["white"])
    red = mat("red", P["red"])

    # --- socle sombre -------------------------------------------------------------
    box((0, 0, 0.1), (2.75, 2.75, 0.2), dark, 0.05)

    # --- corps : tronc de pyramide (2.6 -> 2.15), hauteur 0.95 ---------------------------
    z0, h, w0, w1 = 0.2, 0.95, 2.6, 2.15
    frustum(z0, h, w0, w0, w1, w1, steel, bevel=0.06)
    tilt = math.degrees(math.atan((w0 - w1) / 2 / h))      # inclinaison des parois
    ym = -(w0 + w1) / 4                                     # milieu de la paroi avant
    zm = z0 + h / 2
    # bande de danger au pied de la paroi avant
    for i in range(8):
        box((-1.05 + i * 0.3, ym - 0.1, z0 + 0.1), (0.3, 0.05, 0.14), yellow if i % 2 == 0 else dark, rot_x=-tilt)
    # grande plaque avant rivetée avec fenêtre du four
    box((0, ym - 0.03, zm + 0.08), (2.0, 0.06, 0.62), orange, 0.03, rot_x=-tilt)
    box((0, ym - 0.07, zm + 0.1), (1.3, 0.05, 0.42), dark, 0.03, rot_x=-tilt)
    box((0, ym - 0.1, zm + 0.1), (1.05, 0.04, 0.26), yellow, rot_x=-tilt)
    # tuyau latéral droit qui longe la paroi (dépasse de la silhouette)
    cyl((1.3, 0.1, 0.6), 0.14, 1.9, brown, rot=(90, 0, 0))
    for y in (-0.7, 0.9):
        cyl((1.3, y, 0.6), 0.2, 0.08, dark, rot=(90, 0, 0))

    # --- dessus : bac ouvert, engrenages apparents -------------------------------------
    zt = z0 + h
    box((0, 0, zt + 0.03), (1.95, 1.95, 0.06), dark, 0.02)
    for (x, y, sx, sy) in [(0, -1.0, 2.15, 0.14), (0, 1.0, 2.15, 0.14), (-1.0, 0, 0.14, 1.95), (1.0, 0, 0.14, 1.95)]:
        box((x, y, zt + 0.07), (sx, sy, 0.14), steel, 0.03)
    gear((-0.38, 0.1, zt + 0.17), 0.52, 0.2, 9, gear_angle, yellow, orange)
    gear((0.52, -0.38, zt + 0.17), 0.34, 0.2, 6, -gear_angle * 9 / 6 + 20, orange, dark)
    gear((0.55, 0.55, zt + 0.17), 0.24, 0.2, 5, gear_angle * 9 / 5 + 25, white, dark)

    # --- à l'arrière : une haute cheminée (gauche) et une soupape carrée (droite) ----------
    cyl((-0.8, 0.82, zt + 0.5), 0.2, 0.85, dark)
    cyl((-0.8, 0.82, zt + 0.3), 0.25, 0.1, orange)
    cyl((-0.8, 0.82, zt + 0.95), 0.27, 0.09, dark)
    box((0.8, 0.88, zt + 0.25), (0.5, 0.5, 0.35), brown, 0.04)
    box((0.8, 0.88, zt + 0.46), (0.36, 0.36, 0.08), yellow)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_out"
    angle = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    os.makedirs(out, exist_ok=True)
    build(angle)
    path = render_scene(os.path.join(out, "assembleur.png"), size=512, scale=4.4,
                        pitch_deg=S.PITCH_BUILDING_DEG, cy=0.7)
    print("OK", path)
