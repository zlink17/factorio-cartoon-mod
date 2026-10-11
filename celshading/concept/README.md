# Images cibles (ComfyUI)

Méthode du mod (voir [docs/celshading/plan.md](../../docs/celshading/plan.md), section 3.3) : pour chaque objet,
des images cibles guidées par le sprite original ; Bastien choisit ; puis un modèle Blender s'en approche.
Les images restent dans `.cache/celshading/concept/<objet>/` (non versionné) ; l'image retenue est recopiée dans
`celshading/concept/cibles/`.

ComfyUI est installé hors du repo (`~/workspace/comfyui`) ; lancer le serveur s'il ne répond pas sur le port 8188 :

```bash
cd ~/workspace/comfyui && .venv/bin/python main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch
```

## Étapes

```bash
# 1. guides tirés du sprite original (environnement de ComfyUI, pour Depth Anything V2)
~/workspace/comfyui/.venv/bin/python -I celshading/concept/prepare.py .cache/celshading/concept/assembleur-1/guides \
    base/graphics/entity/assembling-machine-1/assembling-machine-1.png 214 226
# 2. références de style : nos rendus cel-shading (moteur du mod)
.venv/bin/python celshading/concept/styles.py .cache/celshading/concept/assembleur-1/guides \
    celshading/mod/graphics/overrides/base/entity/assembling-machine-1/assembling-machine-1.png:214:226 \
    celshading/mod/graphics/overrides/base/entity/assembling-machine-2/assembling-machine-2.png:214:226 \
    .cache/celshading/essai/essai.png
# 3. génération (recette retenue ci-dessous), une image par graine
.venv/bin/python -I celshading/concept/concept.py <guides> <sortie> 11,12,13 --tag e ...
```

## Recette retenue (11 octobre, assembleur 1 : image `e-11` jugée réussie par Bastien, cible provisoire)

DreamShaper XL Turbo (modèle par défaut), 768 x 768, 8 étapes, cfg 3,5, ControlNet profondeur 0,4 et contours
0,25, **IP-Adapter « style transfer » 0,6 sur trois de nos rendus cel-shading** (assembleurs 1 et 2, formes
d'essai). C'est l'IP-Adapter qui fait sortir le modèle du rendu photo : aplats nets, ombres franches.

Prompt :
> (cel shading:1.5), (toon shading:1.4), (flat colors:1.3), anime style video game art in the style of The Legend of
> Zelda The Wind Waker, hard-edged shadows, simple chunky rounded shapes, low detail. Top-down view from above of a
> steampunk industrial assembling machine, Metal Slug style chunky exaggerated machine: grey-green painted steel body,
> copper top plate, big brass gears, an electric motor block, four front panels, big rivets, thick pipes. Bright
> saturated sunny colors, thin dark outline, plain grey background

Négatif :
> (3d render:1.3), (realistic:1.4), photo, soft shading, ambient occlusion, detailed, intricate, many small parts,
> metallic reflections, specular, PBR, purple, violet, noise, grain, rust, dirt, scratches, gradient, blurry, text,
> watermark, perspective, 3/4 view, isometric, wood, medieval, characters, people

## Essais écartés

| Essai | Résultat |
|---|---|
| DreamShaper seul, prompt « cel shading » | rendu 3D photo ; « blue-violet shadows » teint toute la machine en violet |
| DreamShaper seul, mots-clés pondérés | encore plus photo |
| Illustrious XL v0.1 seul (étiquettes, 28 étapes) | délavé, formes déstructurées |
