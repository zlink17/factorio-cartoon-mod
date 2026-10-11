# Méthode : images cibles par ComfyUI, production par Blender

Méthode commune aux mods du repo (cartoon, cel-shading), validée par Bastien le 11 octobre 2026 après l'essai du
propulseur (mod cartoon) et de l'assembleur 1 (mod cel-shading).

## Changement du 12 octobre : le prototype Blender d'abord, l'IA si besoin

Décision de Bastien, après l'arbre du mod cel-shading : un premier prototype Blender, fait vite, a donné la direction
mieux que les images générées. L'image cible n'est donc **plus systématique** :

1. **Prototype Blender** d'abord : quelques grosses formes, aux couleurs et aux règles du guide de style du mod, à
   l'emprise de l'original. Montré en grand et à la taille du jeu (puis en jeu), Bastien juge.
2. S'il convient, on **itère dessus** ; Bastien peut donner une image de référence pour s'en inspirer (ex.
   `celshading/concept/cibles/arbre-bastien.jpg`).
3. S'il **ne colle pas** (pas de direction, rendu trop pauvre), on passe par l'IA pour trouver une bonne première
   source : les étapes ci-dessous, puis le modèle Blender s'approche de l'image retenue.

## Principe (quand on passe par l'IA)

**L'IA donne la direction, Blender produit.** Pour chaque objet à refaire, ComfyUI génère des variantes guidées par
le sprite original (silhouette, volumes) et par le style du mod ; Bastien choisit ; le modèle Blender reproduit
l'image retenue. L'image générée n'est **jamais** le sprite final : elle n'a ni animation, ni directions, ni cadrage
exact, et deux générations ne se ressemblent pas. Blender garde ce qui fait la production : planches animées,
quatre directions, niveaux, cadre au pixel près, reproductibilité.

Avant cette méthode, on dessinait les machines directement en code (formes simples, chiffres) : on ne voyait le
résultat qu'après coup, et les choix de style arrivaient tard. Des croquis 2D en aplats n'ont pas aidé Bastien ;
une image riche, si.

## Étapes pour un objet (passage par l'IA)

1. **Guides** tirés du sprite original : `tools/concept/prepare.py` (contours, profondeur, masque, cadrage, shift).
2. **Références de style** du mod : `tools/concept/styles.py` (nos propres sprites, recadrés sur fond gris).
3. **Variantes** : `tools/concept/concept.py` avec la recette du mod (`<mod>/concept/recette.json`) et le texte de
   l'objet ; deux séries de 4 graines, avec deux dosages (plus proche de l'original / plus libre).
4. **Planche** : `tools/concept/planche.py`. **Chaque image porte son identifiant** (`a-13`, `b-22`...) : Bastien
   désigne les images par ce nom. Chaque variante est montrée en grand et à la taille du jeu.
5. **Choix de Bastien** : une variante, un mélange (img2img : dessin de l'une, couleurs de l'autre, voir la recette
   du mod), ou des commentaires pour une nouvelle série.
6. **Modèle Blender** qui s'approche de l'image retenue, dans les règles du guide de style du mod ; un écart au guide
   demandé par la cible (ex. reflet sur les tuyaux) est proposé à Bastien et noté dans le guide.
7. **Comparaison** original / cible / rendu, en grand, en zoom x2 et à la taille du jeu : `tools/concept/compare.py`.
   Itérer zone par zone ; montrer à Bastien.
8. Puis la suite habituelle d'un lot : production complète, contrôle, vérification en jeu, commit.

Exemple (propulseur) :

```bash
~/workspace/comfyui/.venv/bin/python -I tools/concept/prepare.py .cache/concept/propulseur/guides \
    space-age/graphics/entity/thruster/thruster-1.png 264 542 --shift 0.046875 1.78125
.venv/bin/python tools/concept/styles.py .cache/concept/propulseur/guides <références du mod...>
.venv/bin/python -I tools/concept/concept.py .cache/concept/propulseur/guides .cache/concept/propulseur/gen \
    11,12,13,14 --tag a --recette cartoon/concept/recette.json --prompt "a rocket thruster engine machine..."
.venv/bin/python -I tools/concept/planche.py .cache/concept/propulseur/guides .cache/concept/propulseur/planche-a.png \
    .cache/concept/propulseur/gen/a-*.png --sol plateforme
.venv/bin/python -I tools/concept/compare.py .cache/concept/propulseur/guides cartoon/concept/cibles/propulseur-m70-42.png \
    <rendu Blender> .cache/concept/propulseur/compare.png --sol plateforme
```

## Rangement

| Quoi | Où |
|---|---|
| Outils communs | `tools/concept/` (versionné) |
| Recette d'un mod (texte de style, références, réglages) | `<mod>/concept/recette.json` + `README.md` (versionné) |
| Images retenues | `<mod>/concept/cibles/<objet>-<identifiant>.png` (versionné) |
| Guides, variantes, planches | `.cache/concept/<objet>/` (non versionné) |

## Règles

- **Une génération à la fois** : ComfyUI et la carte graphique (GTX 1660 Super, 6 Go) sont partagés par toutes les
  sessions. Prévenir les autres sessions avant de lancer une série, comme pour le banc d'essai.
- Environ **1 min 30 par image** (~1 Mpx, 8 étapes) ; 3 min pour la première (chargement des modèles).
- Toujours **l'identifiant sur les planches**, et la vue à la taille du jeu à côté de la vue en grand.
- Les choix de style restent ceux de Bastien : on propose des variantes, il choisit.

## Installation (faite le 11 octobre 2026, hors du repo)

- ComfyUI dans WSL : `~/workspace/comfyui` (environnement `.venv`, Python 3.12, PyTorch CUDA 12.8). Lancer le
  serveur s'il ne répond pas sur 127.0.0.1:8188 :

  ```bash
  cd ~/workspace/comfyui && .venv/bin/python main.py --listen 127.0.0.1 --port 8188 --disable-auto-launch
  ```
- Nœuds : `custom_nodes/ComfyUI_IPAdapter_plus`. Depth Anything V2 small (licence Apache 2.0) est téléchargé par
  `transformers` au premier `prepare.py`.

| Modèle (`models/`) | Rôle | Licence |
|---|---|---|
| `checkpoints/DreamShaperXL_Turbo_v2_1.safetensors` | SDXL, 8 étapes | CreativeML OpenRAIL++ |
| `controlnet/controlnet-union-sdxl-promax.safetensors` (xinsir) | profondeur et contours | Apache 2.0 |
| `ipadapter/ip-adapter-plus_sdxl_vit-h.safetensors` + `clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | style par l'image | Apache 2.0 |
| `loras/WindWaker_IL.safetensors` (ajouté par Bastien, cel-shading) | style Wind Waker pour Illustrious | Civitai [170319](https://civitai.com/models/170319), version IL_v1.0 : gratuit, dérivés permis, vente des images non permise ; téléchargement réservé aux comptes connectés |
| `loras/pixel-art-xl.safetensors` (pixel, installé le 11 octobre) | pixel art pour SDXL (avec DreamShaperXL Turbo) : pas de mot-clé, sortie à réduire × 8 au plus proche voisin | Hugging Face [nerijs/pixel-art-xl](https://huggingface.co/nerijs/pixel-art-xl), CreativeML OpenRAIL-M |
| `loras/PixelArt_Icon_IL_M_V2.1_00002.safetensors.safetensors` (ajouté par Bastien, pixel) | icônes pixel art pour Illustrious, mot-clé `pixelarticon` | Civitai [2443581](https://civitai.com/models/2443581), licence Illustrious ; téléchargement réservé aux comptes connectés |

Ancien essai, non retenu : ComfyUI Desktop sous Windows avec SD 1.5 + ControlNet canny, en filtre sur des rendus
(`cartoon/ai/`) ; l'IA y faisait le sprite final, ce qui ne marche pas.
