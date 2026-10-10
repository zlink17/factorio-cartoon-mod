"""Minerais (fer, cuivre, charbon, pierre, uranium) : gisements et icônes d'objets.

Usage : python cartoon/blender/ore.py <dossier_sortie> [minerai|tous]

Pour chaque minerai, écrit :
  <nom>-entity.png   planche 1024 x 1024 des gisements : 8 x 8 cellules de 128 px (2 cases). Une rangée = une étape de
                     richesse (rangée 0 = le plus gros tas, rangée 7 = quelques cailloux), une colonne = une variante.
  <nom>-glow.png     (uranium seulement) calque lumineux, même disposition
  <nom>.png, <nom>-1.png, -2, -3  les quatre icônes de l'objet (tas d'importance croissante), 64 px + mipmaps (120 x 64) ;
                     ce sont aussi les objets posés sur les convoyeurs.
Un tas est un amas de blocs taillés à facettes (trois tons), au sol avec une ombre à plat.
"""
import math, os, sys
import bpy
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style as S
from lib import flatten_to_shadow, mat, mip_strip, render_icon, render_scene, reset

P = S.PALETTE
CELL = 128
PX_PER_TILE = 64
OUTLINE = 0.012
SHADOW = (0.4, 0.02, 0.35)

ORES = {                                   # nom : (couleur, couleur du dessus plus claire pour les éclats)
    "iron-ore": "ore_iron",
    "copper-ore": "ore_copper",
    "coal": "ore_coal",
    "stone": "ore_stone",
    "uranium-ore": "ore_uranium",
}
GAME = {"iron-ore": "base", "copper-ore": "base", "coal": "base", "stone": "base", "uranium-ore": "base"}

# par étape : nombre de blocs, rayon min et max d'un bloc (en cases)
STAGES = [(16, 0.15, 0.23), (14, 0.14, 0.21), (12, 0.14, 0.2), (10, 0.13, 0.19), (8, 0.12, 0.18),
          (6, 0.12, 0.17), (3, 0.11, 0.15), (2, 0.1, 0.14)]


class Rng:
    """Petit générateur déterministe (le même résultat à chaque export)."""
    def __init__(self, seed):
        self.s = (seed * 2654435761 + 12345) & 0xFFFFFFFF

    def u(self, a=0.0, b=1.0):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return a + (b - a) * (self.s >> 8) / float(1 << 24)


def chunk(x, y, r, m, rng, lift=0.0):
    """Bloc taillé : sphère à facettes aplatie, orientée au hasard, posée au sol (ou sur d'autres blocs : `lift`)."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=(x, y, r * 0.5 + lift))
    o = bpy.context.object
    o.scale = (rng.u(0.9, 1.25), rng.u(0.8, 1.1), rng.u(0.55, 0.8))
    o.rotation_euler = (rng.u(-0.3, 0.3), rng.u(-0.3, 0.3), rng.u(0, math.tau))
    for v in o.data.vertices:
        k = rng.u(0.86, 1.14)
        v.co.x, v.co.y, v.co.z = v.co.x * k, v.co.y * k, v.co.z * rng.u(0.9, 1.1)
    o.data.materials.append(m)
    return o


def build_pile(name, count, lo, hi, seed, spread=None):
    reset()
    m = mat("ore", P[ORES[name]])
    rng = Rng(seed)
    spread = spread or min(0.62, 0.14 + 0.03 * count)
    spots = []
    tries = 0
    while len(spots) < count and tries < 600:
        tries += 1
        a, d = rng.u(0, math.tau), spread * math.sqrt(rng.u())
        x, y, r = d * math.cos(a), d * math.sin(a) * 0.85, rng.u(lo, hi)
        if all(math.hypot(x - sx, (y - sy) * 1.15) > (r + sr) * 0.62 for sx, sy, sr in spots):
            spots.append((x, y, r))
    for x, y, r in sorted(spots, key=lambda s: -s[1]):          # de l'arrière vers l'avant
        lift = max(0.0, 1.0 - math.hypot(x, y) / spread) * r * 1.1      # le centre du tas est plus haut
        chunk(x, y, r, m, rng, lift)


def over(top, bottom):
    ta, ba = top[:, :, 3:4] / 255.0, bottom[:, :, 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[:, :, :3] * ta + bottom[:, :, :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.dstack([np.clip(rgb, 0, 255), np.clip(oa * 255, 0, 255)]).astype(np.uint8)


def render_cell(name, stage, variation, out):
    path = os.path.join(out, "_ore.png")
    count, lo, hi = STAGES[stage]
    seed = stage * 8 + variation + 100 * list(ORES).index(name)
    scale = CELL / PX_PER_TILE
    build_pile(name, count, lo, hi, seed)
    render_scene(path, size=CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline_units=OUTLINE)
    sprite = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    build_pile(name, count, lo, hi, seed)
    flatten_to_shadow(SHADOW[0], SHADOW[1])
    render_scene(path, size=CELL, scale=scale, pitch_deg=S.PITCH_BUILDING_DEG, outline=False)
    shadow = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    os.remove(path)
    shadow[:, :, :3] = 0
    shadow[:, :, 3] = (shadow[:, :, 3].astype(np.float32) * SHADOW[2]).astype(np.uint8)
    return over(sprite, shadow)


def build_icons(name, out):
    # quatre icônes : tas de plus en plus gros
    for k, count in enumerate((3, 5, 7, 10)):
        suffix = "" if k == 0 else f"-{k}"
        icon = render_icon(lambda: build_pile(name, count, 0.15, 0.22, 7 + k, spread=0.3 + 0.04 * k),
                           os.path.join(out, "_icon.png"), 64, 58, outline_px=0.45)
        cv2.imwrite(os.path.join(out, f"{name}{suffix}.png"), mip_strip(icon, 64))


def build_ore(name, out):
    sheet = np.zeros((8 * CELL, 8 * CELL, 4), np.uint8)
    for stage in range(8):
        for var in range(8):
            sheet[stage * CELL:(stage + 1) * CELL, var * CELL:(var + 1) * CELL] = render_cell(name, stage, var, out)
    cv2.imwrite(os.path.join(out, f"{name}-entity.png"), sheet)
    if name == "uranium-ore":                                       # calque lumineux : les blocs, éclaircis
        glow = sheet.copy()
        glow[:, :, :3] = (200, 255, 160)
        glow[:, :, 3] = (sheet[:, :, 3].astype(np.float32) * 0.55).astype(np.uint8)
        cv2.imwrite(os.path.join(out, f"{name}-glow.png"), glow)
    build_icons(name, out)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ore_out"
    which = sys.argv[2] if len(sys.argv) > 2 else "tous"
    os.makedirs(out, exist_ok=True)
    for name in (ORES if which == "tous" else [which]):
        build_ore(name, out)
        print("OK", name, flush=True)
