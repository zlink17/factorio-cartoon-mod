# Mods de textures pour Factorio 2.0

Ce repo contient plusieurs mods qui remplacent les textures du jeu, chacun dans son style.
Chaque mod a son dossier, avec **le mod installable** (`mod/`) et **les outils qui fabriquent ses sprites**.

| Mod | Style | Dossier | Techniques | État |
|---|---|---|---|---|
| **Cartoon** | aplats, gros contours | [`cartoon/`](cartoon/) | rendus Blender ; IA (ComfyUI), mise de côté | assembleurs, convoyeurs, bras |
| **Pixel** | pixel art | [`pixel/`](pixel/) | dessin en code avec Pillow | assembleurs, convoyeurs, bras, minerais |

```
cartoon/                  mod cartoon
  mod/                    le mod : info.json, Lua, manifest.lua, graphics/overrides/  (à copier dans Factorio)
  blender/                rendus 3D toon (technique principale)
  ai/                     génération par IA avec ComfyUI (essai, non retenu pour les machines)
  STYLE.md                guide de style : référence pour tout sprite cartoon
pixel/                    mod pixel
  mod/                    le mod
  pillow/                 sprites dessinés en code (Pillow) + palette
tools/                    outils communs aux mods
  build_manifest.py       génère <mod>/mod/manifest.lua
  install_mod.sh          copie un mod dans le dossier mods de Factorio
docs/                     notes de session (historique)
```

## Principe commun

1. Les générateurs écrivent des PNG dans `<mod>/mod/graphics/overrides/<jeu>/...`, au **même chemin que l'original**
   (par exemple `base/entity/assembling-machine-1/assembling-machine-1.png`).
2. `tools/build_manifest.py <mod>` liste ces fichiers dans `<mod>/mod/manifest.lua`.
3. `data-final-fixes.lua` remplace, dans tous les prototypes, les chemins `__base__/graphics/...` listés dans le manifeste.
   Les textures non refaites restent celles du jeu.

Les sprites originaux de Factorio ne sont pas dans le repo (ils sont dans le dossier d'installation du jeu).

## Commandes

```bash
# environnement Python (un seul .venv à la racine ; bpy demande Python 3.11)
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r cartoon/blender/requirements.txt -r pixel/pillow/requirements.txt

# installer un mod dans Factorio (régénère le manifeste puis copie le mod)
tools/install_mod.sh cartoon
tools/install_mod.sh pixel
```

Chaque mod a son propre README avec ses commandes de génération : [cartoon](cartoon/README.md), [pixel](pixel/README.md).

> Les deux mods remplacent les mêmes textures : n'en activer qu'un à la fois dans Factorio.
