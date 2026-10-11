# Mod Cartoon : plan d'ensemble

Rédigé le 10 octobre 2026. **État (11 octobre) : étapes 0 et 1 terminées, lots 2.1, 2.2, 2.3, 2.4, 2.7 et 2.8 faits ; prochaine action : lot 2.5 Tuyaux. Galerie jouable en place (`cartoon-galerie/`).** Point de départ : [synthese-cartoon.md](synthese-cartoon.md) (état au 10 octobre).
Règles visuelles : [`cartoon/STYLE.md`](../../cartoon/STYLE.md).

Ce document fixe **ce qu'il reste à faire pour obtenir un mod complet et publiable**, dans quel ordre, et **comment on
travaille** désormais. Il est volontairement « macro » : chaque lot sera détaillé au moment de le commencer.

---

## 1. Ampleur du travail

Inventaire des PNG du jeu (Factorio 2.0, dossier `data/`) :

| Jeu | PNG | Gros postes |
|---|---|---|
| `base` | 4 220 | entités 2 344 (dont arbres 559, pompes 111, puits de chaleur 92, rails hérités 154, ennemis ~280), décorations 759, icônes 580, particules 170, techno 132, sols 156 |
| `space-age` | 3 516 | astéroïdes 378, plantes 109, canon électrique 78, grande foreuse 73, cinq planètes de sols et de décorations, ennemis de Gleba et de Vulcanus |
| `core` | 519 | interface (GUI), curseurs, câbles, visualisations |
| `elevated-rails` | 186 | rails surélevés, trains vus en hauteur |
| `quality` | 52 | icônes de qualité, modules |

**Fait : 153 fichiers (≈ 2 %).** Mais ce sont les fichiers les plus visibles des premières heures de jeu, et la chaîne
de production (Blender, contrôle des tailles, manifeste, installation) est en place.

Beaucoup de fichiers n'ont pas besoin d'être refaits : masques (`*_mask.png`, teintés par le jeu), cartes d'effets
(`effect_map`), reflets dans l'eau, bruits et LUT de shaders. Le premier travail de l'étape 0 est de les distinguer.

---

## 2. Comment on travaille désormais

### 2.1 Un lot = une unité de travail

Le travail est découpé en **lots** (une famille d'objets : « fours », « arbres », « trains »...). Pour chaque lot :

1. **Cadrage** : liste des fichiers à refaire (sortie de l'inventaire), lecture des prototypes (tailles, `shift`, nombre
   d'images, `line_length`, directions), choix de la technique, questions de style à trancher avec Bastien.
2. **Prototype** : un seul objet représentatif, validé visuellement (aperçu à la taille du jeu, à côté de l'original).
3. **Production** : générateur complet, qui écrit **directement** dans `cartoon/mod/graphics/overrides/`.
4. **Contrôle automatique** : tailles, ombres non vides, manifeste à jour (voir 2.3).
5. **Vérification en jeu** : capture du banc d'essai (voir étape 0), comparée à la capture d'origine.
6. **Commit** du lot (générateur + PNG + manifeste + mise à jour de `STYLE.md` et de la couverture), puis **la case
   du lot est cochée ici**.

### 2.2 Définition de « fini »

Un lot est fini quand : tous ses fichiers sont remplacés ou marqués « laissés d'origine » avec une raison ; le
contrôle automatique passe ; il a été **vu en jeu** (pas seulement en aperçu composé) ; le générateur se relance
de zéro et redonne les mêmes fichiers.

### 2.3 Contrôle avant chaque installation

`tools/check_mod.py cartoon --jeu` : tailles identiques à l'original (donc mipmaps des icônes conservées), canal
alpha, ombres non vides, manifeste à jour, images inutilisées, et test de chargement dans une instance isolée de
Factorio (le mod se charge, aucun prototype ne pointe encore vers un original remplacé).

### 2.4 Suivi

- **Ce plan** : cases cochées par lot, mis à jour à chaque fin de lot.
- **La galerie** (`cartoon-galerie/mod/`, scénario « galerie ») : chaque lot y ajoute ou complète sa zone, contrôlée
  par `tools/galerie.py`, puis installée dans le jeu de Bastien (`tools/install_mod.sh cartoon-galerie`).
- **`docs/cartoon/couverture.md`** (généré) : pourcentage de fichiers remplacés par famille et par jeu.
- **`synthese-cartoon.md`** : leçons apprises, enrichie quand on découvre un piège.
- **Versions** : `info.json` passe en `0.1.0` à la première publication, puis une version mineure par jalon.
  `changelog.txt` au format Factorio.

---

## 3. Étape 0 : fondations (avant tout nouveau sprite)

Objectif : rendre la production rapide, vérifiable et reproductible. **C'est l'étape qui rend le reste réaliste.**

- [x] **Commiter le travail en cours** (minerais, `ore.py`, icônes, retouches de `STYLE.md` et `style.py`).
- [x] **Inventaire automatique** (`tools/inventory.py`) : lancer `factorio.exe --dump-data` (accessible depuis WSL) pour
      obtenir `data-raw-dump.json`, en extraire chaque fichier PNG référencé avec son prototype, sa taille, son nombre
      d'images et son rôle (sprite, ombre, masque, effet, icône). Produit la liste de travail de chaque lot et
      `couverture.md`. Les fichiers à ne pas refaire (masques, effets, reflets) y sont marqués une fois pour toutes.
- [x] **Banc d'essai en jeu automatisé** (`tools/bench.py`, scénario dans `tools/bench/mod/`) : un petit mod de test (ou scénario) dont le `control.lua` pose une vitrine
      (chaque entité, dans chaque direction, convoyeurs chargés d'objets, sols et nature) et prend des captures avec
      `game.take_screenshot`, lancé en ligne de commande depuis WSL. Même vitrine avec et sans le mod : comparaison
      côte à côte. Si Factorio refuse de démarrer, l'erreur est lue dans `factorio-current.log`.
- [x] **Galerie jouable** (`cartoon-galerie/mod/`, mod `factorio-cartoon-galerie`, ajoutée le 11 octobre) : scénario
      lancé par Bastien depuis Jeu solo > Scénarios. Une zone encadrée par lot, machines en marche et réapprovisionnées
      sans fin, fenêtre pour aller à chaque zone, mode triche, sans ennemis ; le reste de la carte est un Nauvis normal.
      Le mod cartoon y est facultatif : désactivé, la même carte montre l'original. Contrôle : `tools/galerie.py`.
- [x] **Une commande de production** : `tools/build.py cartoon <lot>` (lots déclarés dans `cartoon/lots.py`) lance le bon générateur, écrit dans les overrides,
      régénère le manifeste et lance le contrôle. Fini la copie à la main depuis `sortie/`.
- [x] **Factoriser les générateurs Blender** (`lib.py` : chemins de sortie, sprite + ombre portée, fenêtre de découpe, planches, tiges) : `lib.py` porte déjà le style ; y regrouper ce qui est dupliqué entre
      `belt.py`, `splitter.py`, `underground.py`, `inserter.py`, `pole.py` (caméra calée sur un original, planches,
      ombres, icônes à mipmaps). Chaque nouveau lot doit coûter un modèle, pas un pipeline.
- [x] **Générateur d'icônes commun** (`lib.save_icon`, utilisé par tous les générateurs sauf les convoyeurs, vus de dessus) : un rendu Blender à angle fixe pour les icônes (objets et entités), avec mipmaps.
      Sera utilisé par presque tous les lots.
- [x] **Reproductibilité** (`tools/build.py cartoon tous --verifier`, 10 min, 153 fichiers sur 153) : dépendances figées (`requirements.txt`, version de Blender/`bpy`), commande unique pour tout
      régénérer, test rapide qui vérifie qu'un générateur produit des fichiers aux bonnes tailles.

## 4. Étape 1 : valider l'existant en jeu

Avec le banc d'essai (vues rapprochées « detail-* » à la résolution du jeu, machines en marche, et captures animées
« anim-* » en GIF), vérifier ce qui n'a jamais été vu à l'écran et corriger :

- [x] Bras robotisés : orientations des plateformes, positions des pinces et mouvement identiques à l'original (5 bras, 4 directions)
- [x] Souterrains : capot du bon côté pour l'entrée et la sortie dans les 4 directions, objets cachés dessous
- [x] Animation des répartiteurs : animés dans les 4 directions et les 4 niveaux
- [x] Assembleurs 1 à 3 : animés en marche, ombres en place
- [x] Minerais : **corrigé**, les gisements formaient des bandes horizontales (tas trop plats et trop petits aux étapes
      moyennes, voir `FIELD_*` dans `ore.py`) ; ils sont maintenant continus comme l'original
- [x] Répartiteurs : la tête (barre fine) se perdait sur les convoyeurs ; **décidé** : bloc gris plus épais, chevrons
      à la couleur du niveau
- [x] Sols : **décidé** : masques de transition nets (`terrain/masks.py` : flou léger, seuil, anticrénelage ; partagés
      avec des sols de Space Age)
- [x] **Constat** (reporté au lot 2.8) : les décorations d'origine (touffes d'herbe réalistes) jurent fortement sur les sols en aplats
      (capture `monde-02`) ; le lot 2.8 « Décorations » est à avancer juste après les objets (2.1)
- [x] Revue de cohérence générale par Bastien (comparaisons dans `.cache/vitrine/comparaison/`) : validée

---

## 5. Étapes 2 à 6 : les lots

L'ordre suit **ce que voit le joueur** : d'abord les premières heures sur Nauvis, puis le milieu et la fin de partie,
puis l'interface, puis Space Age. Chaque étape se termine par une version publiable.

Technique indiquée : **B** = Blender (modèle 3D toon), **P** = procédural 2D (OpenCV/Pillow), **?** = à décider au cadrage.

### Étape 2 : le début de partie sur Nauvis → version 0.1 (première publication)

| Lot | Contenu | Tech. | Remarques |
|---|---|---|---|
| [x] 2.1 Objets sur les convoyeurs | Plaques, engrenage, câble, circuits, acier, briques, bois, plastique, soufre, batterie, packs de science... (30 icônes, `items.py`) | B | Vue à 45°, rotation libre ; vu en jeu (`detail-objets`) |
| [x] 2.2 Production de base | Four en pierre, foreuse à charbon, foreuse électrique (69 fichiers, animée, 4 directions) | B | Four (`furnace.py`, flammes en aplats), foreuse à charbon (`burner_drill.py`), foreuse électrique sèche et humide (`electric_drill.py`, calques comme l'original, fenêtres de fluide à la forme de l'original) ; vus en jeu (`detail-production`, `detail-foreuses-humides`). Laissés : halos et voyants (d'origine), poussières et fumées, épaves (lot 3.9), motif de zone de minage (étape 5) |
| [x] 2.3 Stockage | Coffres bois, fer, acier | B | `chests.py` : 9 fichiers (sprite, ombre, icône). Caisse unique, cadre, planches et nervures peints (pas de contour par planche) ; vus en jeu (`detail-stockage`). Laissés : restes (lot 3.9) |
| [x] 2.4 Énergie vapeur | Pompe côtière, chaudière, machine à vapeur | B | Chaudière (`boiler.py`, 14 fichiers, `detail-energie`), machine à vapeur (`steam_engine.py`, 5 fichiers, `detail-machines-vapeur`), pompe côtière (`offshore_pump.py`, 25 fichiers : planches animées, ombres, pieds, partie immergée, fluide et vitres en aplats, icône ; `detail-pompes-cotieres`). Laissés : halos de la chaudière, reflet de la pompe (technique), restes (lot 3.9) |
| [ ] 2.5 Tuyaux | Tuyau (28 variantes de raccord), tuyau souterrain, couvercles de tuyaux, tuyaux des assembleurs 2 et 3 | B | Vue de dessus (règle des objets au sol) |
| [ ] 2.6 Petits bâtiments | Laboratoire, radar, petite lampe | B | |
| [x] 2.7 Nature | Rochers, arbres (559 fichiers : ~15 espèces × variantes × feuillage), poissons | P | Arbres : 448 fichiers (`terrain/trees.py`, gros lobes teintés par le jeu). Gros rochers et poissons : 54 fichiers (`terrain/rocks.py`, blocs prismatiques) ; vus en jeu (`detail-arbres`, `detail-rochers`). Reflets dans l'eau : fichiers techniques, laissés d'origine |
| [x] 2.8 Décorations | Touffes d'herbe, buissons, cailloux, taches (669 fichiers, `terrain/decoratives.py`) | P | Une touffe sur cinq, contour teinté, taches à 60 %. Laissés aux autres lots : gros rochers (2.7), traces d'ennemis (3.8), sol nucléaire (4.5) |
| [ ] 2.9 Eau et falaises | Eau (profonde, peu profonde, verte, boue), falaises | P / B | Les falaises ont de nombreuses orientations |
| [ ] 2.10 Personnage | Inactif, course, minage, mort, avec et sans arme, 3 niveaux d'armure | B | Modèle articulé : nouveau savoir-faire (rig + animation) |
| [ ] 2.11 Chargeurs et lecteur de convoyeur | Chargeurs 1 à 3 + turbo, lecteur de convoyeur, paratonnerre | B | Restes de la synthèse |
| [ ] 2.12 Publication 0.1 | Vignette du mod, description, captures, `changelog.txt`, publication sur le portail des mods | — | Décider le nom public |

### Étape 3 : le milieu de partie sur Nauvis → version 0.2

| Lot | Contenu | Tech. |
|---|---|---|
| [ ] 3.1 Fours avancés | Four en acier, four électrique | B |
| [ ] 3.2 Pétrole | Puits de pétrole, raffinerie, usine chimique, réservoir, pompe (111 fichiers), gisement de pétrole | B |
| [ ] 3.3 Circuits | Combinateurs, interrupteur, haut-parleur, panneau d'affichage, connecteurs de circuit (16 fichiers, sur beaucoup d'entités) | B |
| [ ] 3.4 Énergie | Panneau solaire, accumulateur | B |
| [ ] 3.5 Trains | Rails (droits, courbes, demi-diagonales), signaux, gare, locomotive, wagons (36 orientations chacun) | B |
| [ ] 3.6 Logistique | Roboport, robots de construction et de logistique, coffres logistiques (5 couleurs) | B |
| [ ] 3.7 Défense | Murs, portes, tourelles (mitrailleuse, laser, lance-flammes, artillerie), mines | B |
| [ ] 3.8 Ennemis | Petits à géants : mordeurs, cracheurs, vers, nids (~280 fichiers, 16 directions, nombreuses animations) | B | 
| [ ] 3.9 Effets | Explosions, fumées, feu, étincelles, particules, traces de brûlure, restes (corpses) | P ? |
| [ ] 3.10 Modules et balise | Balise, modules (icônes) | B |

> Le lot 3.8 est le plus risqué de tout le mod (créatures organiques, articulées, très nombreuses images). Il fera
> l'objet d'un essai de faisabilité avant d'être engagé ; il peut aussi être repoussé après l'étape 4.

### Étape 4 : la fin de partie sur Nauvis → version 0.3

| Lot | Contenu | Tech. |
|---|---|---|
| [ ] 4.1 Nucléaire | Réacteur, échangeur de chaleur, tuyau de chaleur (92 fichiers), turbine, centrifugeuse | B |
| [ ] 4.2 Véhicules | Voiture, char, araignée (spidertron) | B |
| [ ] 4.3 Silo à fusée | Silo, fusée, capsule, aire d'atterrissage (cargo) | B |
| [ ] 4.4 Robots de combat et capsules | Défenseur, destructeur, distracteur, grenades, capsules | B |
| [ ] 4.5 Divers | Site du crash (vaisseau, coffres), sol nucléaire, béton et dalles (sols construits), remblai | B / P |

### Étape 5 : l'interface → version 0.4

| Lot | Contenu | Tech. |
|---|---|---|
| [ ] 5.1 Icônes restantes | Toutes les icônes d'objets, de fluides, de recettes encore d'origine (580 dans base) | B (icônes des entités déjà modélisées : quasi gratuites) |
| [ ] 5.2 Technologies | 132 images de technologies (256 px avec mipmaps) | B |
| [ ] 5.3 Groupes, succès, équipements | Onglets d'objets, succès, équipements de l'armure | B / P |
| [ ] 5.4 GUI (`core`) | Feuille `gui-new.png`, curseurs, emplacements, barres | ? | À cadrer : le plus délicat (une seule grande planche, découpée par le jeu) ; décider si on y touche |

### Étape 6 : Space Age → version 1.x

Un sous-plan par planète, détaillé le moment venu. Ordre proposé : celui du joueur.

| Lot | Contenu |
|---|---|
| [ ] 6.1 Commun Space Age | Bras en vrac de pile (stack inserter), grande foreuse, concasseur, icônes et technologies Space Age |
| [ ] 6.2 Plateforme spatiale | Sols de plateforme, propulseur, collecteur d'astéroïdes, astéroïdes (378 fichiers), tourelles fusée et électrique |
| [ ] 6.3 Vulcanus | Sols, décorations, fonderie, tungstène, geysers, démolisseurs |
| [ ] 6.4 Fulgora | Sols, ruines, usine électromagnétique, paratonnerre, collecteur de foudre, ferraille, foudre |
| [ ] 6.5 Gleba | Sols, plantes (109 fichiers), tour agricole, biochambre, biolabo, nids et ennemis de Gleba |
| [ ] 6.6 Aquilo | Sols, glace, usine cryogénique, réacteur et générateur à fusion, tour de chauffage, aspect « gelé » des entités (62 fichiers) |
| [ ] 6.7 Rails surélevés et qualité | Jeux `elevated-rails` et `quality` |

---

## 6. Risques et décisions à prendre

| Sujet | Question | Quand |
|---|---|---|
| Créatures et personnage | Blender sait-il produire des animations organiques lisibles en style cartoon à un coût raisonnable ? | Essai de faisabilité au lot 2.10 |
| Arbres et décorations | Un modèle par espèce ou un générateur paramétré ? Les feuilles se prêtent mal aux contours nets. | Cadrage du lot 2.7 |
| Transitions de sol | Garder les masques d'origine (fondus doux) ou les refaire nets ? | Étape 1 |
| GUI | Refaire l'interface ou la laisser d'origine ? | Cadrage du lot 5.4 |
| Poids du mod | Le jeu d'origine pèse 2,4 Go de graphismes ; à 2 % fait, le mod pèse déjà 37 Mo. Prévoir l'optimisation des PNG (`oxipng`) et suivre la taille à chaque version. | À chaque publication |
| Compatibilité | Autres mods qui réutilisent les fichiers de base (ils hériteront du style, c'est voulu) ; mods qui modifient les mêmes entités. | Avant la 0.1 |
| Licence | Nos sprites sont des créations (rendus de nos modèles), pas des retouches des fichiers de Wube : à rappeler dans la description. Choisir une licence pour le code et les images. | Avant la 0.1 |
| Mod pixel | Les deux mods partagent les outils (`tools/`). Toute évolution de l'outillage doit rester compatible avec le mod pixel. | En continu |

---

## 7. Résumé des jalons

| Version | Contenu | Couverture visée |
|---|---|---|
| — | Étape 0 (outillage) et étape 1 (validation de l'existant) | — |
| 0.1 | Début de partie sur Nauvis : tout ce qu'on voit les premières heures | ~25 % de `base` |
| 0.2 | Milieu de partie (pétrole, trains, robots, défense, ennemis) | ~65 % de `base` |
| 0.3 | Fin de partie (nucléaire, véhicules, fusée) | ~85 % de `base` |
| 0.4 | Interface (icônes, technologies, GUI) | `base` complet |
| 1.0 | Nauvis entièrement cartoon, mod stable et documenté | |
| 1.x | Space Age, planète par planète | |

Les pourcentages seront recalculés par l'inventaire automatique de l'étape 0 (ils excluront les masques et cartes d'effets).
