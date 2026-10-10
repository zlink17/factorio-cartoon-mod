#!/usr/bin/env python3
"""Régénère manifest.lua d'un mod à partir du contenu de <mod>/mod/graphics/overrides/.

Usage : python tools/build_manifest.py [cartoon|pixel]     (défaut : cartoon)

graphics/overrides/<mod>/...  -> sprites refaits (Blender, IA ou dessin), même chemin que l'original.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_manifest(mod="cartoon"):
    mod_dir = ROOT / mod / "mod"
    overrides = mod_dir / "graphics" / "overrides"
    entries = []
    if overrides.exists():
        for png in sorted(overrides.rglob("*.png")):
            rel = png.relative_to(overrides).as_posix()  # <jeu>/chemin/sprite.png
            game_mod, _, rest = rel.partition("/")
            if rest:
                entries.append(f"__{game_mod}__/graphics/{rest}")

    lines = ["-- Fichier généré par tools/build_manifest.py (ne pas éditer à la main).",
             "return {"]
    lines += [f'  ["{k}"] = true,' for k in entries]
    lines.append("}")
    (mod_dir / "manifest.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "cartoon"
    entries = build_manifest(mod)
    print(f"{mod}/mod/manifest.lua : {len(entries)} sprites remplacés.")
