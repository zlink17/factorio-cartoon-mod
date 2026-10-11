"""Passe pixel commune : toute image du mod (Pillow ou rendu Blender) y passe avant d'être cadrée.

Entrée : image RGBA à la résolution d'art (1 px = 1 px d'art). Étapes :
  1. alpha à 0 ou 255 (pas d'anticrénelage) ;
  2. chaque couleur ramenée à la plus proche de la palette, ou de la rampe de sa matière si on la connaît
     (carte d'identifiants de matière, rendue par Blender) ;
  3. contour coloré : le bord de la silhouette prend le ton le plus sombre de sa propre rampe ;
     en option, les jonctions entre matières prennent le ton d'ombre ;
  4. nettoyage : un pixel isolé (ses 4 voisins ont tous une même autre couleur) prend cette couleur, sauf s'il est
     protégé (reflet voulu).
"""
import numpy as np

from . import palette as P

ALPHA_CUT = 128


def to_array(img):
    a = np.asarray(img.convert("RGBA") if hasattr(img, "convert") else img).copy()
    return a.astype(np.uint8)


def binarize_alpha(a, cut=ALPHA_CUT):
    a = a.copy()
    opaque = a[..., 3] >= cut
    a[..., 3] = np.where(opaque, 255, 0)
    a[~opaque, :3] = 0
    return a


def quantize(a, materials=None):
    """Couleurs ramenées à la palette. `materials` : tableau (h, w) de noms de matière ("" si inconnue) :
    la couleur est alors cherchée dans la rampe de cette matière seulement."""
    a = a.copy()
    opaque = a[..., 3] > 0
    idx = P.index_of(a[..., :3])
    a[..., :3] = P.COLORS[idx]
    if materials is not None:
        for name in {m for m in np.unique(materials) if m}:
            sel = (materials == name) & opaque
            r = np.array(P.RAMPS[name], dtype=np.int32)
            px = a[sel, :3].astype(np.int32)
            # rang par luminance : on garde la valeur, la teinte vient de la rampe
            lum = px @ np.array([299, 587, 114]) / 1000
            rl = r @ np.array([299, 587, 114]) / 1000
            a[sel, :3] = r[np.abs(lum[:, None] - rl[None, :]).argmin(1)]
    a[~opaque, :3] = 0
    return a


def _neighbors(mask):
    """Pour chaque pixel : (haut, bas, gauche, droite) du masque, faux hors de l'image."""
    p = np.pad(mask, 1, constant_values=False)
    return p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]


def _ramp_rank(a):
    """(rampe, rang) de chaque pixel, d'après sa couleur de palette."""
    idx = P.index_of(a[..., :3])
    names = np.array([P.OWNER[i][0] for i in range(len(P.OWNER))], dtype=object)[idx]
    ranks = np.array([P.OWNER[i][1] for i in range(len(P.OWNER))])[idx]
    return names, ranks


def outline(a, materials=None, junctions=False):
    """Contour coloré de la silhouette (ton 0 de la rampe du pixel) ; jonctions entre matières en ton 1."""
    a = a.copy()
    opaque = a[..., 3] > 0
    names, _ = _ramp_rank(a)
    if materials is not None:
        names = np.where(materials.astype(bool), materials, names)
    edge = opaque & ~np.logical_and.reduce(_neighbors(opaque))
    for name in {n for n in np.unique(names[edge])}:
        sel = edge & (names == name)
        a[sel, :3] = P.RAMPS[name][0]
    if junctions:
        p = np.pad(names, 1, constant_values="")
        below, right = p[2:, 1:-1], p[1:-1, 2:]
        junction = opaque & ~edge & (((below != names) & (below != "")) | ((right != names) & (right != "")))
        for name in {n for n in np.unique(names[junction])}:
            sel = junction & (names == name)
            a[sel, :3] = P.RAMPS[name][1]
    return a


def cleanup(a, keep=None):
    """Pixels isolés remplacés par la couleur commune de leurs 4 voisins (si elle existe)."""
    a = a.copy()
    h, w = a.shape[:2]
    key = (a[..., 0].astype(np.int64) << 24) | (a[..., 1].astype(np.int64) << 16) | (a[..., 2].astype(np.int64) << 8) \
        | a[..., 3]
    p = np.pad(key, 1, constant_values=-1)
    up, down, left, right = p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]
    lonely = (up == down) & (up == left) & (up == right) & (up != key) & (up >= 0) & (a[..., 3] > 0)
    if keep is not None:
        lonely &= ~keep
    ys, xs = np.nonzero(lonely)
    for y, x in zip(ys, xs):
        k = int(up[y, x])
        a[y, x] = [(k >> 24) & 255, (k >> 16) & 255, (k >> 8) & 255, k & 255]
    return a


def passe(img, materials=None, junctions=False, keep=None, outline_on=True):
    """Passe complète ; renvoie un tableau RGBA uint8 à la résolution d'art."""
    a = binarize_alpha(to_array(img))
    a = quantize(a, materials)
    a = cleanup(a, keep)
    if outline_on:
        a = outline(a, materials, junctions)
    return a


def shadow(a, alpha=110):
    """Ombre au sol en aplat : silhouette noire d'alpha unique (le jeu la dessine en noir semi-transparent)."""
    a = to_array(a)
    out = np.zeros_like(a)
    out[..., 3] = np.where(a[..., 3] >= ALPHA_CUT, alpha, 0)
    return out
