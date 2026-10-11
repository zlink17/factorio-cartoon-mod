# Images cibles du mod cel-shading

Méthode commune aux mods (étapes, rangement, installation, licences) : [docs/methode-images-cibles.md](../../docs/methode-images-cibles.md) ;
outils : [`tools/concept/`](../../tools/concept/). Place dans le plan du mod : [docs/celshading/plan.md](../../docs/celshading/plan.md), section 3.3.

Ce dossier contient la recette du mod (`recette.json`) et les images retenues (`cibles/`). Guides et variantes
restent dans `.cache/concept/<objet>/` (non versionné).

## Recette (11 octobre, assembleur 1 : image `e-11` jugée réussie par Bastien, cible provisoire)

Vérifiée avec `tools/concept/concept.py --recette` : variantes `e-13` à `e-16`, cohérentes avec `e-11`. Bastien a
retenu **e-11 et e-15** (`cibles/assembleur-1.png`, `cibles/assembleur-1-b.png`) : modèle `blender/assembler.py`.

DreamShaper XL Turbo (modèle par défaut), 768 x 768, 8 étapes, cfg 3,5, ControlNet profondeur 0,4 et contours
0,25, **IP-Adapter « style transfer » 0,6 sur trois de nos rendus cel-shading** (assembleurs 1 et 2, formes
d'essai : `style-0.png` à `style-2.png` dans le dossier des guides). C'est l'IP-Adapter qui fait sortir le modèle
du rendu photo : aplats nets, ombres franches. Le style (prompt et négatif) est dans `recette.json` ; la description
de l'objet se passe avec `--prompt`.

```bash
G=.cache/concept/assembleur-1
# 1. guides tirés du sprite original (environnement de ComfyUI, pour Depth Anything V2)
~/workspace/comfyui/.venv/bin/python -I tools/concept/prepare.py $G/guides \
    base/graphics/entity/assembling-machine-1/assembling-machine-1.png 214 226 --toile 1024 1024
# 2. références de style : nos rendus cel-shading (moteur du mod). Pour l'assembleur 1, c'étaient les modèles
#    cartoon rendus en cel-shading (assembleurs 1 et 2, retirés depuis) et les formes d'essai (blender/essai.py) ;
#    pour les objets suivants : les sprites déjà refaits du mod, par exemple
.venv/bin/python tools/concept/styles.py $G/guides \
    celshading/mod/graphics/overrides/base/entity/assembling-machine-1/assembling-machine-1.png:214:226 \
    .cache/celshading/essai/essai.png
# 3. génération, une image par graine
.venv/bin/python -I tools/concept/concept.py $G/guides $G/gen 11,12,13 --tag e --recette celshading/concept/recette.json \
    --prompt "Assembling machine: grey-green painted steel body, copper top plate, big brass gears, an electric motor block, four front panels."
```

## Essais écartés

| Essai | Résultat |
|---|---|
| DreamShaper seul, prompt « cel shading » | rendu 3D photo ; « blue-violet shadows » teint toute la machine en violet |
| DreamShaper seul, mots-clés pondérés | encore plus photo |
| Illustrious XL v0.1 seul (étiquettes, 28 étapes) | délavé, formes déstructurées |
| Illustrious XL v0.1 + LoRA Wind Waker (`w1ndw4k3r`, poids 1, 28 étapes, cfg 5, `g-31`, `g-32`) | vrai volume 3D façon Wind Waker (textures peintes), mais flou, terne, peu industriel ; ~3 min par image |
