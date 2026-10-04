#!/usr/bin/env python3
"""Régénère manifest.lua à partir du contenu de graphics/.

graphics/generated/<mod>/...  -> sprites produits par le filtre (approche simple, non versionnés)
graphics/overrides/<mod>/...  -> sprites refaits à la main ou par IA (approche complexe, versionnés)

Si un même sprite existe aux deux endroits, `overrides` a la priorité.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GFX = ROOT / "graphics"
# Ordre croissant de priorité : le dernier écrase le précédent.
SOURCES = ["generated", "overrides"]


def build_manifest():
    entries = {}
    for source in SOURCES:
        base = GFX / source
        if not base.exists():
            continue
        for png in sorted(base.rglob("*.png")):
            rel = png.relative_to(base).as_posix()  # <mod>/chemin/sprite.png
            mod, _, rest = rel.partition("/")
            if not rest:
                continue
            entries[f"__{mod}__/graphics/{rest}"] = source

    lines = ["-- Fichier généré par tools/build_manifest.py (ne pas éditer à la main).",
             "return {"]
    lines += [f'  ["{k}"] = "{v}",' for k, v in sorted(entries.items())]
    lines.append("}")
    (ROOT / "manifest.lua").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


if __name__ == "__main__":
    entries = build_manifest()
    generated = sum(1 for v in entries.values() if v == "generated")
    overrides = sum(1 for v in entries.values() if v == "overrides")
    print(f"manifest.lua : {generated} sprites filtrés, {overrides} sprites refaits.")
