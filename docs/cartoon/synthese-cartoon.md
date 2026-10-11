# Mod Cartoon : synthèse du travail

État au 11 octobre 2026 (étape 2 commencée : lots 2.1, 2.7 et 2.8 faits). Ce document résume ce qui a été fait, comment, ce qu'on a appris en
chemin et ce qui reste. Le guide de style de référence est [`cartoon/STYLE.md`](../../cartoon/STYLE.md) ; le mode d'emploi
des outils est dans [`cartoon/README.md`](../../cartoon/README.md) ; la feuille de route est dans [`plan.md`](plan.md).

## 0. Reprendre le travail (nouvelle session)

1. Lire [`plan.md`](plan.md) : méthode (un lot = cadrage, prototype, production, contrôle, vérification en jeu, commit),
   étapes et cases cochées. **Étapes 0 (outillage) et 1 (validation en jeu de l'existant) terminées ; lots 2.1
   « Objets sur les convoyeurs », 2.7 « Nature » et 2.8 « Décorations » faits.**
2. **Prochaine action : lot 2.2 « Production de base »** (four en pierre, foreuses), puis l'ordre du plan.
   **Fait le 11 octobre (hors lot) : tri des décorations par profondeur.** Herbes, buissons, rameaux, cailloux et
   souche de Nauvis passent dans deux couches triées, sous les convoyeurs et les entités : herbes dans
   « remnants », éléments uniques (cailloux, buissons...) dans « floor », au-dessus (`cartoon/mod/sorted_decoratives.lua`).
   Chaque image est recalée pour que le pied du dessin tombe sur la position de la décoration
   (`tools/decorative_feet.py`, lancé par `build.py`, écrit `cartoon/mod/feet.lua` ; appliqué dans
   `data-final-fixes.lua`). Règle voulue par Bastien : ce qui a le pied plus bas à l'écran passe devant. Scènes de
   contrôle : `detail-superpositions`, `detail-melange` (arbres, rochers, convoyeur) et `monde-rocher` du banc.
   Limites connues : une touffe devant un caillou ou un rocher passe dessous (peu visible) ; pieds à égalité =
   ordre arbitraire ; performance à surveiller sur une grande partie.
3. Cadrage d'un lot : `.venv/bin/python tools/inventory.py cartoon liste icons/` (fichiers, tailles, prototypes).
4. Production : ajouter le générateur dans `cartoon/lots.py`, puis `.venv/bin/python tools/build.py cartoon <lot>`.
5. Vérification : `.venv/bin/python tools/check_mod.py cartoon --jeu`, puis `.venv/bin/python tools/bench.py cartoon
   --sans-origine` (captures et comparaisons dans `.cache/vitrine/comparaison/`, ouvre une fenêtre Factorio ~40 s).
6. Avant de commiter un lot : `.venv/bin/python tools/inventory.py cartoon` (couverture), cocher le lot dans le plan.
7. Après le commit : `tools/install_mod.sh cartoon` met à jour le mod dans le jeu de Bastien (accord permanent).
   Le banc d'essai et `check_mod.py --jeu` utilisent une instance isolée et ne touchent pas à son jeu.

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
              underground.py, splitter.py, pole.py, ore.py
  terrain/    ground.py (sols de Nauvis), masks.py (masques de transition nets), decoratives.py, trees.py,
              rocks.py (gros rochers, poissons)
  lots.py     les lots et les commandes qui les produisent (lu par tools/build.py)
  ai/         ComfyUI (comfy_batch.py, workflow, post-traitement) : essai, non retenu
  STYLE.md    guide de style
cartoon-epure/mod/   sous-mod facultatif « terrain épuré » (voir plus bas)
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

## 5. Ce qui est fait (1 357 fichiers remplacés, tous vus en jeu)

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
- eau et bords d'eau encore d'origine (lot 2.9) ; tuyaux des assembleurs 2 et 3 (lot 2.5) ; patch « gelé » d'Aquilo (étape 6).

## 8. Chiffres

- 1 357 fichiers remplacés sur 8 246 à couvrir (16 %) : 669 de décorations, 448 d'arbres, 54 de rochers et poissons, 75 d'entités, 71 d'icônes, 22 de terrain (19 planches, 3 masques),
  5 de câbles (jeu `core`), 13 pour Space Age.
- ~3 500 lignes de code (générateurs, outils, banc d'essai) ; 37 Mo d'images dans `cartoon/mod/graphics`.
- Tout le mod se régénère en 10 min (`tools/build.py cartoon tous`) ; le banc d'essai fait ses 264 captures en ~40 s par passe.
- Le mod n'a pas été publié ; il s'installe avec `tools/install_mod.sh cartoon`.
