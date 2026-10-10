"""Masques de transition entre sols, à bords nets (style cartoon).

Usage : python cartoon/terrain/masks.py <dossier_sortie>

Factorio mélange deux sols voisins avec un masque en dégradé (base/terrain/masks/transition-1, -3, -4 : niveaux de
gris, rangés en cellules) : le sol voisin est dessiné avec le masque comme opacité, d'où des fondus doux. On garde la
forme des masques d'origine mais on remplace le dégradé par un bord franc : léger flou (lobes arrondis, plus de
filaments), seuil à mi-hauteur, le tout à 4 fois la taille puis réduit (bord anticrénelé). Un bord droit entre deux
cellules reste à sa place (un seuil à 50 % après un flou symétrique ne le déplace pas).
Les masques sont partagés avec des sols de Space Age, qui ont donc aussi des transitions nettes.

Écrit <sortie>/base/terrain/masks/transition-N.png (mêmes dimensions que l'original).
"""
import os, sys
import cv2
import numpy as np

FACTORIO_DATA = os.environ.get("FACTORIO_DIR", "/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio") + "/data"
MASKS = ("transition-1", "transition-3", "transition-4")
CELL = 64                   # les masques sont des grilles de cellules de 64 px (une case à l'échelle 0,5)
SS = 4                      # suréchantillonnage
BLUR = 2.0                  # flou avant seuil, en px de l'original : supprime les filaments, arrondit les lobes
THRESHOLD = 0.5


def sharpen_cell(cell):
    """Une cellule en dégradé (uint8) -> bord net anticrénelé. Le flou prolonge les bords de la cellule elle-même :
    deux cellules voisines dans la planche n'ont rien à voir entre elles."""
    h, w = cell.shape
    big = cv2.resize(cell.astype(np.float32) / 255.0, (w * SS, h * SS), interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), BLUR * SS, borderType=cv2.BORDER_REPLICATE)
    hard = (big >= THRESHOLD).astype(np.float32)
    small = cv2.resize(hard, (w, h), interpolation=cv2.INTER_AREA)
    return np.clip(np.round(small * 255), 0, 255).astype(np.uint8)


def sharpen(mask):
    """Masque en dégradé -> masque à bords nets, cellule par cellule, mêmes dimensions."""
    out = mask.copy()
    for y in range(0, mask.shape[0], CELL):
        for x in range(0, mask.shape[1], CELL):
            out[y:y + CELL, x:x + CELL] = sharpen_cell(mask[y:y + CELL, x:x + CELL])
    return out


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "masks_out"
    src = os.path.join(FACTORIO_DATA, "base", "graphics", "terrain", "masks")
    dst = os.path.join(out, "base", "terrain", "masks")
    os.makedirs(dst, exist_ok=True)
    for name in MASKS:
        mask = cv2.imread(os.path.join(src, f"{name}.png"), cv2.IMREAD_GRAYSCALE)
        cv2.imwrite(os.path.join(dst, f"{name}.png"), sharpen(mask))
        print("OK", name)
