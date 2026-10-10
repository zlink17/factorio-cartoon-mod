"""Ombre portée et icône d'un assembleur (niveau 1, 2 ou 3).

Usage : python cartoon/blender/assembler_extras.py <dossier_sortie> [niveau 1..3]
Écrit base/entity/assembling-machine-N/assembling-machine-N-shadow.png et base/icons/assembling-machine-N.png.

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
from assembler import N_FRAMES, TIERS, build, fit_camera
from lib import (crop_centered, entity_path, icon_path, mip_strip, render_icon as render_icon_model, sheet,
                 render_shadow as flat_shadow)

SHADOW_GRID = (8, 4)               # colonnes, lignes du fichier d'ombre original
SUN_SHEAR = (0.3, 0.02)             # décalage au sol par unité de hauteur (droite, vers le bas)
CANVAS = 400                       # grand canevas carré pour rendre l'ombre avant découpe
ICON = 64
ICON_FILL = 60                     # plus grande dimension de la machine dans l'icône (px)
ICON_OUTLINE_PX = 0.5   # réglage empirique : rend environ 1,2 px de contour


def render_shadow_cell(cfg, tier, phase, scale, shift, out):
    """Une image d'ombre (cadre de l'original), rendue avec la caméra du sprite."""
    fh = max(cfg["frame"])
    # même nombre de pixels par unité que le sprite (fh / scale), même axe de caméra
    big = flat_shadow(lambda: build(phase, tier), os.path.join(out, "_shadow_big.png"), (CANVAS, CANVAS),
                      scale * CANVAS / fh, SUN_SHEAR, shift_y=shift * fh / CANVAS)
    w, h = cfg["shadow_cell"]
    ox, oy = cfg["shadow_offset"]
    cell = crop_centered(big, (w, h), (ox, oy))
    x0 = int(round(CANVAS / 2 + ox - w / 2))
    y0 = int(round(CANVAS / 2 + oy - h / 2))
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
    planche = sheet(cells, cols)
    cv2.imwrite(entity_path(out, cfg["name"], f"{cfg['name']}-shadow.png"), planche)
    c = np.array(clips)
    print("ombre : emprise min/max", c[:, 0].min(), c[:, 1].min(), c[:, 2].max(), c[:, 3].max(),
          "dans un cadre", w, "x", h, "->", planche.shape[1], "x", planche.shape[0])


def render_icon(out, tier):
    path = os.path.join(out, "_icon.png")
    im = render_icon_model(lambda: build(0.0, tier), path, ICON, ICON_FILL, ICON_OUTLINE_PX)
    strip = mip_strip(im, ICON)
    cv2.imwrite(icon_path(out, TIERS[tier]["name"]), strip)
    print("icône :", strip.shape)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assembler_extras_out"
    tier = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    os.makedirs(out, exist_ok=True)
    scale, shift = fit_camera(out, 0.0, tier)
    render_shadow(out, tier, scale, shift)
    render_icon(out, tier)
