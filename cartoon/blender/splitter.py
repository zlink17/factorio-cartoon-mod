"""Répartiteurs (splitter, fast-splitter, express-splitter), animés sur 32 images.

Usage : python cartoon/blender/splitter.py <dossier_sortie> [répartiteur|tous]

Pour chaque niveau, écrit les fichiers du prototype d'origine (planches de 8 x 4 images) :
  <nom>-north.png, -east.png, -south.png, -west.png     la tête du répartiteur et son ombre
  <nom>-east-top_patch.png, -west-top_patch.png         la moitié haute, dessinée par-dessus les objets (est et ouest)
  <nom>-icon.png                                        icône 64 px + mipmaps

La tête est un bloc de 2 cases de large (couleur du niveau), une cloison au milieu, un chariot qui va
d'une voie à l'autre et deux pignons qui tournent avec lui. Le modèle est rendu une fois par image sur un grand canevas centré sur
l'entité, puis découpé aux fenêtres de l'original (taille et décalage des prototypes) : l'est et l'ouest
sont des entités verticales de 2 cases, dont la moitié haute est une pièce à part (« top_patch »).
Les convoyeurs dessous sont ceux de belt.py (le moteur les anime avec la planche des convoyeurs).
"""
import math, os, sys
import bpy
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from belt import BELTS, prism
from lib import cyl, flatten_to_shadow, gear, mat, mip_strip, render_icon, render_scene, reset

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

HALF_LEN = 0.3           # demi-profondeur de la tête le long du flux
HALF_WIDTH = 0.97        # demi-largeur (2 cases)
HEIGHT = 0.26


def build_head(direction, phase, belt):
    """Ajoute la tête du répartiteur à la scène (sans réinitialiser)."""
    (fx, fy), _, _ = DIRS[direction]
    lx, ly = -fy, fx
    rail, dark = mat("body", P[BELTS[belt]["rail"]]), mat("dark", P["dark"])
    steel, light = mat("steel", P["grey"]), mat("light", P["white"])

    def to_world(s, d, z=0.0):
        return fx * s + lx * d, fy * s + ly * d

    def slab(s0, s1, d0, d1, z0, z1, m, nu=4, nv=8):
        prism(lambda u, v: to_world(s0 + (s1 - s0) * u, d0 + (d1 - d0) * v), nu, nv, z0, z1, m)

    slab(-HALF_LEN, HALF_LEN, -HALF_WIDTH, HALF_WIDTH, 0.0, HEIGHT, rail)               # bloc
    slab(-HALF_LEN + 0.07, HALF_LEN - 0.07, -HALF_WIDTH + 0.08, HALF_WIDTH - 0.08, HEIGHT, HEIGHT + 0.03, dark)   # plateau
    slab(-HALF_LEN - 0.1, HALF_LEN + 0.1, -0.04, 0.04, 0.0, HEIGHT + 0.08, steel, 8, 1)                      # cloison centrale
    # mécanisme : un chariot qui va d'une voie à l'autre le long d'un rail, et deux pignons aux extrémités qui
    # tournent avec lui (crémaillère) ; deux petits coulisseaux de part et d'autre vont en sens inverse
    travel, gear_r = 0.52, 0.15
    pos = travel * math.sin(2 * math.pi * phase)
    top = HEIGHT + 0.03
    slab(-0.1, 0.1, -0.74, 0.74, top, top + 0.025, steel, 2, 16)                               # rail
    slab(-0.19, 0.19, pos - 0.19, pos + 0.19, top, top + 0.15, light, 2, 2)                    # chariot
    slab(-0.1, 0.1, pos - 0.1, pos + 0.1, top + 0.15, top + 0.19, dark, 2, 2)
    for k, s in enumerate((-0.25, 0.25)):
        c = -pos * (1 if k else -1) * 0.9
        slab(s - 0.045, s + 0.045, c - 0.09, c + 0.09, top, top + 0.08, steel, 2, 2)           # coulisseaux
    spin = math.degrees(pos / gear_r)
    for side in (-0.8, 0.8):
        x, y = to_world(0.0, side)
        gear((x, y, top + 0.06), gear_r, 0.1, 8, spin, light, dark)
    return to_world


def build_scene(direction, phase, belt):
    reset()
    build_head(direction, phase, belt)


def render_canvas(direction, phase, belt, out):
    """Le répartiteur et son ombre à plat sur un grand canevas centré sur l'entité."""
    path = os.path.join(out, "_sp.png")
    scale = CANVAS / PX_PER_TILE
    build_scene(direction, phase, belt)
    render_scene(path, size=CANVAS, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline_units=OUTLINE)
    sprite = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    build_scene(direction, phase, belt)
    flatten_to_shadow(SHADOW[0], SHADOW[1])
    render_scene(path, size=CANVAS, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline=False)
    shadow = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    shadow[:, :, :3] = 0
    shadow[:, :, 3] = (shadow[:, :, 3] * SHADOW[2]).astype(np.uint8)
    return sprite, over(sprite, shadow)


def over(top, bottom):
    ta, ba = top[:, :, 3:4] / 255.0, bottom[:, :, 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


def window_origin(window):
    w, h, sx, sy = window
    return int(round(CANVAS / 2 + sx - w / 2)), int(round(CANVAS / 2 + sy - h / 2))


def crop(canvas, window):
    w, h, _, _ = window
    x0, y0 = window_origin(window)
    return canvas[y0:y0 + h, x0:x0 + w]


def crop_patch(sprite, shadowed, patch, window):
    """Pièce du haut : avec l'ombre, sauf sur les lignes déjà couvertes par la structure (sinon l'ombre serait doublée)."""
    out = crop(shadowed, patch).copy()
    x0, y0 = window_origin(patch)
    ws, hs, _, _ = window
    _, ys = window_origin(window)
    lo, hi = max(ys, y0) - y0, min(ys + hs, y0 + patch[1]) - y0
    if hi > lo:
        out[lo:hi] = crop(sprite, patch)[lo:hi]
    return out


def build_sheet(frames, size):
    w, h = size
    rows = N_FRAMES // COLUMNS
    return np.vstack([np.hstack(frames[r * COLUMNS:(r + 1) * COLUMNS]) for r in range(rows)])


def build_icon(belt, out):
    def model():
        reset()
        build_head("north", 0.0, belt)
    return mip_strip(render_icon(model, os.path.join(out, "_icon.png"), 64, 60), 64)


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
        cv2.imwrite(os.path.join(out, f"{name}-{direction}.png"), build_sheet(main, window[:2]))
        if patch:
            cv2.imwrite(os.path.join(out, f"{name}-{direction}-top_patch.png"), build_sheet(top, patch[:2]))
    cv2.imwrite(os.path.join(out, f"{name}-icon.png"), build_icon(belt, out))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "splitter_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (SPLITTERS if which == "tous" else [which]):
        build_splitter(name, out)
        print("OK", name, flush=True)
