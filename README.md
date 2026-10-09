# factorio-cartoon-mod

Mod Factorio (2.0) qui remplace les textures du jeu par une version au style cartoon, avec deux approches qui cohabitent dans le même mod.

> **Style** : toutes les règles visuelles (projection, contours, palette, ombrage) sont dans [STYLE.md](STYLE.md). À respecter pour tout sprite.

## Les deux approches

| | Simple | Complexe |
|---|---|---|
| Principe | Filtre automatique (lissage, couleurs réduites, contours) | Sprites refaits par IA (Gemini) ou à la main |
| Outils | `tools/simple/cartoonize.py` | `tools/complex/` |
| Sortie | `graphics/generated/` (non versionné) | `graphics/overrides/` (versionné) |
| Qualité | Correcte, inégale | Meilleure, plus cohérente |
| Couverture | Tous les sprites | Les assets les plus visibles, progressivement |

**Priorité** : si un sprite existe dans les deux dossiers, `overrides` l'emporte sur `generated`. Le mod utilise donc le filtre partout, et les versions refaites là où elles existent.

## Fonctionnement

1. Les outils écrivent les images dans `graphics/generated/` ou `graphics/overrides/`.
2. `tools/build_manifest.py` génère `manifest.lua`, la liste des textures remplacées et leur source.
3. `data-final-fixes.lua` remplace, dans tous les prototypes, les chemins `__base__/graphics/...` par la version cartoon.

## Utilisation

```bash
pip install -r tools/requirements.txt

# Approche simple : test sur 20 sprites, puis conversion complète
python tools/simple/cartoonize.py --data "<dossier Factorio>/data" --limit 20
python tools/simple/cartoonize.py --data "<dossier Factorio>/data" --mods base space-age

# Approche complexe : voir tools/complex/README.md

# Rendus Blender (pip install bpy) : sprite de référence et animation de l'assembleur
python tools/blender/assembler.py sortie/
python tools/blender/animate.py sortie/     # planche de 32 images + aperçu GIF

# Régénérer le manifeste à la main si besoin
python tools/build_manifest.py
```

Copier ou lier ce dossier dans `mods/` de Factorio (renommé `factorio-cartoon-mod_0.0.1`).

## À faire

- [x] Récupérer les sprites de l'installation Factorio (assembleur 1 pour l'instant)
- [ ] Tester le filtre simple et ajuster le rendu
- [ ] Définir le style de référence pour l'approche complexe
- [x] Assembleur 1 : planche d'animation de 32 images (`tools/blender/animate.py`), installée dans `graphics/overrides/`
- [ ] Tester le mod dans Factorio (jamais lancé pour l'instant)
- [ ] Ombre de l'assembleur 1 et icône
- [ ] Refaire les autres assets les plus visibles (assembleurs 2 et 3, convoyeurs, fours, personnage)
- [ ] Gérer les icônes et l'interface (GUI)

Les sprites originaux de Factorio ne sont pas inclus dans le repo.
