# Mod pixel : synthèse de la situation

État au 2026-10-10. Le guide de style est [STYLE.md](STYLE.md) ; ce fichier raconte où on en est, ce qui a été décidé et ce qui reste à faire.

## Objectif

Remplacer les textures de Factorio 2.0 (base et Space Age) par du **pixel art** dessiné **en code avec Pillow**, dans l'esprit de l'image de référence de Bastien (krank.love : couleurs vives mais calmes, formes franches, contours colorés, ombre portée en aplat). Les formes, proportions et couleurs par niveau restent celles de Factorio.

Ce mod est une alternative au mod **cartoon** (rendus Blender, dossier `cartoon/`). Les deux remplacent les mêmes textures : ils sont déclarés **incompatibles** dans leur `info.json` (`"! factorio-pixel-mod"` / `"! factorio-cartoon-mod"`). Il faut en désactiver un dans le menu Mods (ou dans `mod-list.json`).

## Pourquoi Pillow

Bastien ne dessine pas, et le rendu Blender avec post-traitement faisait « 3D pixelisée ». Le dessin procédural en 2D donne des pixels nets par construction (pas d'anti-aliasing), une palette verrouillée, des contours teintés, et on itère vite : code, rendu PNG, regard sur l'image, correction. Aseprite a été écarté (payant, pas d'apport pour de la génération par code).

## Organisation

```
pixel/
  mod/                      le mod Factorio (info.json, data-final-fixes.lua, manifest.lua, poles_data.lua, graphics/overrides/)
  pillow/                   les générateurs
    palette.py              palette partagée et rampes par niveau
    pixutil.py              ombrage automatique (contour, lumière haut-gauche, ombre bas-droite)
    assembler.py            assembleurs 1 à 3 (planche de 32 images)
    belt.py                 convoyeurs (droits, virages, bouts de ligne) pour 5 niveaux
    belt_structures.py      souterrains et répartiteurs
    inserter.py             inserters (tige, mains, plateforme, ombres)
    ore.py                  minerais
    poles.py                poteaux électriques (modèle 3D projeté sur 4 rotations)
    wire.py                 câbles cuivre, rouge, vert
    terrain.py              sols de Nauvis et masques de transition
    export_mod.py           écrit tout dans mod/graphics/overrides/ et régénère manifest.lua et poles_data.lua
  STYLE.md   README.md   SYNTHESE.md
```

**Principe du mod** : `data-final-fixes.lua` parcourt `data.raw` et remplace les chemins listés dans `manifest.lua` (clés `filename`, `icon`, `picture`, `spritesheet`) par les fichiers de `graphics/overrides/<jeu>/...` (même chemin que l'original). Il corrige ensuite les tailles, échelles, décalages et points d'attache de certains prototypes quand nos images n'ont pas les dimensions des originales.

**Échelle** : 1 pixel d'art = 2 pixels de jeu = 4 pixels de fichier (export x4, affichage à l'échelle 0,5), soit **16 px d'art par case**. Interpolation du jeu : les pixels restent nets de près, s'adoucissent à fort dézoom.

## Génération et installation

Depuis la racine du repo, avec le `.venv` (Pillow, numpy) :

```bash
.venv/bin/python pixel/pillow/export_mod.py     # régénère toutes les images, manifest.lua et poles_data.lua
tools/install_mod.sh pixel                      # copie le mod dans le dossier mods de Factorio (Windows, via WSL)
```

L'export complet prend plusieurs minutes (terrain, planches de 8192 px) ; l'installation est lente aussi (copie d'images volumineuses vers `/mnt/c`). Chaque générateur a son propre aperçu en ligne de commande (`python pixel/pillow/<fichier>.py <dossier>`).

## État par élément

| Élément | Contenu | Statut |
|---|---|---|
| **Assembleurs 1 à 3** | forme de Factorio (rebord, plateau cuivre, paroi à triangles, flancs évasés), couleurs des niveaux (gris-vert, bleu, olive), moteur, piston ou deux vérins fins (niveau 3), engrenages, bras articulé (niveaux 2 et 3), voyant qui clignote ; planche de 32 images, ombre animée | validé en jeu |
| **Convoyeurs** | droits, 8 virages, chevrons animés ; fonds teintés par niveau : brun (basique), bordeaux (rapide), marine (express), vert (turbo, Space Age) | validé en jeu (turbo à vérifier) |
| **Souterrains** | 4 niveaux ; capot en voûte sur la moitié de la case, entrée et sortie en miroir | corrigé suite au dernier retour, validé par Bastien avec les bouts de ligne supprimés |
| **Répartiteurs** | 4 niveaux et lane-splitter ; poteaux, nez diviseur, rail à 3 engrenages animés, capots colorés, voyants | à vérifier en jeu (refaits plus travaillés, pas encore commentés) |
| **Inserters** | basique, rapide, longs bras, burner, en vrac ; tige, mains ouverte et fermée, plateforme à 4 orientations, ombres | vus en jeu, pas de remarque ; ancrage des mains supposé |
| **Minerais** | fer, cuivre, charbon, pierre, uranium ; planche 8 x 8 (étapes de richesse x variantes) | vus en jeu, pas de remarque |
| **Poteaux électriques** | petit (bois), moyen (rouillé), grand (acier), sous-station ; 4 rotations ; points d'attache des câbles calculés | « très bien » ; moyen et grand allégés sur demande |
| **Câbles** | cuivre, rouge, vert : même courbe que le jeu, paliers nets, deux tons ; ombre | validés |
| **Terrain de Nauvis** | herbe 1 à 4, terre sèche, terre 1 à 7, sable 1 à 3, désert rouge 0 à 3 ; masques de transition quantifiés | à vérifier en jeu (aucun retour) |

## Décisions de Bastien à conserver

- Le design suit **Factorio** (formes, couleurs des niveaux) avec des éléments d'assemblage par-dessus ; l'image krank.love donne la direction générale du style, pas les formes.
- Vue à environ 30° pour les bâtiments, avec **flancs gauche et droit visibles** (évasés d'environ 4 px de chaque côté, pas plus).
- Convoyeurs : **petits chevrons**, fond **teinté par niveau**, couleurs sourdes pour rester dans la gamme des machines.
- Souterrains : couleurs alignées sur le convoyeur du même niveau ; entrée et sortie doivent se distinguer clairement.
- **Pas de bouts de ligne** visibles sur les convoyeurs (rangées 12 à 19 de la planche volontairement vides, interrupteur `END_CAPS` dans `belt.py`).
- Poteaux moyen et grand : peu chargés visuellement.
- Prévenir Bastien avant d'installer une application ou une dépendance sur sa machine.

## Ce qu'on a appris (pièges à ne pas refaire)

1. **Les tailles de sprites doivent correspondre aux valeurs lues par les prototypes**, sinon le jeu refuse de charger (« sprite rectangle outside the actual sprite size »). Pour chaque fichier remplacé, vérifier tous les prototypes qui l'utilisent : le lane-splitter réutilise les sprites du répartiteur, le `stack-inserter` de Space Age réutilise l'ombre de la tige du burner. Quand une taille change, on la corrige en Lua dans `data-final-fixes.lua`.
2. **Souterrains** (conventions vérifiées en jeu avec le mod cartoon) : le capot couvre la moitié **aval** de la case pour une entrée et la moitié **amont** pour une sortie ; la cellule « sortie » d'une colonne de la planche contient le capot de la **direction opposée** ; les rangées 2 et 3 (chargement par le côté, est et ouest) copient les rangées 0 et 1 ; les pièces « patch » restent celles du jeu.
3. **Bouts de ligne des convoyeurs** (rangées 12 à 19) : rangées paires animées, impaires fixes, chevrons dans le sens du flux, position au bord aval. Dessinés trop visibles, ils ressortaient autour des souterrains posés seuls : on les a supprimés.
4. **Mise à jour des mods** : le jeu doit être relancé pour relire les textures ; deux mods qui remplacent les mêmes fichiers ne cohabitent pas.
5. **Terrain** : un sol est une planche de 4096 px de large avec 3 bandes de variantes (1, 2, 4 cases ; 8 pour le sable 1) séparées par du vide. Les transitions entre sols sont obtenues en masquant la texture voisine avec un masque en dégradé (`masks/transition-1`, `-3`, `-4`) ; on les a seuillés par blocs de 4 x 4 px. Ces masques servent aussi à des tuiles de Space Age.
6. **Poteaux** : les points d'attache des câbles (`connection_points`) dépendent des isolateurs dessinés et de la rotation ; ils sont **générés** (`poles_data.lua`), ne pas les éditer à la main.
7. Les fichiers du dossier de données de Factorio sont lus depuis `/mnt/c/Program Files (x86)/Steam/steamapps/common/Factorio/data` ; les parcourir en entier est lent, restreindre les recherches à `prototypes/`.
8. Le `factorio-current.log` / `factorio-previous.log` (dossier `AppData/Roaming/Factorio`) donne la cause exacte d'une erreur de chargement en une lecture.

## À vérifier en jeu

- Terrain : coutures entre variantes, lisibilité des machines sur les nouveaux fonds, transitions nettes entre sols, densité des fleurs et des touffes.
- Répartiteurs : taille et lisibilité, voyants qui clignotent en permanence alors que l'animation ne devrait jouer qu'au passage d'objets.
- Convoyeur, souterrain et répartiteur turbo (Space Age) : couleurs et chargement sans erreur.
- Inserters : décalage éventuel des mains et de la plateforme (l'ancrage a été supposé au centre de l'image) ; ombre des mains en aplat translucide fixe.
- Câbles : accroche exacte aux isolateurs, ombre des câbles.
- Assembleurs : débord de 1 px de chaque côté de l'emprise 3 x 3, décalage vertical (−0,25 case, estimé).

## Limites connues

- Aperçus et plans de vérification faits sur images, pas de test automatique : tout se juge en jeu.
- Pixel art de près ; à fort dézoom les images sont adoucies par le jeu.
- Les icônes (objets, recettes) ne sont pas refaites, sauf les icônes d'assembleurs.

## Reste à faire

- **Terrain** : eau peu profonde, profonde, boue ; bord de mer et ses transitions ; béton, béton raffiné, chemin de pierre ; falaises ; arbres ; herbes et rochers décoratifs.
- **Bâtiments** : coffres, mineurs, fours, chaudières, moteurs à vapeur, pompes, tuyaux, réservoirs, laboratoire, raffinerie, usine chimique, tourelles, murs, portes, robots, rails, trains, voitures.
- **Icônes** et **objets sur les convoyeurs** (plaques, engrenages, etc.), personnage, ennemis.
- **Style** : compléter STYLE.md avec les règles de chaque nouvelle famille d'objets.

## Historique des commits (mod pixel)

| Commit | Contenu |
|---|---|
| `e5abfda`, `38acf89` | assembleurs 1 à 3, ombre animée, voyant, STYLE.md |
| `4a7f3e2`, `1cb1d75`, `3a96602` | convoyeurs, petits chevrons, fonds teintés |
| `e93b631`, `204b8e6` | inserters, minerais, inserter en vrac, premiers souterrains et répartiteurs |
| `3617e16` | correction du chargement (lane-splitter, stack-inserter) |
| `4572260` à `4e1b156` | refonte des souterrains et des répartiteurs, suppression des bouts de ligne |
| `217b4e5` | convoyeur turbo, souterrain et répartiteur turbo |
| `489d85e`, `aaf0f87` | poteaux électriques, câbles, allègement des poteaux moyen et grand |
| `421835d` | sols de Nauvis et masques de transition |
