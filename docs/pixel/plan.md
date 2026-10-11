# Mod Pixel : méthode et plan d'ensemble

Rédigé le 11 octobre 2026. **État : méthode validée par Bastien le 11 octobre (section 8). Étape 0 presque finie (section 6) : reste l'essai B→px
(images cibles de l'assembleur 1 en cours) ; la galerie est faite (12 octobre).**
Situation et pièges connus : [synthese-pixel.md](synthese-pixel.md). Règles visuelles : [`pixel/STYLE.md`](../../pixel/STYLE.md).

Ce document fixe **comment on produit l'intégralité du mod pixel**, sur le modèle du plan du mod cartoon
([docs/cartoon/plan.md](../cartoon/plan.md)) : mêmes lots, même définition de « fini », mêmes outils communs. Il dit
ce qui change parce que le style est du pixel art.

---

## 1. Constat

- **97 fichiers sur ~8 200** (environ 1 %) : assembleurs, convoyeurs, souterrains, répartiteurs, bras, minerais,
  poteaux, câbles, sols de Nauvis. Le style tient (assembleurs et poteaux appréciés), la méthode ne passera pas à
  l'échelle.
- **Tout est dessiné en coordonnées dans Pillow.** Très bien pour ce qui est plat ou répétitif (sols, convoyeurs,
  câbles). Intenable pour ce qui a du volume et beaucoup de vues : radar (64 orientations), trains et voitures
  (36 à 64), tourelles, personnage, ennemis (16 directions, plusieurs animations). Les poteaux ont déjà montré la
  sortie : un petit modèle 3D projeté (`poles.py`).
- **Le mod vit à côté de l'outillage commun.** Nos images n'ont pas la taille des originales ; `data-final-fixes.lua`
  corrige tailles, échelles et décalages. Du coup `build.py`, `check_mod.py`, la couverture, la galerie ne
  s'appliquent pas, et chaque nouveau prototype est un risque de « sprite rectangle outside ».
- **Le style se décide tard** : comme le cartoon avant les images cibles, on ne voit le résultat qu'après l'avoir
  codé.

## 2. Principe

> **L'image cible fixe le style, la technique adaptée produit, la passe pixel unifie.**

1. **Image cible** (machines et objets à volume) : ComfyUI propose, Bastien choisit, comme pour les autres mods
   ([methode-images-cibles.md](../methode-images-cibles.md)), mais avec des **modèles entraînés au pixel art**
   (section 8, question 2). Chaque variante est aussi montrée **pixélisée à la densité du jeu** (16 px par case,
   palette du mod), pour juger ce qui survivra.
2. **Production** par la technique qui convient à la famille (section 4) : Pillow pour le plat et le répétitif,
   **Blender rendu directement en pixels** pour le volume et les rotations.
3. **Passe pixel commune** (`pixel/pixlib/`) : quelle que soit la source, chaque image passe par le même code qui
   impose palette, contours colorés, nettoyage et cadrage. C'est elle qui garantit l'unité du mod.
4. **Contrôle automatique propre au pixel art** (section 3), puis vérification **en jeu**, jamais sur montage.

## 3. Le contrat pixel (règles techniques vérifiées par outil)

| Règle | Valeur | Contrôle |
|---|---|---|
| Densité unique | 16 px d'art par case pour tout le monde (bâtiments, sols, personnage, ennemis, objets au sol) ; 1 px d'art = 4 × 4 px de fichier, `scale = 0.5` | blocs de 4 × 4 px uniformes |
| Grille du monde | les pixels d'art de deux entités voisines tombent sur la même grille (1/16 de case), quel que soit le `shift` de l'original | position des blocs calculée depuis le `shift` |
| Cadre de l'original | même largeur, hauteur, nombre d'images et `line_length` que le fichier remplacé : l'art × 4 est posé dans ce cadre. **Plus de correction de taille en Lua** ; le Lua ne garde que ce qui est vraiment propre au mod (points d'attache des câbles, variantes d'objets au sol) | `check_mod.py pixel --jeu` |
| Palette fermée | toutes les couleurs viennent de `palette.py` (rampes par matière et par niveau) ; jamais de noir pur | couleurs hors palette |
| Pas d'anticrénelage | alpha 0 ou 255 dans les sprites ; ombres au sol en aplat, une seule valeur d'alpha | valeurs d'alpha |
| Animation | mouvements par pas entiers de pixel d'art, boucles fermées ; nombre d'images de l'original, des images répétées sont permises (le pixel art vit bien avec 8 à 16 images distinctes) | — |
| Reproductibilité | un générateur relancé de zéro redonne les mêmes fichiers | `build.py pixel tous --verifier` |

La règle « cadre de l'original » est le gros gain : le mod pixel rejoint `build.py`, `check_mod.py`, l'inventaire,
la couverture, le banc d'essai et la galerie, sans outil à part. Le cadre de l'original est déjà à 64 px par case
avec `scale = 0.5` : notre export × 4 a la même densité, il suffit de le centrer au bon endroit.

## 4. Quelle technique pour quelle famille

| Famille | Technique | Raison |
|---|---|---|
| Sols, eau, rives, minerais, convoyeurs, câbles, décorations | **P** : Pillow procédural (comme aujourd'hui) | vue de dessus, tuiles, motifs : le code donne des pixels propres par construction |
| Fumées, flammes, explosions, particules | **P** | formes simples, peu d'images, palette d'effets |
| Bâtiments (fours, foreuses, coffres, chaudières, tuyaux, labo, raffinerie, réacteur...) | **B→px** : modèle Blender rendu à 16 px par case, puis passe pixel | volume, 4 directions, animations : un modèle au lieu de centaines de coordonnées |
| Rotations nombreuses et créatures (radar, trains, véhicules, tourelles, personnage, ennemis) | **B→px** | seule voie réaliste à 16 à 64 orientations |
| Arbres, rochers, falaises | P ou B→px, au cadrage du lot | dépend de la forme retenue sur l'image cible |
| Icônes | même générateur que l'entité, vue fixe | quasi gratuites une fois l'entité faite |

**B→px, comment.** Rendu Cycles à la **résolution d'art** (pas un rendu en grand réduit ensuite), sans filtre de
pixel, un ton par face (dessus, avant, côtés) en émission comme le mod cartoon, plus une passe d'identifiant de
matière. La passe pixel quantifie chaque matière sur sa rampe de `palette.py`, trace le contour coloré (silhouette et
jonctions entre pièces), retire les pixels isolés et les escaliers irréguliers, place les reflets (1 à 2 px).

**Le risque est connu** : Bastien a déjà écarté un rendu Blender « pixelisé », qui faisait 3D pixelisée. C'était un
rendu en grand, réduit puis filtré : dégradés et anticrénelage survivaient. Ici, ni l'un ni l'autre ne peut passer
(palette fermée, contrôle de l'alpha). L'**essai de l'étape 0** le prouve ou l'écarte, en jeu. S'il est écarté, la solution de repli est le **moteur de `poles.py` généralisé** (boîtes et cylindres
projetés en Python, à la résolution d'art) : plus de travail par objet, mais un contrôle au pixel près.

**On repart de zéro** (décision de Bastien, 11 octobre) : les 97 fichiers déjà faits sont abandonnés, sans revue.
Les familles concernées sont des lots comme les autres (1.1 à 1.6, section 9). Seul le savoir technique est gardé :
les pièges de [synthese-pixel.md](synthese-pixel.md) (tailles lues par les prototypes, conventions des souterrains,
planches de sols, points d'attache des câbles calculés) et l'ancien code, consultable dans l'historique git.

## 5. Le cycle d'un lot

Mêmes lots et mêmes numéros que le mod cartoon, pour comparer les deux mods et partager la galerie.

1. **Cadrage** : liste des fichiers (`tools/inventory.py pixel liste <motif>`), lecture des prototypes, technique
   (P ou B→px), questions de style à trancher. **D'abord : garder, alléger ou retirer ?** Ce que Factorio a
   imaginé pour des sprites détaillés ne convient pas forcément au pixel art (décorations, particules, taches,
   petits détails d'ambiance) : on réduit la quantité ou on retire avant de redessiner.
2. **Image cible** (B→px seulement) : recette `pixel/concept/recette.json`, deux séries de variantes, planche avec
   identifiants (`a-13`...), chaque variante **en grand et pixélisée à 16 px par case**. Bastien choisit ; l'image
   va dans `pixel/concept/cibles/`. Pour P, on suit l'original et `STYLE.md`.
3. **Prototype** : un objet représentatif, comparé original / cible / rendu à la taille du jeu (`compare.py`).
4. **Production** : générateur dans `pixel/pillow/` ou `pixel/blender/`, déclaré dans `pixel/lots.py`,
   lancé par `tools/build.py pixel <lot>` (écrit dans les overrides, régénère le manifeste, contrôle).
5. **Contrôle** : `check_mod.py pixel --jeu` (tailles, chargement) et contrôle pixel (section 3).
6. **Vérification en jeu** : zone du lot dans la galerie, banc d'essai pour les vues de détail.
7. **Commit** du lot, case cochée ici, `STYLE.md` complété ([VALIDÉ] / [PROVISOIRE]), couverture régénérée.

**Fini** = tous les fichiers du lot remplacés ou laissés d'origine avec une raison ; contrôles passés ; vu en jeu
par Bastien ; générateur reproductible.

## 6. Étape 0 : fondations

- [x] **Table rase** (commit `e0c9a4f`) : anciens générateurs, images, `poles_data.lua` et corrections Lua retirés ;
      le mod vide se charge (`check_mod.py pixel --jeu`).
- [x] **Passe pixel commune** `pixel/pixlib/` : `palette.py` (rampes par matière, **provisoires** :
      `python pixel/pixlib/palette.py palette.png` en montre la planche), `passe.py` (alpha net, palette, contours
      colorés, jonctions, nettoyage, ombre en aplat), `cadre.py` (art × 4 dans le cadre de l'original, aligné sur
      la grille du monde ; planches ; icônes 32 px d'art à mipmaps).
- [x] **Rendu Blender en pixels** `pixel/blender/pxlib.py` : rendu à la résolution d'art (un point par pixel, pas
      de tramage), matières de la palette en émission (un ton par orientation de face), carte des matières pour
      la passe ; briques de modélisation reprises du mod cartoon. Vérifié sur une scène d'essai : 7 couleurs, toutes
      dans la palette.
- [x] **`pixel/lots.py` et `build.py pixel`** : seule façon de produire et d'installer (aucun lot pour l'instant).
- [x] **Contrôle pixel** `pixel/controle.py`, appelé par `check_mod.py` (donc par `build.py`) : pixels nets sur la
      grille du monde (d'après le `shift` du prototype), palette, alpha, ombres en aplat, icônes.
- [x] **Couverture** [couverture.md](couverture.md) (`inventory.py pixel`).
- [x] **Galerie** : `tools/galerie.py --mod pixel`, dépendances facultatives et détection du mod dans le scénario
      (variante « pixel », commit `1e27ad4`).
- [x] **Recette ComfyUI** [`pixel/concept/`](../../pixel/concept/README.md) (LoRA Pixel Art XL) et option
      `--pixel` de `planche.py` et `compare.py` (chaque variante aussi à 16 px d'art par case).
- [x] **Allègement des décorations** : réglages de démarrage par famille dans le mod (10 % par défaut), commande
      `/pixel-decorations` pour une carte existante. **À juger en jeu par Bastien.**
- [ ] **Essai B→px** : images cibles de l'assembleur 1 (en cours), choix de Bastien, modèle rendu en pixels,
      posé en jeu. Bastien décide (décision 1). Puis le four en pierre.

Note : la grille du monde n'a de sens que pour ce qui est posé sur la grille (bâtiments, sols) ; arbres,
décorations, véhicules et personnages bougent librement, seule la netteté de leurs pixels est contrôlée.

## 7. Étape 1 : charte visuelle

Pas de revue de l'ancien travail. La charte (palette, contours, densité de détail) se fixe sur les premiers lots :
sols et décorations allégées, puis un arbre et un assembleur, posés ensemble dans la galerie. `STYLE.md` est
réécrit au fil de ces choix ; l'ancien n'est qu'une source d'idées.

## 8. Décisions de Bastien (11 octobre)

1. **Technique des bâtiments** : B→px, si l'essai de l'étape 0 le valide en jeu ; repli sur le moteur de `poles.py`.
2. **Images cibles** : avec des **modèles dédiés au pixel art**, pas le modèle généraliste seul. Candidats, compatibles
   avec ce qui est installé (ControlNet et IP-Adapter SDXL) :
   - **Pixel Art XL** (nerijs, [Hugging Face](https://huggingface.co/nerijs/pixel-art-xl)) : LoRA SDXL, licence
     CreativeML OpenRAIL-M, sans compte ; s'utilise avec DreamShaperXL Turbo. Le plus utilisé ; pas de mot-clé,
     sortie à réduire × 8 au plus proche voisin. **Premier à essayer.**
   - **Pixel Art Game UI Icons** ([Civitai 2443581](https://civitai.com/models/2443581)) : LoRA Illustrious pour les
     icônes (mot-clé `pixelarticon`), avec le checkpoint Illustrious déjà installé ; compte Civitai nécessaire
     (téléchargement par Bastien, comme `WindWaker_IL`). Pour les icônes.
   Les images générées ne sont que des cibles, jamais distribuées. **Les deux sont installés** (11 octobre),
   détail dans [methode-images-cibles.md](../methode-images-cibles.md).
3. **Icônes** : 32 px d'art, export × 2 dans le cadre de 64 px.
4. **Objets sur les convoyeurs et au sol** : variante dessinée à la densité du monde (`pictures` de l'objet).
5. **Décorations et ambiance** : tout ce qui a été pensé pour le Factorio d'origine ne convient pas à ce mod. Une
   grosse partie des décorations est **retirée ou réduite à environ 10 %**, à juger en jeu (étape 0). Règle
   générale ajoutée au cadrage de chaque lot (section 5). Ordre : ce qui couvre l'écran d'abord (décorations,
   nature, eau), puis les bâtiments.
6. **Existant** : on refait tout, sans revoir l'ancien travail. Les familles déjà faites sont des lots comme les
   autres (1.1 à 1.6).

## 9. Lots

Découpage, contenu et jalons : [docs/cartoon/plan.md](../cartoon/plan.md), section 5. Technique et état propres au
mod pixel :

### Familles déjà faites autrefois, à refaire de zéro

| Lot | Technique | Ancien travail (abandonné) |
|---|---|---|
| [ ] 1.1 Sols de Nauvis et transitions | P | jamais commentés |
| [ ] 1.2 Minerais | P | vus en jeu |
| [ ] 1.3 Convoyeurs, souterrains, répartiteurs | P (B→px pour les structures, au cadrage) | validés sauf répartiteurs et turbo |
| [ ] 1.4 Bras | B→px | vus en jeu, ancrage supposé |
| [ ] 1.5 Poteaux et câbles | B→px (poteaux), P (câbles) | validés |
| [ ] 1.6 Assembleurs 1 à 3 | B→px | validés en jeu |

### Étape 2 : début de partie sur Nauvis → 0.1

Ordre de travail : 1.1 et 2.8 (sols et décorations), 1.2 et 2.7 (minerais et nature), 2.9 (eau), puis 1.3 à 1.6,
2.1 à 2.6, 2.10, 2.11.

| Lot | Technique |
|---|---|
| [ ] 2.1 Objets sur les convoyeurs | B→px : icône 32 px d'art et variante au sol à 16 px par case |
| [ ] 2.2 Production de base (four, foreuses) | B→px |
| [ ] 2.3 Stockage | B→px |
| [ ] 2.4 Énergie vapeur | B→px |
| [ ] 2.5 Tuyaux | B→px |
| [ ] 2.6 Petits bâtiments (labo, radar, lampe) | B→px |
| [ ] 2.7 Nature (arbres, rochers, poissons) | P ou B→px, au cadrage |
| [ ] 2.8 Décorations | P, seulement les familles gardées après l'allègement (étape 0) |
| [ ] 2.9 Eau et falaises | P (eau), falaises au cadrage |
| [ ] 2.10 Personnage | B→px |
| [ ] 2.11 Chargeurs et lecteur de convoyeur | B→px |
| [ ] 2.12 Publication 0.1 | — |

Étapes 3 à 6 : celles du cartoon ; bâtiments, véhicules et ennemis en B→px, effets en P.

## 10. Risques

| Sujet | Risque | Réponse |
|---|---|---|
| B→px | « 3D pixelisée » à nouveau | essai de l'étape 0 jugé en jeu ; repli sur le moteur de `poles.py` |
| Rotations | les pixels « grouillent » d'une orientation à l'autre (radar, trains) | formes simples, contours appuyés ; à juger en jeu |
| Fort dézoom | le jeu adoucit les images | inévitable ; le style est pensé pour le zoom normal |
| Personnage et ennemis | animations organiques | même essai de faisabilité que le cartoon (lot 2.10), une fois pour les deux mods |
| Outils communs | une évolution pour le pixel casse le cartoon ou le cel-shading | tout changement de `tools/` relancé sur les trois mods |
