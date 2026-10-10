"""Répartiteurs (splitter, fast-splitter, express-splitter), animés sur 32 images.

Usage : python cartoon/blender/splitter.py <dossier_sortie> [répartiteur|tous]

Pour chaque niveau, écrit les fichiers du prototype d'origine (<jeu>/entity/<nom>/ et <jeu>/icons/, planches de 8 x 4 images) :
  <nom>-north.png, -east.png, -south.png, -west.png     la tête du répartiteur et son ombre
  <nom>-east-top_patch.png, -west-top_patch.png         la moitié haute, dessinée par-dessus les objets (est et ouest)
  <nom>-icon.png                                        icône 64 px + mipmaps

La tête est un bloc gris de 2 cases de large portant deux chevrons à la couleur du niveau, une cloison au milieu,
un chariot qui va d'une voie à l'autre et deux pignons qui tournent avec lui. Le modèle est rendu une fois par image sur un grand canevas centré sur
l'entité, puis découpé aux fenêtres de l'original (taille et décalage des prototypes) : l'est et l'ouest
sont des entités verticales de 2 cases, dont la moitié haute est une pièce à part (« top_patch »).
Les convoyeurs dessous sont ceux de belt.py (le moteur les anime avec la planche des convoyeurs).
"""
import math, os, sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from belt import BELTS, prism
from lib import crop_centered, entity_path, gear, mat, render_with_shadow, reset, save_icon, sheet

P = S.PALETTE
PX_PER_TILE = 64
CANVAS = 480
N_FRAMES = 32
COLUMNS = 8
SHADOW = (0.5, 0.02, 0.4)          # décalage au sol par unité de hauteur (x, y) et opacité
OUTLINE = 0.009

SPLITTERS = {
    "splitter": "transport-belt",
    "fast-splitter": "fast-transport-belt",
    "express-splitter": "express-transport-belt",
    "turbo-splitter": "turbo-transport-belt",
}

# direction -> (flux (x, y), fenêtre de la structure, fenêtre de la pièce du haut ou None)
# fenêtre = (largeur, hauteur, décalage x, décalage y) en px du fichier, par rapport au centre de l'entité
DIRS = {
    "north": ((0, 1),  (160, 70, 14, 0),  None),
    "east":  ((1, 0),  (90, 84, 8, 26),   (90, 104, 8, -40)),
    "south": ((0, -1), (164, 64, 8, 0),   None),
    "west":  ((-1, 0), (90, 86, 12, 24),  (90, 96, 12, -36)),
}

# L'express a un côté ouest un peu plus large (94 px) et décalé de 5 px au lieu de 6 : (structure, pièce du haut)
DIR_OVERRIDES = {
    "express-splitter": {"west": ((94, 86, 10, 24), (94, 96, 10, -36))},
    # le turbo (Space Age) a ses propres fenêtres : (largeur, hauteur, décalage x, y) en px du fichier
    "turbo-splitter": {
        "north": ((158, 66, 15, 2), None),
        "east": ((86, 84, 10, 26), (90, 102, 8, -39)),
        "south": ((164, 64, 8, 1), None),
        "west": ((90, 84, 12, 26), (90, 96, 12, -35)),
    },
}

HALF_LEN = 0.33          # demi-profondeur de la tête le long du flux
HALF_WIDTH = 0.97        # demi-largeur (2 cases)
HEIGHT = 0.3             # assez haut pour que la face avant se voie, assez bas pour tenir dans le cadre du nord (70 px)
CHEVRON = (0.2, 0.3, 0.09)   # chevrons du dessus : recul des branches, demi-envergure, épaisseur (en cases)


def build_head(direction, phase, belt):
    """Ajoute la tête du répartiteur à la scène (sans réinitialiser).

    Un bloc gris acier (il doit ressortir sur les bords des convoyeurs, qui ont la couleur du niveau), deux chevrons
    à la couleur du niveau sur le dessus (un par voie, dans le sens du flux, comme ceux de l'original), une cloison centrale, et un mécanisme bas : un chariot qui va d'une voie à l'autre le long
    d'un rail, deux pignons aux extrémités qui tournent avec lui (crémaillère)."""
    (fx, fy), _, _ = DIRS[direction]
    lx, ly = -fy, fx
    rail, dark = mat("body", P[BELTS[belt]["rail"]]), mat("dark", P["dark"])
    steel, light = mat("steel", P["grey"]), mat("light", P["white"])

    def to_world(s, d, z=0.0):
        return fx * s + lx * d, fy * s + ly * d

    def slab(s0, s1, d0, d1, z0, z1, m, nu=4, nv=8):
        prism(lambda u, v: to_world(s0 + (s1 - s0) * u, d0 + (d1 - d0) * v), nu, nv, z0, z1, m)

    def chevron(s_tip, d_center, z0, z1, m):
        back, half, thick = CHEVRON

        def f(u, v):
            d = (v - 0.5) * 2 * half                          # de -half à +half, la pointe au milieu (v = 0,5)
            s = s_tip - back * abs(d) / half + (u - 0.5) * thick
            return to_world(s, d_center + d)
        prism(f, 1, 2, z0, z1, m)

    slab(-HALF_LEN, HALF_LEN, -HALF_WIDTH, HALF_WIDTH, 0.0, HEIGHT, steel)                 # bloc
    top = HEIGHT
    for lane in (-0.5, 0.5):
        chevron(0.12, lane, top, top + 0.03, rail)                                           # un chevron par voie
    slab(-HALF_LEN, HALF_LEN, -0.05, 0.05, 0.0, top + 0.06, dark, 8, 1)                      # cloison centrale
    travel, gear_r = 0.52, 0.13
    pos = travel * math.sin(2 * math.pi * phase)
    slab(-0.24, -0.16, -0.74, 0.74, top, top + 0.02, steel, 2, 16)                           # rail (bord arrière)
    slab(-0.27, -0.13, pos - 0.14, pos + 0.14, top, top + 0.09, light, 2, 2)                 # chariot
    spin = math.degrees(pos / gear_r)
    for side in (-0.82, 0.82):
        x, y = to_world(-0.2, side)
        gear((x, y, top + 0.04), gear_r, 0.07, 8, spin, light, dark)
    return to_world


def build_scene(direction, phase, belt):
    reset()
    build_head(direction, phase, belt)


def render_canvas(direction, phase, belt, out):
    """Le répartiteur et son ombre à plat sur un grand canevas centré sur l'entité."""
    return render_with_shadow(lambda: build_scene(direction, phase, belt), os.path.join(out, "_sp.png"), CANVAS,
                              CANVAS / PX_PER_TILE, SHADOW, OUTLINE)


def window_origin(window):
    w, h, sx, sy = window
    return int(round(CANVAS / 2 + sx - w / 2)), int(round(CANVAS / 2 + sy - h / 2))


def crop(canvas, window):
    return crop_centered(canvas, window[:2], window[2:])


def crop_patch(sprite, shadowed, patch, window):
    """Pièce du haut : avec l'ombre, sauf sur les lignes déjà couvertes par la structure (sinon l'ombre serait doublée)."""
    out = crop(shadowed, patch)
    x0, y0 = window_origin(patch)
    ws, hs, _, _ = window
    _, ys = window_origin(window)
    lo, hi = max(ys, y0) - y0, min(ys + hs, y0 + patch[1]) - y0
    if hi > lo:
        out[lo:hi] = crop(sprite, patch)[lo:hi]
    return out


def build_icon(name, belt, out):
    def model():
        reset()
        build_head("north", 0.0, belt)
    save_icon(out, name, model)


def build_splitter(name, out):
    belt = SPLITTERS[name]
    for direction, (_, window, patch) in DIRS.items():
        window, patch = DIR_OVERRIDES.get(name, {}).get(direction, (window, patch))
        main, top = [], []
        for i in range(N_FRAMES):
            sprite, shadowed = render_canvas(direction, i / N_FRAMES, belt, out)
            main.append(crop(shadowed, window))
            if patch:
                top.append(crop_patch(sprite, shadowed, patch, window))
        cv2.imwrite(entity_path(out, name, f"{name}-{direction}.png"), sheet(main, COLUMNS))
        if patch:
            cv2.imwrite(entity_path(out, name, f"{name}-{direction}-top_patch.png"), sheet(top, COLUMNS))
    build_icon(name, belt, out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "splitter_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (SPLITTERS if which == "tous" else [which]):
        build_splitter(name, out)
        print("OK", name, flush=True)
