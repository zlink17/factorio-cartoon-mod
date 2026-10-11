#!/usr/bin/env python3
"""Régénère feet.lua d'un mod : le pied de chaque décoration refaite (graphics/overrides/<jeu>/decorative/).

Usage : python tools/decorative_feet.py [cartoon]     (défaut : cartoon ; aussi lancé par tools/build.py)

Le pied est la dernière ligne opaque du dessin (l'ombre portée, semi-transparente, ne compte pas), en px du fichier
comptés depuis le centre de l'image. data-final-fixes.lua décale chaque image pour poser ce pied sur la position de la
décoration : le jeu, qui trie la couche « object » par position, fait alors passer devant ce qui est plus bas à l'écran.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OPAQUE = 200             # alpha minimal du dessin ; l'ombre portée est à ~107


def build_feet(mod="cartoon"):
    mod_dir = ROOT / mod / "mod"
    overrides = mod_dir / "graphics" / "overrides"
    feet = {}
    for png in sorted(overrides.glob("*/decorative/**/*.png")):
        alpha = np.asarray(Image.open(png).convert("RGBA"))[..., 3]
        rows = np.nonzero((alpha >= OPAQUE).any(1))[0]
        if len(rows):
            game_mod, _, rest = png.relative_to(overrides).as_posix().partition("/")
            feet[f"__{game_mod}__/graphics/{rest}"] = float(rows.max() + 1 - alpha.shape[0] / 2)
    lines = ["-- Fichier généré par tools/decorative_feet.py (ne pas éditer à la main).",
             "-- Pied de chaque décoration refaite, en px du fichier sous le centre de l'image.",
             "return {"]
    lines += [f'  ["{k}"] = {v:g},' for k, v in feet.items()]
    lines.append("}")
    (mod_dir / "feet.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return feet


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "cartoon"
    print(f"{mod}/mod/feet.lua : {len(build_feet(mod))} décorations.")
