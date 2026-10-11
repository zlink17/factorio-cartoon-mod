"""Cadrage : l'art (1 px = 1 px d'art) agrandi et posé dans le cadre exact de l'original, aligné sur la grille du monde.

Contrat (docs/pixel/plan.md, section 3) : 16 px d'art par case. Un fichier à l'échelle `scale` compte 32 / scale px
par case, donc un px d'art y fait FACTEUR = 2 / scale px (4 px pour scale = 0.5, l'échelle de presque tout le jeu).

Grille du monde : le jeu centre le cadre (W x H px) sur la position de l'entité + `shift` (en cases). La position
tombe donc à la colonne W/2 - shift.x * 32/scale du cadre (idem en y) ; on y pose le point d'ancrage de l'art (un
coin de pixel d'art), si bien que les bords des pixels d'art tombent tous sur les 1/16 de case du monde.
"""
import os

import numpy as np
from PIL import Image


def factor(scale=0.5):
    f = 2 / scale
    if abs(f - round(f)) > 1e-9:
        raise ValueError(f"échelle {scale} : un px d'art ne fait pas un nombre entier de px de fichier")
    return int(round(f))


def upscale(a, k):
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def origin(frame, shift=(0, 0), scale=0.5):
    """Position de l'entité dans le cadre, en px de fichier (colonne, ligne)."""
    w, h = frame
    per_tile = 32 / scale
    return w / 2 - shift[0] * per_tile, h / 2 - shift[1] * per_tile


def place(art, anchor, frame, shift=(0, 0), scale=0.5, clip_ok=False):
    """Pose `art` (tableau RGBA à la résolution d'art) dans un cadre `frame` = (W, H) px de fichier.
    `anchor` = (x, y) en px d'art : le coin de pixel qui doit tomber sur la position de l'entité.
    Lève une erreur si l'art déborde du cadre (sauf `clip_ok`)."""
    k = factor(scale)
    ox, oy = origin(frame, shift, scale)
    left, top = ox - anchor[0] * k, oy - anchor[1] * k
    # cadre de largeur impaire ou shift fin : la position tombe entre deux px de fichier ; on arrondit (écart d'au
    # plus 1/128 de case, invisible), comme grid_offset
    left, top = int(round(left)), int(round(top))
    big = upscale(art, k)
    out = np.zeros((frame[1], frame[0], 4), np.uint8)
    x0, y0 = max(left, 0), max(top, 0)
    x1, y1 = min(left + big.shape[1], frame[0]), min(top + big.shape[0], frame[1])
    clipped = big[y0 - top:y1 - top, x0 - left:x1 - left]
    if not clip_ok and (clipped[..., 3].sum() != big[..., 3].sum()):
        raise ValueError(f"l'art ({art.shape[1]} x {art.shape[0]} px d'art, ancre {anchor}) déborde du cadre {frame}")
    out[y0:y1, x0:x1] = clipped
    return out


def grid_offset(frame, shift=(0, 0), scale=0.5):
    """Décalage (x, y) de la grille des px d'art dans le cadre, en px de fichier (0 à FACTEUR - 1)."""
    k = factor(scale)
    ox, oy = origin(frame, shift, scale)
    return int(round(ox)) % k, int(round(oy)) % k     # même arrondi que place (round de Python, vers le pair)


def sheet(frames, line_length):
    """Planche : images (toutes de même taille) rangées par lignes de `line_length`."""
    h, w = frames[0].shape[:2]
    rows = (len(frames) + line_length - 1) // line_length
    out = np.zeros((h * rows, w * min(line_length, len(frames)), 4), np.uint8)
    for i, f in enumerate(frames):
        r, c = divmod(i, line_length)
        out[r * h:(r + 1) * h, c * w:(c + 1) * w] = f
    return out


def icon(art, size=64):
    """Icône à mipmaps (bande 120 x 64 pour 64) depuis un art de size/2 px (32 px d'art, décision de Bastien).
    Niveau 64 : art x 2 ; 32 : l'art ; 16 et 8 : un px sur 2, sur 4 (plus proche voisin, pas de flou)."""
    n = size // 2
    if art.shape[:2] != (n, n):
        raise ValueError(f"icône : art de {art.shape[1]} x {art.shape[0]} px, {n} x {n} attendu")
    levels = [upscale(art, 2), art, art[::2, ::2], art[::4, ::4]]
    strip = np.zeros((size, sum(level.shape[1] for level in levels), 4), np.uint8)
    x = 0
    for level in levels:
        strip[:level.shape[0], x:x + level.shape[1]] = level
        x += level.shape[1]
    return strip


def save(a, out, rel):
    """Écrit le tableau RGBA en <out>/<rel> (rel = chemin sous graphics/overrides, ex. base/entity/x/x.png)."""
    path = os.path.join(out, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(a, "RGBA").save(path, optimize=True)
    return path
