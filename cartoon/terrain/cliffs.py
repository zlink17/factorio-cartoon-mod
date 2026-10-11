"""Falaises de Nauvis en colonnes prismatiques, comme les gros rochers (`rocks.py`).

Usage : python cartoon/terrain/cliffs.py <dossier_sortie> [planche[,planche...]|toutes]
        planche = sides, outer, inner, entrance

Chaque orientation de falaise est une cellule de 256 px (4 cases à l'échelle 0,5) de quatre planches : côtés
(`cliff-sides`, 8 x 4 cellules), coins extérieurs et intérieurs (`cliff-outer`, `cliff-inner`), entrées
(`cliff-entrance`, 4 x 4). Le jeu dessine chaque cellule en deux calques : le haut de la falaise, au-dessus des
entités, et le pied (`-lower`), dessous ; plus une ombre portée (`-shadow`).
- silhouette : réunion des corps des deux calques (alpha > 200 : le pied porte en plus un halo d'ombre peu opaque) ;
- colonnes prismatiques posées sur la silhouette, de l'arrière vers l'avant (`rocks.blocks`), à taille fixe en
  cases (une même falaise garde le même grain d'une cellule à l'autre) ; contour noir chaud sur la silhouette ;
- halo du pied : en aplat sombre semi-transparent, comme l'ombre intégrée des rochers ;
- répartition : chaque pixel va au calque qui le portait dans l'original (alpha lissé le plus fort).
Laissés d'origine : ombres portées (`-shadow`, déjà des aplats nets), falaises de Space Age (étape 6).
"""
import os
import sys
import zlib

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from decoratives import FACTORIO_DATA, OUTLINE_BGR, OUTLINE_PX, SHADOW_ALPHA, SS, Rng, hx  # noqa: E402
from rocks import blocks  # noqa: E402

CLIFF = ("#3f2d1e", "#6e5238", "#b59c78")          # flanc sombre, flanc éclairé, dessus : brun de l'original
SHEETS = ("sides", "outer", "inner", "entrance")
CELL = 256
BLOCK_PX = 16.0          # demi-largeur d'une colonne (px du fichier, 64 par case)
HEIGHT = 5.0             # hauteur des colonnes, en demi-largeurs
SIDES = 6
SRC = os.path.join(FACTORIO_DATA, "base", "graphics", "terrain", "cliffs")


def silhouette(body):
    """Masque du corps (bool, taille du fichier) -> à SS, trous bouchés, bord en pans droits."""
    body = body.astype(np.uint8)
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    body = cv2.morphologyEx(body, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    h, w = body.shape
    cs, _ = cv2.findContours(body, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    m = np.zeros((h * SS, w * SS), np.uint8)
    for c in cs:
        if cv2.contourArea(c) < 12:
            continue
        p = cv2.approxPolyDP(c, 1.2, True).astype(np.float32) * SS + SS / 2
        cv2.fillPoly(m, [np.round(p).astype(np.int32)], 1)
    return m


PAD = 48                 # px : la cellule est prolongée de ses bords avant de poser les colonnes (voir render_cell)


def render_cell(up, low, seed):
    """Une cellule (BGRA haut, BGRA pied) -> (haut, pied) redessinés, mêmes tailles.
    Une falaise se continue dans la cellule voisine : on prolonge la cellule (bords répétés) avant de poser les
    colonnes, puis on recadre ; sans cela, les colonnes s'alignent sur le bord de la cellule (ligne de sommets et
    contour droits au raccord)."""
    H, W = up.shape[:2]
    up = cv2.copyMakeBorder(up, PAD, PAD, PAD, PAD, cv2.BORDER_REPLICATE)
    low = cv2.copyMakeBorder(low, PAD, PAD, PAD, PAD, cv2.BORDER_REPLICATE)
    h, w = up.shape[:2]
    au, al = up[:, :, 3].astype(np.float32), low[:, :, 3].astype(np.float32)
    sil = silhouette((au > 200) | (al > 200))
    rgba = np.zeros((h * SS, w * SS, 4), np.float32)
    if sil.sum():
        ys, xs = np.nonzero(sil)
        size = BLOCK_PX * SS / max(xs.max() - xs.min(), ys.max() - ys.min(), 1)   # blocks() : part de la taille
        tone, line = blocks(sil, size, HEIGHT, SIDES, Rng(seed))
        inside = (tone >= 0) & (cv2.dilate(sil, np.ones((2 * SS + 1, 2 * SS + 1), np.uint8)) > 0)
        cols = [hx(t) for t in CLIFF]
        color = np.zeros((h * SS, w * SS, 3), np.float32)
        for t in range(3):
            color[tone == t] = cols[t]
        color[(line > 0) & inside] = np.array(cols[0]) * 0.55
        thick = max(1, int(round(OUTLINE_PX * SS)))
        disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * thick + 1, 2 * thick + 1))
        out = (cv2.dilate(inside.astype(np.uint8), disk) > 0) & ~inside
        color[out] = OUTLINE_BGR
        alpha = (inside | out).astype(np.float32)
        rgba[..., :3] = color * alpha[..., None]
        rgba[..., 3] = alpha * 255
    else:
        alpha = np.zeros((h * SS, w * SS), np.float32)
    a0 = cv2.resize(np.maximum(au, al), (w * SS, h * SS), interpolation=cv2.INTER_LINEAR)
    halo = (cv2.GaussianBlur((a0 > 40).astype(np.float32), (0, 0), SS) > 0.5) & (alpha == 0)
    rgba[halo, 3] = SHADOW_ALPHA * 255
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    im = np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)
    # chaque pixel au calque qui le portait (alpha lissé, pour que les bords et le contour suivent)
    su, sl = cv2.GaussianBlur(au, (0, 0), 3), cv2.GaussianBlur(al, (0, 0), 3)
    to_up = (su >= sl) & ((su > 0) | (sl > 0))
    hi, lo = im.copy(), im.copy()
    hi[~to_up] = 0
    lo[to_up] = 0
    crop = (slice(PAD, PAD + H), slice(PAD, PAD + W))
    return hi[crop], lo[crop]


def build(sheet, out):
    up = cv2.imread(os.path.join(SRC, f"cliff-{sheet}.png"), cv2.IMREAD_UNCHANGED)
    low = cv2.imread(os.path.join(SRC, f"cliff-{sheet}-lower.png"), cv2.IMREAD_UNCHANGED)
    hi, lo = np.zeros_like(up), np.zeros_like(low)
    for y in range(0, up.shape[0], CELL):
        for x in range(0, up.shape[1], CELL):
            seed = zlib.crc32(f"{sheet}-{x}-{y}".encode())
            hi[y:y + CELL, x:x + CELL], lo[y:y + CELL, x:x + CELL] = render_cell(
                up[y:y + CELL, x:x + CELL], low[y:y + CELL, x:x + CELL], seed)
    dst = os.path.join(out, "base", "terrain", "cliffs")
    os.makedirs(dst, exist_ok=True)
    cv2.imwrite(os.path.join(dst, f"cliff-{sheet}.png"), hi)
    cv2.imwrite(os.path.join(dst, f"cliff-{sheet}-lower.png"), lo)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "cliffs_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    for s in (SHEETS if which == "toutes" else which.split(",")):
        build(s, out)
        print("OK", s, flush=True)
