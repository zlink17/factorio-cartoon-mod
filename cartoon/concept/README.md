# Images cibles du mod cartoon

Méthode commune aux mods : [docs/methode-images-cibles.md](../../docs/methode-images-cibles.md) (outils dans
`tools/concept/`). Ici, seulement ce qui est propre au cartoon : la recette et les images retenues.

## Recette (`recette.json`)

Établie sur le propulseur (11 octobre 2026) : DreamShaper XL Turbo, 8 étapes, cfg 2,5 ; ControlNet profondeur 0,7 et
contours 0,35 ; **IP-Adapter « style transfer » 0,55 sur cinq sprites du mod** (assembleur 1, chaudière, machine
à vapeur, radar, laboratoire). À 0,8, l'IP-Adapter tire toutes les couleurs vers le gris-vert de nos références
(série A) ; à 0,55, les couleurs de l'objet reviennent, vives et contrastées (série B).

Références de style (à refaire dans le dossier des guides de chaque objet) :

```bash
.venv/bin/python tools/concept/styles.py <guides> \
    cartoon/mod/graphics/overrides/base/entity/assembling-machine-1/assembling-machine-1.png:214:226 \
    cartoon/mod/graphics/overrides/base/entity/boiler/boiler-N-idle.png \
    cartoon/mod/graphics/overrides/base/entity/steam-engine/steam-engine-H.png:352:257 \
    cartoon/mod/graphics/overrides/base/entity/radar/radar.png:196:254 \
    cartoon/mod/graphics/overrides/base/entity/lab/lab.png:194:174
```

Génération (le texte de l'objet va dans `--prompt` ; la recette donne le style) :

```bash
.venv/bin/python -I tools/concept/concept.py <guides> <sortie> 21,22,23,24 --tag b \
    --recette cartoon/concept/recette.json \
    --prompt "a rocket thruster engine machine: beige cream engine block in the upper part, big round open exhaust nozzle bell at the bottom, dark inside with radial ribs, orange copper pipes, chunky, few large parts"
```

Mélange de deux variantes (dessin de l'une, couleurs de l'autre) : repartir de la première en img2img, guidé par
son propre trait, avec la seconde comme seule référence de style :
`--init <a.png> --denoise 0.7 --edges-file trait-a.png --edges 0.7 --depth 0.5 --styles couleurs-b.png --style 0.8`
(le trait : pixels sombres de l'image de départ ; la référence : l'image sur fond gris, carrée). 0,55 garde mieux
le dessin, 0,7 prend mieux les couleurs.

## Images retenues (`cibles/`)

| Objet | Image | Choix de Bastien | Modèle |
|---|---|---|---|
| Propulseur (Space Age) | `propulseur-m70-42.png` | dessin de a-13, couleurs de b-22 (mélange à 0,7) | `cartoon/blender/thruster.py` (essai, image fixe) |

Ce que l'essai a appris : le modèle Blender reprend les grandes masses, les couleurs et la silhouette ; la densité
de la tuyauterie passe avec des tubes lissés et un reflet sur les métaux (exception au guide, `STYLE.md` §4).
