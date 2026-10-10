# Mod Cartoon : synthèse du travail

État au 10 octobre 2026. Ce document résume ce qui a été fait, comment, ce qu'on a appris en chemin et ce qui reste.
Le guide de style de référence est [`cartoon/STYLE.md`](../cartoon/STYLE.md) ; le mode d'emploi des outils est dans [`cartoon/README.md`](../cartoon/README.md).

## 1. Objectif

Un mod Factorio 2.0 qui remplace les textures du jeu par une version cartoon : aplats de couleur, gros contours noir chaud,
ombrage à trois tons, mêmes formes et mêmes cadrages que l'original (le joueur doit reconnaître chaque objet au premier coup d'œil).
Les contraintes de départ : outils gratuits uniquement, GPU modeste (GTX 1660 Super, 6 Go), cohérence du style prioritaire.

## 2. Décisions de méthode

| Piste | Verdict |
|---|---|
| Filtre automatique (lissage, couleurs réduites, contours) | **Abandonné** : résultat médiocre (taches sombres, couleurs ternes). Supprimé du repo. |
| IA locale (ComfyUI, SD 1.5 + ControlNet canny) | **Essayée, non retenue** pour les machines. Sur un rendu Blender, les formes tiennent mais l'IA n'apporte rien de net (à denoise bas) ou casse le style (à denoise 0,5 : textures, couleurs parasites). Outils conservés dans `cartoon/ai/`. |
| **Rendus 3D toon avec Blender (`bpy`)** | **Technique principale.** Un modèle 3D par objet, rendu avec la même projection que l'original, ce qui garantit cohérence, animations parfaites et réutilisation entre niveaux (assembleurs 1 à 3, convoyeurs jaune/rouge/bleu/turbo...). |
| Génération 2D procédurale (OpenCV) | Utilisée pour les **sols** (textures plates tuilables) et les **câbles**. |

## 3. Organisation du repo

```
cartoon/
  mod/        le mod installable (info.json, Lua, manifest.lua, graphics/overrides/)
  blender/    générateurs 3D : style.py (source de vérité), lib.py, assembler*.py, animate.py, belt.py, inserter.py,
              underground.py, splitter.py, pole.py, ore.py
  terrain/    ground.py : sols de Nauvis
  ai/         ComfyUI (comfy_batch.py, workflow, post-traitement) : essai, non retenu
  STYLE.md    guide de style
tools/        build_manifest.py (génère le manifeste), install_mod.sh (installe dans Factorio), check_sizes.py (contrôle)
docs/         notes de session et cette synthèse
```

Principe commun : un générateur écrit des PNG dans `cartoon/mod/graphics/overrides/<jeu>/...`, **au même chemin que l'original** ;
`tools/build_manifest.py` liste les fichiers dans `manifest.lua` ; `data-final-fixes.lua` remplace dans tous les prototypes
les chemins `__base__/graphics/...` listés (clés `filename`, `icon`, `picture`, `spritesheet`). Ce qui n'est pas refait reste d'origine.
Le mod déclare `! factorio-pixel-mod` (incompatible avec le mod pixel du même repo) et `? space-age` (dépendance optionnelle,
pour l'ordre de chargement).

## 4. Le style, tel que calé

- **Projection** : bâtiments alignés sur la grille, vue inclinée de 30° (sol raccourci par cos 30°, parois en tronc de pyramide) ;
  **convoyeurs, tuyaux au sol : vue de dessus**. Calée par mesure sur l'assembleur 1 original (recouvrement de silhouette 92 %).
- **Contours** : noir chaud, épaisseur définie en unités du monde. Sur les petites pièces (bras, capots, pylônes, tas de minerai),
  on utilise un contour plus fin sinon elles deviennent entièrement noires.
- **Trois tons** : dessus ×1,12, face avant ×0,85, côtés ×0,62.
- **Palette** : teintes de l'assembleur 1 conservées (gris-vert, cuivre rouillé, laiton, fer sombre) ; une teinte par niveau
  (assembleur 2 bleu, assembleur 3 olive ; convoyeurs jaune, rouge, bleu, vert turbo ; bras brun, jaune, rouge, bleu, vert) ;
  teintes claires pour les pylônes (ils doivent ressortir sur le sol brun) ; une couleur par minerai.
- **Format** : PNG RGBA, même dimension et même cadrage que l'original, au pixel près.

## 5. Ce qui est fait (153 sprites remplacés)

| Famille | Contenu | Générateur |
|---|---|---|
| Assembleurs 1, 2, 3 | Planches animées de 32 images, ombres (animées pour 2 et 3), icônes. Niveau 2 : bras articulé ; niveau 3 : deux bras et deux pistons. | `assembler.py`, `animate.py`, `assembler_extras.py` |
| Convoyeurs | Jaune, rouge, bleu et turbo (Space Age) : 20 rangées (droits, 8 courbes, bouts de ligne) × 16, 32 ou 64 images ; stries ton sur ton et flèches colorées comme l'original ; icônes. | `belt.py` |
| Souterrains | Trois niveaux + turbo : capot courbé le long du flux, bouche sombre à linteau, entrée et sortie différentes. | `underground.py` |
| Répartiteurs | Trois niveaux + turbo : tête de 2 cases animée (chariot d'une voie à l'autre, pignons), moitiés haute et basse pour l'est et l'ouest. | `splitter.py` |
| Bras robotisés | À charbon, de base, à longue portée, rapide, en vrac : plateformes (4 orientations), mains, ombres, icônes. | `inserter.py` |
| Pylônes et câbles | Poteau, poteau moyen, pylône, sous-station (4 variantes chacun, ombres, icônes) ; câbles cuivre, rouge, vert, ombre, surbrillance. | `pole.py` |
| Minerais | Fer, cuivre, charbon, pierre, uranium : gisements (8 étapes × 8 variantes), calque lumineux de l'uranium, 20 icônes (aussi les objets sur les convoyeurs). | `ore.py` |
| Sols de Nauvis | 19 planches (herbe, terre, sable, désert rouge) en aplats avec petits détails ; les masques de transition restent d'origine. | `terrain/ground.py` |

## 6. Ce qu'on a appris (à ne pas redécouvrir)

- **Une planche de mauvaise taille empêche Factorio de démarrer** (« sprite rectangle is outside the actual sprite size »).
  Le cas qui nous a piégés : le répartiteur express a un côté ouest de 94 px au lieu de 90. `tools/check_sizes.py` compare chaque
  sprite du mod à l'original ; à lancer avant chaque installation. Le journal est dans `AppData\Roaming\Factorio\factorio-current.log`.
- **Les tailles et décalages viennent des prototypes** (`data/*/prototypes/...`), pas des noms de fichiers : il faut les lire
  (taille d'image, nombre d'images, `shift`, `line_length`).
- **Une sortie de souterrain utilise la cellule de la direction opposée** (vérifié en jeu, et dans l'original la cellule « sortie est » a
  des chevrons tournés vers l'ouest). Les colonnes de la planche sont dans l'ordre nord, est, sud, ouest.
- **Les câbles s'accrochent à des points fixés par le prototype** (`connection_points`, par rapport au centre de l'entité) : les
  isolateurs des pylônes sont placés exactement là (écart de 0 à 2 px mesuré).
- **Le convoyeur turbo décale d'une demi-boucle les cases voisines** (`alternate`) : 64 images, flèche toutes les 2 cases.
- **Raccords** : le motif d'un virage de convoyeur est étiré sur la longueur de l'arc pour se raccorder aux droits à chaque image.
- **Les ombres sont des fichiers séparés** (`draw_as_shadow`) ; une multiplication sur des octets (255 × 255) avait vidé toutes les
  ombres des pylônes sans erreur visible : le contrôle d'ombres vides est maintenant dans `check_sizes.py`.
- **Contraste** : des sprites bruns sur un sol brun disparaissent ; il faut des teintes claires et de vraies ombres.
- **Le sol** est composé de planches de textures de 64 px par case (variantes de 1, 2, 4, 8 cases) mélangées par des masques ; on
  peut remplacer les textures sans toucher aux masques, à condition qu'aucun détail ne touche le bord d'une cellule.
- **Sous WSL** : le dossier Factorio est lisible depuis `/mnt/c/...` ; ComfyUI Desktop n'est joignable que si WSL est en mode réseau
  « mirrored » (`.wslconfig`). `bpy` demande Python 3.11 (environnement `.venv` créé avec `uv`).

## 7. Ce qui reste

À vérifier en jeu (jamais vu à l'écran, seulement en aperçus composés) : bras robotisés (ordre des 4 orientations de plateforme,
bras à longue portée), capot des souterrains (pièces « patch » laissées vides), animation des répartiteurs, sols (aspect des
transitions, qui restent des fondus doux).

À faire, par ordre de priorité envisagé :
1. **Objets sur les convoyeurs** : plaques, engrenage, câble, circuit, bâton, acier, brique, plastique, soufre, batterie... (une vingtaine d'icônes couvre l'essentiel).
2. **Rochers**, puis **arbres** (des dizaines de modèles et de planches), puis **décorations du sol** (touffes, cailloux), **eau** et **falaises**.
3. **Chargeurs**, lecteur de convoyeur, tuyaux des assembleurs 2 et 3 (`-pipe-N/E/S/W`), paratonnerre, reflets sur l'eau des pylônes.
4. Pièces « patch » des souterrains, patch « gelé » d'Aquilo (turbo), masques de transition du sol plus nets.
5. Fours, personnage, GUI et icônes de l'interface, autres planètes.

## 8. Chiffres

- 153 sprites remplacés : 75 d'entités, 41 d'icônes, 19 de terrain, 5 de câbles (jeu `core`), 13 pour Space Age.
- ~2 700 lignes de code (générateurs Blender, terrain, ComfyUI, outils) ; 37 Mo d'images dans `cartoon/mod/graphics` (dont 14 Mo de sols).
- Le mod n'a pas été publié ; il s'installe avec `tools/install_mod.sh cartoon`.
