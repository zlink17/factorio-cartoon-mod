"""Ombre portée et icône d'un assembleur (niveau 1, 2 ou 3).

Usage : python cartoon/blender/assembler_extras.py <dossier_sortie> [niveau 1..3]
Écrit assembling-machine-N-shadow.png et assembling-machine-N-icon.png (à installer dans
cartoon/mod/graphics/overrides/base/entity/assembling-machine-N/ et .../icons/assembling-machine-N.png).

Ombre : le même modèle, projeté à plat au sol, noir uni, rendu avec la caméra du sprite.
Elle est découpée à la taille et à la position de l'ombre originale (voir TIERS dans assembler.py),
puis rangée dans la grille 8 x 4 du fichier original. Niveau 1 : une seule image recopiée 32 fois ;
niveaux 2 et 3 : une image par phase de l'animation (les pistons et les bras bougent).
Icône : rendu 64 x 64 avec un contour plus épais, plus la bande de mipmaps (64, 32, 16, 8 -> 120 x 64).
"""
import os, sys
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from assembler import N_FRAMES, TIERS, build, fit_camera, measure
from lib import flatten_to_shadow, mip_strip, render_icon as render_icon_model, render_scene

SHADOW_GRID = (8, 4)               # colonnes, lignes du fichier d'ombre original
SUN_SHEAR = (0.3, 0.02)             # décalage au sol par unité de hauteur (droite, vers le bas)
CANVAS = 400                       # grand canevas carré pour rendre l'ombre avant découpe
ICON = 64
ICON_FILL = 60                     # plus grande dimension de la machine dans l'icône (px)
ICON_OUTLINE_PX = 0.5   # réglage empirique : rend environ 1,2 px de contour


def render_shadow_cell(cfg, tier, phase, scale, shift, out):
    """Une image d'ombre (cadre de l'original), rendue avec la caméra du sprite."""
    build(phase, tier)
    flatten_to_shadow(*SUN_SHEAR)
    path = os.path.join(out, "_shadow_big.png")
    fh = max(cfg["frame"])
    # même nombre de pixels par unité que le sprite (fh / scale), même axe de caméra
    render_scene(path, size=(CANVAS, CANVAS), scale=scale * CANVAS / fh,
                 pitch_deg=S.PITCH_BUILDING_DEG, shift_y=shift * fh / CANVAS, outline=False)
    big = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    w, h = cfg["shadow_cell"]
    ox, oy = cfg["shadow_offset"]
    x0 = int(round(CANVAS / 2 + ox - w / 2))
    y0 = int(round(CANVAS / 2 + oy - h / 2))
    cell = big[y0:y0 + h, x0:x0 + w].copy()
    cell[:, :, :3] = 0
    ys, xs = np.where(big[:, :, 3] > 10)
    clip = (xs.min() - x0, ys.min() - y0, xs.max() - x0, ys.max() - y0)   # emprise dans le cadre
    return cell, clip


def render_shadow(out, tier, scale, shift):
    cfg = TIERS[tier]
    cols, rows = SHADOW_GRID
    n = N_FRAMES if cfg["shadow_animated"] else 1
    cells, clips = [], []
    for i in range(n):
        cell, clip = render_shadow_cell(cfg, tier, i / N_FRAMES, scale, shift, out)
        cells.append(cell)
        clips.append(clip)
    cells = cells * (cols * rows) if n == 1 else cells
    h, w = cells[0].shape[:2]
    sheet = np.vstack([np.hstack(cells[r * cols:(r + 1) * cols]) for r in range(rows)])
    cv2.imwrite(os.path.join(out, f"{cfg['name']}-shadow.png"), sheet)
    c = np.array(clips)
    print("ombre : emprise min/max", c[:, 0].min(), c[:, 1].min(), c[:, 2].max(), c[:, 3].max(),
          "dans un cadre", w, "x", h, "->", sheet.shape[1], "x", sheet.shape[0])


def render_icon(out, tier):
    path = os.path.join(out, "_icon.png")
    im = render_icon_model(lambda: build(0.0, tier), path, ICON, ICON_FILL, ICON_OUTLINE_PX)
    strip = mip_strip(im, ICON)
    cv2.imwrite(os.path.join(out, f"{TIERS[tier]['name']}-icon.png"), strip)
    print("icône :", strip.shape)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_extras_out"
    tier = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    os.makedirs(out, exist_ok=True)
    scale, shift = fit_camera(out, 0.0, tier)
    render_shadow(out, tier, scale, shift)
    render_icon(out, tier)
