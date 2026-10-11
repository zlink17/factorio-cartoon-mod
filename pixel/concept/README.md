# Images cibles du mod pixel

Méthode commune aux mods : [docs/methode-images-cibles.md](../../docs/methode-images-cibles.md) ; outils :
[`tools/concept/`](../../tools/concept/). Place dans le plan du mod : [docs/pixel/plan.md](../../docs/pixel/plan.md).

Ce dossier contient la recette du mod (`recette.json`) et les images retenues (`cibles/`). Guides et variantes
restent dans `.cache/concept/pixel/<objet>/` (non versionné).

## Recette (11 octobre, provisoire : à caler sur l'assembleur 1)

DreamShaper XL Turbo + **LoRA Pixel Art XL** (`pixel-art-xl.safetensors`, décision de Bastien : des modèles dédiés au
pixel art), guidés par la profondeur et les contours de l'original. Pas encore de référence de style par
IP-Adapter : le mod repart de zéro, nos premières cibles retenues pourront en servir. Pour les icônes, le LoRA
Illustrious `PixelArt_Icon_IL_M_V2.1_00002.safetensors.safetensors` (mot-clé `pixelarticon`) avec
`--ckpt Illustrious-XL-v0.1.safetensors`.

Les planches se font avec **`--pixel`** : sous chaque variante, sa version à 16 px d'art par case (la densité du
jeu), pour juger ce qui survivra.

```bash
G=.cache/concept/pixel/assembleur-1
~/workspace/comfyui/.venv/bin/python -I tools/concept/prepare.py $G/guides \
    base/graphics/entity/assembling-machine-1/assembling-machine-1.png 214 226 --shift 0 0.0625
.venv/bin/python -I tools/concept/concept.py $G/guides $G/gen 11,12,13,14 --tag a --recette pixel/concept/recette.json \
    --prompt "Assembling machine: grey-green painted steel body, copper top plate, big brass gears, an electric motor block."
.venv/bin/python -I tools/concept/planche.py $G/guides $G/planche-a.png $G/gen/a-*.png --pixel --sol herbe
```
