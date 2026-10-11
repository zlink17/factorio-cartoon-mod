"""Contrôle propre au mod pixel (appelé par tools/check_mod.py, donc aussi par tools/build.py pixel).

Pour chaque image du mod, selon son rôle dans le jeu (tools/inventory.py) :
  - sprite, masque, lumière, ombre : pixels d'art nets, c'est-à-dire blocs de FACTEUR x FACTEUR px uniformes
    (FACTEUR = 2 / scale), placés sur la grille du monde calculée depuis le `shift` du prototype ;
  - icône : blocs de 2 x 2 px au niveau 64 px ;
  - sprite et icône : alpha 0 ou 255, couleurs de la palette (pixlib/palette.py) ;
  - ombre : une seule valeur d'alpha (aplat) ;
  - technique : rien (tables, bruits, cartes d'effets).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pixlib import cadre, palette  # noqa: E402


def _blocks_ok(a, k, ox, oy):
    """Vrai si tous les blocs k x k (grille décalée de ox, oy) de `a` sont uniformes ; les blocs coupés par le bord
    du cadre comptent aussi."""
    h, w = a.shape[:2]
    by = np.maximum(((np.arange(h) - oy) // k) * k + oy, 0)     # premier px du bloc de chaque ligne
    bx = np.maximum(((np.arange(w) - ox) // k) * k + ox, 0)
    return bool((a == a[by][:, bx]).all())


def _cells(info, shape):
    """Cellules (x, y, w, h) de l'image d'après le découpage du prototype ; None s'il ne pave pas l'image."""
    f = info.framing or {}
    size = f.get("size")
    w = f.get("width") or (size if isinstance(size, int) else (size or [None])[0])
    h = f.get("height") or (size if isinstance(size, int) else (size or [None, None])[1])
    x0, y0 = f.get("x", 0), f.get("y", 0)
    H, W = shape[:2]
    if not w or not h or x0 or y0 or W % w or H % h:
        return None
    return [(x, y, w, h) for y in range(0, H, h) for x in range(0, W, w)]


def _shift(info):
    s = (info.framing or {}).get("shift") or (0, 0)
    return (s["x"], s["y"]) if isinstance(s, dict) else (s[0], s[1])


def check_image(png, info):
    """Liste des problèmes d'une image ; `info` : tools.inventory.Image (rôle, découpage) ou None."""
    role = info.role if info else "sprite"
    if role == "technique":
        return []
    a = np.asarray(Image.open(png).convert("RGBA"))
    errors = []
    alpha = a[..., 3]
    if role == "ombre":
        values = set(np.unique(alpha)) - {0}
        if len(values) > 1:
            errors.append(f"OMBRE PAS EN APLAT ({len(values)} valeurs d'alpha)")
    elif not set(np.unique(alpha)) <= {0, 255}:
        errors.append("ALPHA PARTIEL (anticrénelage)")
    if role in ("sprite", "icone"):
        opaque = alpha > 0
        if not palette.contains(a[..., :3])[opaque].all():
            errors.append(f"HORS PALETTE ({int((~palette.contains(a[..., :3]) & opaque).sum())} px)")
    if role == "icone":
        n = min(64, a.shape[0])
        if not _blocks_ok(a[:n, :n], 2, 0, 0):
            errors.append("ICÔNE : pixels d'art pas nets (blocs 2 x 2)")
        return errors
    scale = (info.framing or {}).get("scale", 0.5) if info else 0.5
    k = cadre.factor(scale)
    cells = _cells(info, a.shape) if info else None
    if cells:
        bad = 0
        for x, y, w, h in cells:
            ox, oy = cadre.grid_offset((w, h), _shift(info), scale)
            bad += not _blocks_ok(a[y:y + h, x:x + w], k, ox, oy)
        if bad:
            errors.append(f"PIXELS PAS NETS ou hors de la grille du monde : {bad} images sur {len(cells)}")
    elif not any(_blocks_ok(a, k, ox, oy) for ox in range(k) for oy in range(k)):
        errors.append(f"PIXELS PAS NETS (blocs {k} x {k})")
    return errors


def check(files, overrides):
    """Appelé par tools/check_mod.py : problèmes de toutes les images du mod."""
    tools = Path(__file__).resolve().parent.parent / "tools"
    sys.path.insert(0, str(tools))
    import inventory
    images, _ = inventory.load("pixel")
    by_rel = {i.rel: i for i in images.values()}
    errors = []
    for png in files:
        rel = png.relative_to(overrides).as_posix()
        errors += [f"{e} : {rel}" for e in check_image(png, by_rel.get(rel))]
    return errors
