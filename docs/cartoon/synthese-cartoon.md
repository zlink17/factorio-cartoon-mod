# Mod Cartoon : synthèse du travail

État au 11 octobre 2026 (étape 2 commencée : lots 2.1 à 2.9 faits). Ce document résume ce qui a été fait, comment, ce qu'on a appris en
chemin et ce qui reste. Le guide de style de référence est [`cartoon/STYLE.md`](../../cartoon/STYLE.md) ; le mode d'emploi
des outils est dans [`cartoon/README.md`](../../cartoon/README.md) ; la feuille de route est dans [`plan.md`](plan.md).

## 0. Reprendre le travail (nouvelle session)

1. Lire [`plan.md`](plan.md) : méthode (un lot = cadrage, prototype, production, contrôle, vérification en jeu, commit),
   étapes et cases cochées. **Étapes 0 (outillage) et 1 (validation en jeu de l'existant) terminées ; lots 2.1
   « Objets sur les convoyeurs », 2.2 « Production de base », 2.3 « Stockage », 2.4 « Énergie vapeur », 2.5 « Tuyaux »,
   2.6 « Petits bâtiments », 2.7 « Nature », 2.8 « Décorations » et 2.9 « Eau et falaises » faits.**
2. **Prochaine action : lot 2.10 Personnage**, puis l'ordre du plan (2.11 Chargeurs, 2.12 Publication).
   **Fait le 11 octobre (hors lot) : tri des décorations par profondeur.** Herbes, buissons, rameaux, cailloux et
   souche de Nauvis passent dans deux couches triées, sous les convoyeurs et les entités : herbes dans
   « remnants », éléments uniques (cailloux, buissons...) dans « floor », au-dessus (`cartoon/mod/sorted_decoratives.lua`).
   Chaque image est recalée pour que le pied du dessin tombe sur la position de la décoration
   (`tools/decorative_feet.py`, lancé par `build.py`, écrit `cartoon/mod/feet.lua` ; appliqué dans
   `data-final-fixes.lua`). Règle voulue par Bastien : ce qui a le pied plus bas à l'écran passe devant. Scènes de
   contrôle : `detail-superpositions`, `detail-melange` (arbres, rochers, convoyeur) et `monde-rocher` du banc.
   Limites connues : une touffe devant un caillou ou un rocher passe dessous (peu visible) ; pieds à égalité =
   ordre arbitraire ; performance à surveiller sur une grande partie.
   **Gisements dégagés (11 octobre)** : ces couches passent au-dessus des minerais et les cachaient ; le mod retire
   herbes, buissons et cailloux des cases de minerai à la génération de la carte (`cartoon/mod/control.lua`, une fois
   sur une partie existante à l'ajout ou la mise à jour du mod, et commande `/cartoon-minerais`). Les taches au sol restent.
3. Cadrage d'un lot : `.venv/bin/python tools/inventory.py cartoon liste icons/` (fichiers, tailles, prototypes).
4. Production : ajouter le générateur dans `cartoon/lots.py`, puis `.venv/bin/python tools/build.py cartoon <lot>`.
5. Vérification : `.venv/bin/python tools/check_mod.py cartoon --jeu`, puis `.venv/bin/python tools/bench.py cartoon
   --sans-origine` (captures et comparaisons dans `.cache/vitrine/comparaison/`, ouvre une fenêtre Factorio ~40 s).
6. Avant de commiter un lot : `.venv/bin/python tools/inventory.py cartoon` (couverture), cocher le lot dans le plan.
7. Après le commit : `tools/install_mod.sh cartoon` met à jour le mod dans le jeu de Bastien (accord permanent).
   Le banc d'essai et `check_mod.py --jeu` utilisent une instance isolée et ne touchent pas à son jeu.
8. **Galerie** : chaque lot fini (ou avancé) ajoute sa zone au scénario « galerie » (`cartoon-galerie/mod/`,
   mod `factorio-cartoon-galerie`, fonction `build_*` + entrée dans `ZONES` de `scenarios/galerie/control.lua`).
   Contrôle : `.venv/bin/python tools/galerie.py` (captures par zone dans `.cache/galerie/`, ~1 min). Bastien la
   lance dans son jeu par Jeu solo > Scénarios ; désactiver le mod cartoon donne la même carte d'origine.

Règles de travail avec Bastien : prévenir **avant** d'installer une application ou une dépendance sur sa machine ;
solutions gratuites uniquement ; cohérence du style prioritaire ; les choix de style sont les siens (proposer, puis
demander) ; messages de commit en français.

`.cache/` (non versionné) contient le dump des prototypes, les rendus de `build.py` et les captures du banc : tout se
régénère (`tools/factorio.py` refait le dump à chaque nouvelle version du jeu).

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
              underground.py, splitter.py, pole.py, ore.py, items.py, furnace.py, burner_drill.py, electric_drill.py,
              chests.py, boiler.py, steam_engine.py, offshore_pump.py, pipe.py, lamp.py, lab.py, radar.py
  terrain/    ground.py (sols de Nauvis), masks.py (masques de transition nets), decoratives.py, trees.py,
              rocks.py (gros rochers, poissons), water.py (eaux, rives, bruit et
              cartes d'effet du shader de l'eau), cliffs.py (falaises)
  lots.py     les lots et les commandes qui les produisent (lu par tools/build.py)
  ai/         ComfyUI (comfy_batch.py, workflow, post-traitement) : essai, non retenu
  STYLE.md    guide de style
cartoon-epure/mod/   sous-mod facultatif « terrain épuré » (voir plus bas)
cartoon-galerie/mod/ scénario « galerie » : une zone par lot, machines en marche, pour vérifier en jeu
tools/
  factorio.py       pilote une instance isolée de Factorio depuis WSL (dump des prototypes, lancement, arrêt)
  inventory.py      inventaire des 8 246 images du jeu, rôle et prototypes ; couverture (docs/cartoon/couverture.md)
  build.py          produit un lot, contrôle, installe dans le mod ; --verifier : test de reproductibilité
  check_mod.py      contrôle du mod (tailles, alpha, ombres vides, manifeste) ; --jeu : test de chargement
  bench.py, bench/  banc d'essai en jeu : scénario « vitrine », captures avec et sans le mod, comparaisons, GIF
  build_manifest.py, install_mod.sh   manifeste ; installation dans le Factorio du joueur
docs/cartoon/ plan.md (feuille de route), synthese-cartoon.md (ce fichier), couverture.md (généré)
```

Principe commun : un générateur écrit l'arborescence de `graphics/overrides` (`<jeu>/entity/<nom>/...`, `<jeu>/icons/...`),
**au même chemin que l'original** ; `tools/build.py` le lance dans `.cache/build/`, contrôle et copie dans
`cartoon/mod/graphics/overrides/`, puis régénère `manifest.lua` ; `data-final-fixes.lua` remplace dans tous les
prototypes toute chaîne listée dans le manifeste. Ce qui n'est pas refait reste d'origine.
Le mod déclare `! factorio-pixel-mod` (incompatible avec le mod pixel du même repo) et `? space-age` (dépendance optionnelle,
pour l'ordre de chargement).

**Sous-mod « terrain épuré »** (`cartoon-epure/mod/`, `factorio-cartoon-epure`, essai du 11 octobre) : à activer à côté
du mod cartoon pour comparer le terrain avec ou sans décorations. Il multiplie la probabilité de génération des
décorations de Nauvis par une densité réglable par famille (paramètres de démarrage, en %) : herbes, plantes et
cailloux à 0 %, taches au sol à 30 %. Arbres, gros rochers et poissons ne changent pas. Seules les nouvelles zones de
carte sont concernées ; `/cartoon-epure` refait les décorations d'une partie existante (supprime puis régénère :
`regenerate_decorative` seul ajoute sans retirer). Installation : `tools/install_mod.sh cartoon-epure`. Pas de
décision de style prise : on garde les deux pour comparer. Les sols cartoon (`ground.py`) dessinent aussi de petites
touffes ton sur ton dans la texture.

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

## 5. Ce qui est fait (1 578 fichiers remplacés, tous vus en jeu)

| Famille | Contenu | Générateur |
|---|---|---|
| Assembleurs 1, 2, 3 | Planches animées de 32 images, ombres (animées pour 2 et 3), icônes. Niveau 2 : bras articulé ; niveau 3 : deux bras et deux pistons. | `assembler.py`, `animate.py`, `assembler_extras.py` |
| Convoyeurs | Jaune, rouge, bleu et turbo (Space Age) : 20 rangées (droits, 8 courbes, bouts de ligne) × 16, 32 ou 64 images ; stries ton sur ton et flèches colorées comme l'original ; icônes. | `belt.py` |
| Souterrains | Trois niveaux + turbo : capot courbé le long du flux, bouche sombre à linteau, entrée et sortie différentes. | `underground.py` |
| Répartiteurs | Trois niveaux + turbo : tête de 2 cases animée, bloc gris portant deux chevrons à la couleur du niveau (chariot d'une voie à l'autre, pignons), moitiés haute et basse pour l'est et l'ouest. | `splitter.py` |
| Bras robotisés | À charbon, de base, à longue portée, rapide, en vrac : plateformes (4 orientations), mains, ombres, icônes. | `inserter.py` |
| Pylônes et câbles | Poteau, poteau moyen, pylône, sous-station (4 variantes chacun, ombres, icônes) ; câbles cuivre, rouge, vert, ombre, surbrillance. | `pole.py` |
| Minerais | Fer, cuivre, charbon, pierre, uranium : gisements (8 étapes × 8 variantes, tas larges qui se chevauchent : gisement continu), calque lumineux de l'uranium, 20 icônes (aussi les objets sur les convoyeurs). | `ore.py` |
| Objets intermédiaires | 30 icônes (aussi les objets sur les convoyeurs) : plaques, poutre, engrenage, câble, tige, 3 circuits, brique, bois, plastique, soufre, batterie, moteurs, cadre de robot, structure légère, combustibles, explosifs, uranium 235 et 238, 7 packs de science. Vue à 45° et rotation libre (plaques de fer et de cuivre en miroir, comme l'original). | `items.py` |
| Décorations de Nauvis | 669 fichiers, 37 familles : touffes et buissons (une touffe sur cinq, contour teinté), rameaux, agaves, crotons, buissons touffus en lobes (roux, rosé, blanc), touffes de paille, petits palmiers (garballo), cailloux en facettes, souches, taches au sol à 60 %. Procédural 2D, placé d'après le canal alpha de l'original. | `terrain/decoratives.py` |
| Arbres de Nauvis | 9 espèces (troncs, feuillage en 3 états, normales, souches) et 5 arbres morts ou secs : 448 fichiers. Feuillage en gros lobes ronds (sapin : étages pointus) en tons neutres, teinté par le jeu ; troncs en aplat à trois tons tirés de l'original ; ombres d'origine. | `terrain/trees.py` |
| Gros rochers et poissons | `big-rock` (20), `huge-rock` (16), `big-sand-rock` (16) : blocs prismatiques posés sur la silhouette de l'original (colonnes hexagonales ; grès en gros blocs olive), teintes sombres proches de l'original. Poissons : silhouette nette sous l'eau. | `terrain/rocks.py` |
| Four en pierre | Pyramide tronquée de briques ocre, cheminée et bouche en pierre grise, ombre, icône ; flammes en aplats (48 images). | `blender/furnace.py` |
| Foreuse à charbon | 4 directions × 32 images (engrenages, vrille, piston), ombres, icône ; pieds arqués ajustés sur l'original. | `blender/burner_drill.py` |
| Foreuse électrique | Cadres des 4 directions, têtes verticale et horizontale (30 images, ombres 21), pièces avant, tambours de sortie, terre remuée, icône ; variante humide (réservoirs à hublot, tuyaux, fenêtres de fluide). | `blender/electric_drill.py` |
| Coffres | Bois, fer, acier : sprite, ombre, icône. Caisse haute et peu profonde (silhouette de l'original) ; cadre, planches et nervures peints sur les faces ; couvercle à pans coupés et loquet (fer), coins et poignée (acier). | `blender/chests.py` |
| Chaudière | 4 directions, ombres, flammes dans les fentes de la grille (64 images), patch de l'est, icône. | `blender/boiler.py` |
| Machine à vapeur | Planches horizontale et verticale (32 images : volant, engrenages, crosse et bielle), ombres, icône. | `blender/steam_engine.py` |
| Pompe côtière | 4 directions × 32 images (pistons dans les fenêtres des cylindres), ombres, pieds, bas du réservoir sous l'eau, eau des fenêtres et vitres en aplats (forme de l'original), icône. | `blender/offshore_pump.py` |
| Tuyaux | 18 formes (droits, coudes, T, croix, bouts, fenêtres) et tuyau isolé, ombre incluse ; fonds des fenêtres ; souterrains (4) ; couvercles et ombres ; raccords des assembleurs 2 et 3 ; icônes. | `blender/pipe.py` |
| Petits bâtiments | Petite lampe (sprite, ombre) ; laboratoire (33 images, lueur bleue qui vacille, ombre, intégration) ; radar (64 orientations de l'antenne, ombres, intégration) ; 3 icônes. | `blender/lamp.py`, `lab.py`, `radar.py` |
| Eau et rives | 6 eaux en aplats (vaguelettes, taches de fond pour l'eau peu profonde et la vase) ; bruit du shader de l'eau lissé (grandes taches nettes) et cartes d'effet des rives en paliers ; rives de l'herbe, des terres et du sable : masques nets recalés, berge de terre cernée sous les bords sud, plage basse pour le sable ; bords d'eau peu profonde nets. | `terrain/water.py` |
| Falaises de Nauvis | 4 planches × 2 calques (haut, pied) : colonnes prismatiques hautes sur la silhouette de l'original, halo du pied en aplat ; ombres d'origine. | `terrain/cliffs.py` |
| Sols de Nauvis | 19 planches (herbe, terre, sable, désert rouge) en aplats avec petits détails ; masques de transition 1, 3 et 4 à bords nets (partagés avec des sols de Space Age). | `terrain/ground.py`, `terrain/masks.py` |

## 6. Ce qu'on a appris (à ne pas redécouvrir)

- **Une planche de mauvaise taille empêche Factorio de démarrer** (« sprite rectangle is outside the actual sprite size »).
  Le cas qui nous a piégés : le répartiteur express a un côté ouest de 94 px au lieu de 90. `tools/check_mod.py` compare chaque
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
  ombres des pylônes sans erreur visible : le contrôle d'ombres vides est maintenant dans `check_mod.py`.
- **Contraste** : des sprites bruns sur un sol brun disparaissent ; il faut des teintes claires et de vraies ombres.
- **Le sol** est composé de planches de textures de 64 px par case (variantes de 1, 2, 4, 8 cases) mélangées par des masques ; on
  peut remplacer les textures sans toucher aux masques, à condition qu'aucun détail ne touche le bord d'une cellule.
- **Les variantes sont souvent des listes** (`filenames = {...}` : arbres, rochers, décorations, 2 179 références) et
  certaines clés sont rares (`small_icon`, `mask_spritesheet`...) : `data-final-fixes.lua` remplace donc **toute chaîne**
  listée dans le manifeste, quelle que soit sa clé. `tools/check_mod.py --jeu` vérifie en jeu qu'il n'en manque aucune.
- **`factorio.exe --dump-data`** (lancé depuis WSL dans une instance isolée, `tools/factorio.py`) donne tous les prototypes
  après chargement : c'est la source de l'inventaire et du test de chargement. Il tourne en 3 s, même jeu ouvert.
- **Lancer le jeu depuis WSL** : Steam relance lui-même `factorio.exe` (le processus lancé se termine tout de suite) ;
  on reconnaît l'instance isolée à sa ligne de commande (`tools/factorio.py`, `running()`/`stop()`). Un mod présent
  dans le dossier de mods mais absent de `mod-list.json` est **activé** par défaut : il faut le désactiver explicitement.
- **Captures en jeu** : `game.take_screenshot` sur une surface dédiée, sans joueur, puis
  `game.set_wait_for_screenshots_to_finish()` ; un fichier « fini.txt » écrit au tick suivant signale la fin.
- **Un sprite du mod peut ne plus correspondre à son générateur** (code retouché sans relancer le rendu) : c'était le
  cas de la planche de l'assembleur 1 (teinte des panneaux avant). `tools/build.py cartoon tous --verifier` relance
  tout de zéro et signale ces écarts ; les rendus Cycles sont reproductibles à ±3 près par canal.
- **Sans dialogue Steam** : lancé hors de Steam, Factorio se fait relancer par Steam, qui demande de confirmer les
  arguments. Il faut un `steam_appid.txt` (427520) **dans le dossier courant** du processus (donc lancer depuis
  `bin/x64`) et les variables `SteamAppId`/`SteamGameId` (passées à Windows par `WSLENV`) : `tools/factorio.py`.
- **Surface de test sous Space Age** : `game.create_surface` sans réglages mélange toutes les planètes (on obtient
  Gleba) ; copier `game.surfaces.nauvis.map_gen_settings`.
- **Icônes d'objets : vue des bâtiments (30°) illisible** pour les objets plats ou hauts (plaques sans épaisseur,
  flacon en abat-jour) : ils sont vus à 45° (`PITCH_ITEM_DEG`). Les plaques de fer et de cuivre de l'original sont
  tournées en sens inverse (coin du haut à gauche pour le fer, à droite pour le cuivre) : voulu par les concepteurs
  pour les distinguer, à conserver (rotation calée par mesure des coins : ±35°).
- **Couleur d'une face = son orientation** (`lib.mat`) : un bout de rondin tourné de côté prend le ton « côté » (×0,62)
  et se confond avec l'écorce ; orienter l'objet pour que les faces à montrer soient vers l'avant ou le haut.
- **Décorations en aplats : la densité d'origine ne marche pas.** L'original couvre l'herbe de touffes
  semi-transparentes de la couleur du sol ; redessinées en aplats contournés, elles font un tapis qui envahit la
  carte. D'où : une touffe sur cinq, contour teinté, taches au sol semi-transparentes. Se juger **en jeu** (vue
  « monde »), pas sur un sprite isolé : isolées, toutes les versions paraissaient correctes.
- **Les décorations ont leur ombre dans le sprite** (pixels presque noirs, peu opaques) : pour lire la forme de la
  plante dans l'original, on écarte les pixels de valeur < 35. Les gros rochers (`big-rock`, `huge-rock`,
  `big-sand-rock`) ne sont pas des décorations mais des entités (`simple-entity`) : lot 2.7.
- **Contour d'un élément fait de brins fins** : un trait par brin noie le remplissage ; on contourne la silhouette
  de l'ensemble (dilatation du masque).
- **Le feuillage des arbres est teinté par le jeu** (`colors` du prototype, une couleur tirée au hasard par arbre,
  multipliée à la texture) : on le dessine en tons neutres, la variété de couleurs vient gratuitement. Les variantes
  « -red », « -brown » partagent les fichiers de l'espèce. Les cartes de normales (`*-normal.png`) éclairent le
  feuillage : on les remplace par des normales plates sous notre feuillage (recalées : cadre et décalage différents).
- **Plusieurs sessions Claude peuvent travailler en même temps** sur le repo et sur l'instance isolée de Factorio
  (`ListAgents`) : deux bancs simultanés se percutent (fichier introuvable, journal verrouillé). Règle convenue : un
  seul banc ou build à la fois, demander avant d'en lancer un, chacun commite ses propres fichiers.
- **Superpositions des décorations** : la couche « decorative » n'est pas triée par profondeur (une touffe derrière
  un caillou peut passer dessus, ce qui ne se voyait pas avec les textures floues d'origine) ; la couche « object »
  est triée par **position** de la décoration, pas par le bas de l'image. D'où le recalage des images sur leur pied
  (`feet.lua`). **Mais dans « object », les décorations ne sont triées qu'entre elles** et dessinées après toutes
  les entités : touffes et cailloux par-dessus les feuillages et les gros rochers (vu dans la partie de Bastien).
  « lower-object » est triée et sous les entités, mais au-dessus des convoyeurs (touffes sur les convoyeurs).
  **« remnants » et « floor » sont triées, sous les convoyeurs, les objets au sol, les entités et leurs ombres** :
  c'est là qu'elles vont. Une image d'herbe à plusieurs touffes étant triée d'un bloc (sur sa touffe la plus
  basse), ses autres touffes passaient sur les cailloux : les herbes vont dans « remnants », sous « floor » où sont
  les éléments uniques. (Essayés et écartés : une touffe par image, ou touffes regroupées en bouquet : les herbes
  « carpet » ont jusqu'à 15 touffes par image, la prairie se vide.) Curiosité : dans « object » et « lower-object »,
  le générateur de carte ne pose pas de décorations sous les entités ; dans les autres couches, si (comme à
  l'origine) ; elles y sont cachées. Ajouter `doodad` au masque de collision des rochers n'y change rien. Le recalage doit se faire **avant** `walk(data.raw)` dans `data-final-fixes.lua` : après, les chemins
  pointent vers le mod et ne correspondent plus aux clés de `feet.lua`.
- **Rochers : redessiner l'éclairage de l'original ne donne pas un rocher.** Facettes de Voronoï ou zones de
  lumière tirées en trois tons donnent des taches de camouflage ; il faut construire des volumes (blocs
  prismatiques à dessus clair et flanc droit sombre). Le corps d'un gros rocher se lit à **alpha > 200** (son ombre
  intégrée est à ~140), pas au seuil de valeur des décorations (< 35), qui perd ses faces sombres.
- **Projection des bâtiments** : la caméra est à 30° de la **verticale** ; à 64 px par case, une longueur au sol
  (axe y) s'affiche à 55 px (× cos 30°), une hauteur à 32 px (× sin 30°). Les sprites de Wube ne suivent pas
  exactement une géométrie simple (le four est plus étroit à l'arrière) : on ajuste les dimensions du modèle par
  recouvrement de silhouette avec l'original (descente de coordonnées, quelques dizaines de rendus sans contour).
- **Petits motifs (briques, rivets) : pas en relief.** Chaque arête vive reçoit un contour Freestyle, qui noie les
  petites pièces ; peindre le motif par une texture procédurale (nœud « Brick Texture ») sur une face plate.
- **Tourner un modèle par direction** : appliquer la rotation à `matrix_world` **après**
  `bpy.context.view_layer.update()`, sinon le dernier objet créé (matrice pas encore calculée) perd son échelle.
  Les engrenages de `lib.gear` sont horizontaux : les créer à l'origine puis régler `location`/`rotation_euler`.
- **Pièces fines (pieds, vrilles)** : un maillage continu (poutre balayée le long d'une courbe, ruban
  hélicoïdal) plutôt qu'une suite de cylindres, sinon chaque raccord reçoit un contour.
- **Entités en calques (foreuse électrique)** : le nord et le sud partagent le même fichier de tête, l'est et
  l'ouest aussi ; le jeu fait glisser la tête (`shift_animation_waypoints`), on la rend donc à l'origine. Les
  fichiers « -front » redessinent par-dessus la tête les pièces du cadre qui sont devant elle : on les obtient en
  ne gardant, après rotation, que les objets du cadre entièrement devant (y < -0,75).
- **Fenêtres de fluide (foreuse humide)** : leurs cadres sont serrés au pixel près autour des hublots de
  l'original, et leurs positions ne suivent pas une rotation propre d'une direction à l'autre. On garde la forme
  exacte de l'original en aplats (verre sombre, fond et reflets que le jeu teinte) et on place nos réservoirs
  direction par direction sous ces hublots (position 3D déduite de la position à l'écran) ; la pièce avant est
  percée aux hublots, car le jeu dessine les fenêtres avant elle.
- **Petits objets à motifs (coffres)** : un cadre fait de poutres séparées reçoit un contour par poutre et devient
  un fil de fer à 64 px. Une seule caisse, avec un matériau par face (`chests.paint`) et le motif peint en
  coordonnées du monde (`chests.mat_face` : bandes, cadres emboîtés) : un seul contour, lisible.
- **Coffres : la silhouette de l'original ne suit pas un cube** : face avant de 34 px et dessus de 35 px donnent
  une caisse de 1,06 case de haut sur 0,63 de profondeur, avancée de 0,24 case dans sa case (les trois coffres).
- **Chaudière : l'original est dessiné plus bas que notre projection** (comme les coffres, avancés dans leur
  case) : `down` décale la caméra (0,33 case vers le bas de l'écran), ajusté avec les dimensions. L'ajustement
  par recouvrement doit **pénaliser ce qui sort du cadre** de l'original (coupé net en jeu) et être **borné** :
  libre, il fond tambour et réservoirs en un seul cylindre qui recouvre mieux mais ne ressemble plus à rien.
- **Roues vues de face : les incliner vers la caméra.** Avec la vue à 30°, une roue debout face à l'avant
  (volant de la machine à vapeur) est écrasée de moitié en hauteur et se perd dans le plateau ; l'original les
  montre presque rondes. `steam_engine.face_camera` incline la pièce de 30° vers l'avant **dans le repère du
  monde** (sinon, une fois le modèle tourné pour l'autre orientation, elle fait face au côté et s'aplatit).
- **Ajustement borné (machine à vapeur)** : libre, il grossit cylindres et châssis jusqu'à cacher le mécanisme,
  qui fait la moitié basse de l'original. Bornes dans `BOUNDS` ; le mécanisme suit la position des cylindres.
- **Canevas de rendu** : il doit contenir aussi le cadre de l'ombre (décalé vers la droite) : l'ombre horizontale
  de la machine à vapeur (508 px, décalée de 96) sortait d'un canevas de 576 px ; `build.py` a refusé le fichier
  (taille différente de l'original).
- **Flammes de la chaudière** : le jeu ne les dessine que dans un petit cadre fixe par direction, et la grille de
  l'original n'est pas au même endroit du tambour d'une direction à l'autre. `boiler.grate_place` calcule, par
  direction, où poser la grille pour qu'elle se projette au centre de ce cadre ; les flammes sont les pixels des
  fentes repérés dans notre rendu. Une platine posée sur un cylindre : `rot_x = angle - 90` (face selon le rayon).
- **Pompe côtière en calques** : le jeu dessine la pompe en six calques par direction : pieds (couche du sol,
  sous tout), bas du réservoir (`underwater_pictures`, sous la surface de l'eau), planche animée et ombre, puis
  l'eau des fenêtres (`fluid_animation`, teintée de la couleur du fluide) et les reflets des vitres, **à des cadres
  fixes**. Comme pour la foreuse humide, les fenêtres de l'original ne sont pas au même endroit d'une direction à
  l'autre : `offshore_pump.window_span` lit l'étendue de l'eau de l'original (union des 32 images) et place, par
  direction, la fenêtre et la course du piston dessous ; les gaines entrent par les bouts des cylindres pour ne pas
  la couvrir. L'ajustement borné (rayons des cylindres, du réservoir et de la bride en butée) donne 0,83 de
  recouvrement ; le rendu complet prend ~1 min.
- **Gaine annelée sans contour par anneau** (`offshore_pump.hose`) : un seul tube (courbe convertie en maillage),
  chaque face prend l'une de deux couleurs selon sa distance le long du tracé.
- **Banc : pompe côtière qui tourne** : sans sortie, elle s'arrête ; un tuyau infini qui retire l'eau (« exactly »
  0) sur sa sortie (case voisine côté terre) la fait tourner.
- **Tuyaux : une case = une image de 128 px, ombre comprise** (pas de fichier d'ombre, sauf pour les couvercles).
  Les brides de l'original sont dans la case, contre ses bords : deux cases voisines forment un raccord à deux
  brides. Le bout d'un tube et la face de sa bride au même plan scintillent (moitié tube, moitié bride) : la bride
  dépasse d'un cheveu (0,015 case). Un bout fait de deux tubes accolés laisse un trait de contour : un seul tube
  jusqu'au bouchon. L'ajustement donne des brides de 0,065 case, réduites à un trait : imposé 0,1.
- **Images de tuyau par connexions** : le jeu choisit la forme selon les voisins raccordés ; une longue ligne
  alterne droits et droits à fenêtre (le fluide, dessiné par le jeu dans `*_window_bounding_box`, se voit au
  travers du verre translucide). Les **couvercles** se dessinent sur la case voisine d'un raccord libre ; ils ne
  montrent que le bouchon, contre le bord partagé. Les **raccords des assembleurs** (`pipe_picture`) n'existent
  qu'avec une recette à fluide (`fluid_boxes_off_when_no_fluid_recipe`) ; une machine ne s'oriente qu'avec une
  telle recette : `set_recipe` d'abord (recette débloquée : `force.recipes[r].enabled`), puis `direction`. Le
  raccord nord sort de la paroi arrière, que la machine cache : sans cadre, le tube s'enfonce vers la machine et le
  cadre de l'image le coupe (remarque de Bastien : un cadre et un bout de tube plat y faisaient un bloc posé devant).
- **Souterrains** : l'image porte le nom du côté du raccord en surface (`up` = raccord au nord) ; la distance
  parcourue avant de plonger varie selon la direction dans l'original (`pipe.UNDERGROUND`).
- **Motifs peints le long des arêtes** : le nœud « Wireframe » (taille en unités du monde) donne la distance aux
  arêtes des triangles ; mélangé à la couleur de `lib.mat`, il dessine les montants du dôme du laboratoire sans
  créer d'objets (donc sans contour par montant).
- **Laboratoire** : l'image 0 sert aussi au laboratoire à l'arrêt (`off_animation`) : elle doit être éteinte. La
  lueur de l'original vacille sans régularité : on reprend son intensité image par image (`lab.GLOW`).
- **Radar : l'ajustement automatique échoue** sur un modèle à beaucoup de pièces (il grossit la plateforme et
  rapetisse l'antenne). Mesurer à la main sur l'original (hauteur des pieds, de la tourelle, de l'antenne dans
  deux orientations opposées : l'écart donne la distance à l'axe) a donné de meilleures proportions. L'antenne de
  l'original est presque sur l'axe et très haut (centre vers 2,9 cases) ; image 0 au nord, sens horaire.
- **Tailles des fichiers ≠ prototype** : l'ombre du laboratoire fait 243 px de large, le prototype en déclare 242 ;
  `build.py` compare au fichier, il faut donc produire 243.
- **Banc : laboratoires à l'arrêt** (toutes les recherches y sont faites) ; la galerie met une recherche infinie
  en file (`research_queue`) et des packs dans un laboratoire. `take_screenshot{daytime=0.5}` sur une surface
  `always_day` reste de jour.
- **Banc** : une chaudière ne brûle en continu que si elle a de l'eau et peut évacuer sa vapeur : tuyaux infinis
  (`set_infinity_pipe_filter`, eau « at-least », vapeur « exactly » 0).
- **Eau profonde : c'est le shader qui la peint**, pas la texture du sol. Les tuiles d'eau ont `effect = "water"`
  (prototype `tile-effect`) : couleur opaque `effect_color` et bruit animé `terrain/effects/water-noise.png` ; nos
  vaguelettes ne se voient que sur l'eau peu profonde et la vase (couleur d'effet à 12 % d'opacité). Lisser ce
  bruit (flou raccordable, même moyenne et même écart-type) suffit à rendre l'eau cartoon : les seuils du shader
  découpent de grandes taches nettes. Les cartes d'effet des rives (`effect-maps/water-*-mask.png`, rouge et bleu)
  pilotent écume et assombrissement du bord : quantifiées en trois paliers, ce sont des bandes franches.
- **Planche de rives** (`water-transitions/<sol>.png`, 3200 × 2368) : overlay (x = 0), fond (x = 1088, inutilisé si
  `background_enabled = false`), masque (x = 2176, blanc = terre, cellules de 64). Bandes : coins intérieurs (y = 0),
  extérieurs (576), côtés (1152), U (1728), O (2304), quatre orientations par bande. **La hauteur des cellules
  d'overlay dépend de `tile_height` du prototype** : 2 cases (rangées tous les 128 px) pour l'herbe et les terres,
  1 case (tous les 64 px) pour le sable ; une erreur d'un rang donne des traits au milieu des terres. Le sable est
  aussi dessiné sous l'eau (`background_layer_group = "water"`) : plage.
- **Les variantes de rive ne se raccordent qu'à quelques px près** (jusqu'à 14 px sur les côtés : le fondu
  d'origine le cachait). Un bord net fait des marches à chaque case : `water.snap` recale chaque masque, sur 16 px le
  long des bords de cellule, à la position médiane des côtés de la même planche (propre à chaque sol : herbe, terres
  et sable diffèrent beaucoup). L'overlay déborde sur la case du dessous : on n'y dessine que la berge qui y pend.
- **Falaises** : chaque orientation est une cellule de 256 px en deux calques (haut, pied `-lower`) qui se
  chevauchent ; on dessine la réunion des deux corps (alpha > 200), puis chaque pixel retourne au calque qui le
  portait. Les cellules se suivent le long d'une chaîne : **prolonger la cellule** (bords répétés, 48 px) avant de
  poser les colonnes, sinon elles s'alignent sur le bord (ligne de sommets et contour droits au raccord). Le banc
  pose des **anneaux** de falaises (`ring` : sortie d'une cellule = entrée de la suivante) : la génération de
  carte n'en a posé aucune sur la surface de test.
- **`tools/bench.py` n'a pas d'option `--help`** : tout argument inconnu lance le banc complet.
- **Lua de Factorio = Lua 5.2** : pas de `//` (division entière) ; `tools/bench.py` compile les scripts avec `lupa`
  avant de lancer le jeu.
- **Sous WSL** : le dossier Factorio est lisible depuis `/mnt/c/...` ; ComfyUI Desktop n'est joignable que si WSL est en mode réseau
  « mirrored » (`.wslconfig`). `bpy` demande Python 3.11 (environnement `.venv` créé avec `uv`).

## 7. Ce qui reste

Tout est dans [`plan.md`](plan.md) : étapes 2 (début de partie sur Nauvis, version 0.1 publiée), 3 (milieu de partie),
4 (fin de partie), 5 (interface), 6 (Space Age). Points ouverts notés pendant l'étape 1 :
- les décorations d'origine jurent sur les sols en aplats : lot 2.8 à avancer juste après le lot 2.1 ;
- pièces « patch » des souterrains laissées vides (les objets passent un instant sur le bord du capot : à peine visible) ;
- patch « gelé » d'Aquilo (étape 6) ; rives des sols construits (béton, pierre, remblai : lot 4.5).

## 8. Chiffres

- 1 578 fichiers remplacés sur 8 246 à couvrir (19 %) : 1 560 dans `base` (38 %), 13 pour Space Age, 5 dans `core`
  (câbles). Par rôle : 1 438 sprites, 88 icônes, 48 ombres, 4 masques ; plus 7 fichiers techniques retouchés (bruit
  et cartes d'effet de l'eau). Détail : [couverture.md](couverture.md).
- ~9 100 lignes écrites à la main (générateurs, outils, banc d'essai, galerie, Lua du mod) ; 83 Mo d'images dans
  `cartoon/mod/graphics`.
- Tout le mod se régénère en ~19 min (`tools/build.py cartoon tous --verifier`, 11 octobre : reproductible, 1 534
  fichiers identiques) ; le banc d'essai fait ses 428 captures en ~40 s par passe.
- Le mod n'a pas été publié ; il s'installe avec `tools/install_mod.sh cartoon` (la galerie : `tools/install_mod.sh cartoon-galerie`).
