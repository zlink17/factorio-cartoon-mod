"""Assembleur (3x3) : modèle de référence du style « punk mais cartoon ».

Usage : python cartoon/blender/assembler.py <dossier_sortie> [phase 0..1] [facteur de taille] [niveau 1..3]

Structure reprise de l'assembleur 1 de Factorio : socle sombre, corps en tronc de pyramide
(quatre panneaux à triangle en relief devant), dessus en cuivre rouillé avec
un moteur à gauche, des engrenages au centre et deux engrenages en laiton qui dépassent
du bord arrière. Couleurs mesurées sur l'original (voir style.py).

Niveaux : 1 = gris-vert, engrenages ; 2 = bleu, bras articulé ; 3 = olive, deux bras et deux pistons.
Le corps, les panneaux et la plaque du dessus sont communs ; la couleur et le mécanisme changent.

`build(phase, tier)` est paramétré pour l'animation : chaque image est un rendu avec une phase
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


# Un niveau = une couleur, un cadre (celui de l'original) et la géométrie de l'ombre.
# bbox : pixels opaques de l'image 0 de l'original (x0, y0, x1, y1) ; seuls x0, x1 et y1 servent au calage
# (le haut dépend du mécanisme). shadow_cell / shadow_offset : taille de l'image d'ombre et position de
# son centre par rapport au centre du sprite (px du fichier, 64 px par case).
TIERS = {
    1: dict(name="assembling-machine-1", frame=(214, 226), bbox=(25, 2, 188, 199), body="grey", panel="blue",
            height=1.3, shadow_cell=(190, 165), shadow_offset=(17, 6), shadow_animated=False),
    2: dict(name="assembling-machine-2", frame=(214, 218), bbox=(26, 1, 187, 190), body="steel_blue", panel="navy",
            height=1.25, shadow_cell=(196, 163), shadow_offset=(24, 1.5), shadow_animated=True),
    3: dict(name="assembling-machine-3", frame=(214, 237), bbox=(26, 1, 187, 209), body="olive", panel="olive_dark",
            height=1.3, shadow_cell=(260, 162), shadow_offset=(56, 9.5), shadow_animated=True),
}
FRAME = TIERS[1]["frame"]          # conservé pour les scripts du niveau 1
TARGET_BBOX = TIERS[1]["bbox"]


def arm(base, angle_deg, length, z, width, m, joint_m):
    """Segment de bras horizontal partant de `base` (x, y) ; renvoie son extrémité (x, y)."""
    a = math.radians(angle_deg)
    end = (base[0] + length * math.cos(a), base[1] + length * math.sin(a))
    box(((base[0] + end[0]) / 2, (base[1] + end[1]) / 2, z), (length, width, 0.12), m, 0.03, rot_z=angle_deg)
    cyl((*base, z), width * 0.75, 0.2, joint_m, verts=16)
    return end


def scara(base, phase, offset, z, light, dark, mirror=False):
    """Bras articulé à deux segments qui va chercher une pièce et la ramène (boucle sur `phase`).

    Les angles sont choisis pour que le bras reste sur la plaque du dessus (|x|, |y| < 0.93) ;
    `mirror` le retourne en y pour le placer de l'autre côté."""
    s = 2 * math.pi * (phase + offset)
    a1 = 195 + 25 * math.sin(s)
    a2 = a1 + 50 * math.sin(s + 1.2)
    if mirror:
        a1, a2 = -a1, -a2
    cyl((*base, z - 0.2), 0.15, 0.4, dark, verts=16)
    j = arm(base, a1, 0.6, z, 0.17, light, dark)
    end = arm(j, a2, 0.45, z + 0.1, 0.15, light, dark)
    box((*end, z + 0.1), (0.2, 0.28, 0.1), dark, 0.02, rot_z=a2)


def piston(x, y, zt, phase, offset, steel, light, red):
    """Piston vertical : fût fixe, tige qui monte et descend, embout rouge."""
    lift = 0.5 + 0.5 * math.sin(2 * math.pi * (phase + offset))
    cyl((x, y, zt + 0.4), 0.15, 0.8, steel, verts=20)
    top = zt + 0.7 + 0.4 * lift
    cyl((x, y, (zt + 0.4 + top) / 2 + 0.2), 0.07, top - zt - 0.4 + 0.4, light, verts=12)
    cyl((x, y, top + 0.42), 0.12, 0.1, red, verts=16)


def build(phase=0.0, tier=1):
    reset()
    cfg = TIERS[tier]
    steel, teal, dark = mat("steel", P[cfg["body"]]), mat("teal", P[cfg["panel"]]), mat("dark", P["dark"])
    rust, copper, brass = mat("rust", P["brown"]), mat("copper", P["orange"]), mat("brass", P["yellow"])
    light = mat("light", P["white"])

    # --- socle sombre ---------------------------------------------------------------------
    box((0, 0, 0.06), (2.72, 2.72, 0.12), dark, 0.03)

    # --- corps : tronc de pyramide (2.6 -> 2.15) ---------------------------------------------
    z0, h, w0, w1 = 0.12, cfg["height"], 2.6, 2.15
    frustum(z0, h, w0, w0, w1, w1, steel, bevel=0.03)
    tilt = math.degrees(math.atan((w0 - w1) / 2 / h))
    ym = -(w0 + w1) / 4
    xm = (w0 + w1) / 4
    zm = z0 + h / 2
    zt = z0 + h

    # quatre panneaux avant, chacun avec un triangle en relief
    for x in (-0.9, -0.3, 0.3, 0.9):
        box((x, ym - 0.03, zm), (0.52, 0.05, h * 0.95 / 1.3), teal, 0.02, rot_x=-tilt)
        tri_plate((x, ym - 0.06, zm - 0.04), 0.32, 0.36, 0.03, tilt, dark)

    # --- dessus : plaque de cuivre rouillé, rebord -----------------------------------------------
    box((0, 0, zt + 0.03), (1.95, 1.95, 0.06), rust, 0.02)
    for (x, y, sx, sy) in [(0, -1.0, 2.15, 0.14), (0, 1.0, 2.15, 0.14), (-1.0, 0, 0.14, 1.95), (1.0, 0, 0.14, 1.95)]:
        box((x, y, zt + 0.07), (sx, sy, 0.14), steel, 0.03)

    # moteur et tuyauterie à gauche (commun aux trois niveaux)
    box((-0.68, -0.25, zt + 0.22), (0.56, 0.95, 0.34), dark, 0.04)
    box((-0.68, -0.25, zt + 0.42), (0.4, 0.7, 0.06), steel)
    cyl((-0.78, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))
    cyl((-0.55, 0.5, zt + 0.18), 0.09, 0.8, copper, rot=(90, 0, 0))

    if tier == 1:
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
    elif tier == 2:
        # un bras articulé et un petit engrenage de renvoi
        scara((0.62, 0.5), phase, 0.0, zt + 0.5, light, dark)
        gear((0.55, -0.62, zt + 0.15), 0.26, 0.16, 7, phase * 2 * 360 / 7, brass, dark)
    else:
        # deux bras en opposition de phase, deux pistons au fond à droite
        red = mat("red", P["red"])
        scara((0.62, 0.5), phase, 0.0, zt + 0.5, light, dark)
        scara((0.62, -0.5), phase, 0.5, zt + 0.62, light, dark, mirror=True)
        piston(0.2, 0.78, zt, phase, 0.0, steel, light, red)
        piston(0.62, 0.78, zt, phase, 0.5, steel, light, red)


def measure(path):
    import cv2, numpy as np
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    ys, xs = np.where(im[:, :, 3] > 200)
    return xs.min(), ys.min(), xs.max(), ys.max()


def fit_camera(out, phase=0.0, tier=1):
    """Cherche l'échelle et le décalage de caméra qui donnent la même largeur et le même bas que l'original.

    Le bas (face avant) sert de repère vertical : le haut dépend du mécanisme (pistons, engrenages)."""
    cfg = TIERS[tier]
    frame, target = cfg["frame"], cfg["bbox"]
    tw = target[2] - target[0] + 1
    scale, shift = 3.9, 0.0
    path = os.path.join(out, "_fit.png")
    for _ in range(4):
        build(phase, tier)
        render_scene(path, size=frame, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)
        x0, y0, x1, y1 = measure(path)
        scale *= (x1 - x0 + 1) / tw                      # plus grand si le sprite est trop petit
        shift += (y1 - target[3]) / max(frame) * (-1)    # recale le bas
    os.remove(path)
    return scale, shift


def render_phase(path, phase, scale, shift, factor=1, tier=1):
    """Rend une image de l'animation avec une caméra déjà calée (identique pour toutes les images).

    `factor` > 1 donne le même cadrage en plus grand (entrée de la passe IA)."""
    build(phase, tier)
    frame = TIERS[tier]["frame"]
    size = (frame[0] * factor, frame[1] * factor)
    return render_scene(path, size=size, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift)


def render_fitted(out, phase=0.0, name="assembleur.png", factor=1, tier=1):
    scale, shift = fit_camera(out, phase, tier)
    path = render_phase(os.path.join(out, name), phase, scale, shift, factor, tier)
    return path, scale, shift


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_out"
    phase = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    factor = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    tier = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    os.makedirs(out, exist_ok=True)
    path, scale, shift = render_fitted(out, phase, factor=factor, tier=tier)
    print("OK", path, "scale", round(scale, 3), "shift_y", round(shift, 4), "bbox", measure(path))
