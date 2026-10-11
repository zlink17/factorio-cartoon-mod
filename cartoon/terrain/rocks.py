"""Gros rochers de Nauvis (entités `simple-entity`) en blocs à facettes, et poissons.

Usage : python cartoon/terrain/rocks.py <dossier_sortie> [famille[,famille...]|toutes]
        famille = big-rock, huge-rock, big-sand-rock, fish

Comme les buissons et les arbres, on lit l'image d'origine pour savoir *où* dessiner :
- silhouette : le corps de l'original (alpha > 200 : son ombre intégrée est moins opaque), en pans droits ;
- blocs : des prismes posés sur la silhouette, de l'arrière vers l'avant (colonnes hexagonales hautes pour les
  rochers bruns, comme les colonnes de l'original ; gros blocs à 8 pans, bas, pour le grès du désert) ; dessus
  clair, faces gauche et avant moyennes, face droite sombre ; trait fin entre les blocs, contour noir chaud sur
  la silhouette ; leur sommet ne dépasse pas le haut de la silhouette d'origine ;
- ombre : celle de l'original, en aplat noir semi-transparent.
Essayés et écartés : facettes de Voronoï ou zones de lumière de l'original tirées en trois tons (taches de
camouflage, aucun volume de rocher).
Poissons : l'original est une ombre floue sous l'eau ; on y met une silhouette de poisson nette, même teinte et
même opacité, sans contour.
Les fichiers gardent la taille et le cadrage de l'original. Écrit base/decorative/<dossier>/ et base/entity/fish/.
"""
import os
import sys
import zlib

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from decoratives import FACTORIO_DATA, OUTLINE_BGR, OUTLINE_PX, SHADOW_ALPHA, SS, Rng, hx  # noqa: E402

ROCK = ("#3e2e23", "#6c513d", "#a07e5d")            # gros rochers : brun-roux de l'original, éclairci
SAND = ("#4d4430", "#7a6b44", "#a6955f")            # grès du désert

# famille : (dossier, tons, demi-largeur d'un bloc en part de la taille du rocher, hauteur des blocs, pans)
FAMILIES = {
    "big-rock": ("big-rock", ROCK, 0.16, 1.8, 6),
    "huge-rock": ("huge-rock", ROCK, 0.14, 2.2, 6),
    "big-sand-rock": ("sand-rock", SAND, 0.3, 1.0, 8),
}
LINE_PX = 0.55                                      # trait entre les blocs (px du fichier)


def silhouette(orig):
    """Masque du rocher (sans ombre), trous bouchés, à SS fois la taille, bord en pans droits."""
    body = (orig[:, :, 3] > 200).astype(np.uint8)
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


def blocks(m, size, height, sides, rng):
    """Blocs prismatiques posés sur la silhouette `m`, de l'arrière vers l'avant. Renvoie (ton, trait) : ton par
    pixel (-1 hors des blocs, 0 sombre, 1 moyen, 2 clair) et masque du trait qui entoure chaque bloc."""
    h, w = m.shape
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    r = max(x1 - x0, y1 - y0) * size
    top_of = np.full(w, h, np.int32)                     # haut de la silhouette, par colonne
    any_col = m.any(0)
    top_of[any_col] = m[:, any_col].argmax(0)
    tone = np.full((h, w), -1, np.int32)
    line = np.zeros((h, w), np.uint8)
    lw = max(1, int(round(LINE_PX * SS)))
    step = r * 1.15
    bases = []                                           # pieds des blocs : quinconce dans la silhouette
    y, row = y0 + r * 0.6, 0
    while y < y1:
        x = x0 + (step / 2 if row % 2 else 0) + rng.u(-0.2, 0.2) * step
        while x < x1:
            cx, cy = x + rng.u(-0.2, 0.2) * step, y + rng.u(-0.15, 0.15) * step
            if 0 <= int(cy) < h and 0 <= int(cx) < w and m[int(cy), int(cx)]:
                bases.append((cx, cy))
            x += step
        y += step * 0.5
        row += 1
    for cx, cy in sorted(bases, key=lambda b: b[1]):
        rx = r * rng.u(0.7, 1.3)
        ry = rx * 0.5
        ytop = max(cy - r * height * rng.u(0.5, 1.6), top_of[int(np.clip(cx, 0, w - 1))] + ry)
        ytop = min(ytop, cy - ry * 0.3)
        ang = np.arange(sides) * 2 * np.pi / sides + rng.u(-0.25, 0.25)
        k = np.array([rng.u(0.85, 1.1) for _ in ang])
        top = np.stack([cx + np.cos(ang) * rx * k, ytop + np.sin(ang) * ry * k], 1)
        d = np.array([0, cy + ry - ytop])
        faces = []
        for i in range(sides):                           # faces latérales tournées vers l'avant
            a, b = top[i], top[(i + 1) % sides]
            mid = ang[i] + np.pi / sides
            if np.sin(mid) > 0:
                faces.append((np.array([b, a, a + d, b + d]), 0 if np.cos(mid) > 0.35 else 1))
        faces.append((top, 2))
        full = np.zeros((h, w), np.uint8)
        for poly, _ in faces:
            cv2.fillPoly(full, [np.round(poly).astype(np.int32)], 1)
        line[full > 0] = 0                               # le bloc cache les traits de ceux de derrière
        tone[full > 0] = 1
        for poly, t in faces:
            mk = np.zeros((h, w), np.uint8)
            cv2.fillPoly(mk, [np.round(poly).astype(np.int32)], 1)
            tone[mk > 0] = t
        cs, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(line, cs, -1, 1, lw)
    return tone, line


def render(orig, tones, size, height, sides, seed):
    h, w = orig.shape[:2]
    sil = silhouette(orig)
    if sil.sum() == 0:
        return np.zeros_like(orig)
    tone, line = blocks(sil, size, height, sides, Rng(seed))
    inside = (tone >= 0) & (cv2.dilate(sil, np.ones((2 * SS + 1, 2 * SS + 1), np.uint8)) > 0)
    cols = [hx(t) for t in tones]
    color = np.zeros((h * SS, w * SS, 3), np.float32)
    for t in range(3):
        color[tone == t] = cols[t]
    color[(line > 0) & inside] = np.array(cols[0]) * 0.55
    thick = max(1, int(round(OUTLINE_PX * SS)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * thick + 1, 2 * thick + 1))
    out = (cv2.dilate(inside.astype(np.uint8), disk) > 0) & ~inside
    color[out] = OUTLINE_BGR
    alpha = (inside | out).astype(np.float32)
    a0 = cv2.resize(orig[:, :, 3], (w * SS, h * SS), interpolation=cv2.INTER_LINEAR)
    sh = (cv2.GaussianBlur((a0 > 40).astype(np.float32), (0, 0), SS) > 0.5) & (alpha == 0)
    rgba = np.zeros((h * SS, w * SS, 4), np.float32)
    rgba[..., :3] = color * alpha[..., None]
    rgba[..., 3] = alpha * 255
    rgba[sh, 3] = SHADOW_ALPHA * 255
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    a = np.clip(small[..., 3:4] / 255.0, 1e-6, 1)
    return np.dstack([np.clip(small[..., :3] / a, 0, 255), small[..., 3:4]]).astype(np.uint8)


def render_fish(orig):
    """Silhouette nette (corps en fuseau, queue en V, tête vers le haut) à la place de la tache floue."""
    h, w = orig.shape[:2]
    a = orig[:, :, 3].astype(np.float32)
    ys, xs = np.nonzero(a > a.max() * 0.35)
    cx, cy = xs.mean() * SS + SS / 2, ys.mean() * SS + SS / 2
    bl = (ys.max() - ys.min() + 1) * SS * 1.25                     # longueur du poisson
    bw = (xs.max() - xs.min() + 1) * SS * 0.75
    top = cy - bl * 0.55
    t = np.linspace(0, np.pi, 24)
    half = np.stack([cx + np.sin(t) * bw / 2, top + (1 - np.cos(t)) / 2 * bl * 0.8], 1)
    body = np.concatenate([half, (half * [-1, 1] + [2 * cx, 0])[::-1]])
    ty = top + bl * 0.75
    tail = np.array([[cx, ty - bl * 0.05], [cx + bw * 0.6, ty + bl * 0.32], [cx, ty + bl * 0.2],
                     [cx - bw * 0.6, ty + bl * 0.32]])
    m = np.zeros((h * SS, w * SS), np.uint8)
    cv2.fillPoly(m, [np.round(body).astype(np.int32), np.round(tail).astype(np.int32)], 1)
    rgba = np.zeros((h * SS, w * SS, 4), np.float32)
    rgba[m > 0, :3] = orig[:, :, :3][a > 0].mean(0)
    rgba[m > 0, 3] = a.max()
    small = cv2.resize(rgba, (w, h), interpolation=cv2.INTER_AREA)
    cover = np.clip(small[..., 3:4] / a.max(), 1e-6, 1)          # part du pixel couverte par le poisson
    return np.dstack([np.clip(small[..., :3] / cover, 0, 255), small[..., 3:4]]).astype(np.uint8)


def write(out, rel, im):
    path = os.path.join(out, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, im)


def build(family, out):
    if family == "fish":
        for f in ("fish-1.png", "fish-2.png"):
            orig = cv2.imread(os.path.join(FACTORIO_DATA, "base/graphics/entity/fish", f), cv2.IMREAD_UNCHANGED)
            write(out, os.path.join("base/entity/fish", f), render_fish(orig))
        return
    folder, tones, size, height, sides = FAMILIES[family]
    d = os.path.join(FACTORIO_DATA, "base/graphics/decorative", folder)
    for f in sorted(f for f in os.listdir(d) if f.endswith(".png") and f.startswith(family)):
        orig = cv2.imread(os.path.join(d, f), cv2.IMREAD_UNCHANGED)
        write(out, os.path.join("base/decorative", folder, f),
              render(orig, tones, size, height, sides, zlib.crc32(f.encode())))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "rocks_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "toutes"
    for fam in ([*FAMILIES, "fish"] if which == "toutes" else which.split(",")):
        build(fam, out)
        print("OK", fam, flush=True)
