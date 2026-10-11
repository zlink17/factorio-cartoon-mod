# Mod Cel-shading : approche et plan

Rédigé le 11 octobre 2026. **État (12 octobre) : étape 0 presque finie (moteur, recette d'images cibles, galerie) ; étape 1 en cours : assembleur 1
modélisé d'après les cibles e-11/e-15 (commits `8e1e15f`, `cd26eeb`), vu en jeu, avis de Bastien attendu ; arbre : prototype
Blender (espèce 02) en cours. Méthode révisée le 12 octobre : prototype Blender d'abord, l'IA si besoin. Plan d'implémentation par lots : sections 5 à 10.**
Règles visuelles : [`celshading/STYLE.md`](../../celshading/STYLE.md) (brouillon).

Objectif : un troisième mod de textures, au style « Wind Waker » : cel-shading (lumière et ombre à bord franc),
couleurs vives et ensoleillées, formes rondes et trapues, fumées en boules à spirale, mer bleu profond à vagues blanches.
Le nom du mod et ses textes publics ne citent ni Zelda ni Wind Waker (marques de Nintendo) : « Cel-Shading ».

---

## 1. Ce qui fait le style, et ce qu'on peut en garder dans Factorio

| Trait de Wind Waker | Traduction dans Factorio | Faisable ? |
|---|---|---|
| **Deux tons par couleur** (éclairé / ombre), frontière nette qui suit la forme : un cylindre a une moitié claire et une moitié sombre, une sphère un croissant d'ombre | Ombrage calculé à partir d'une **vraie direction de lumière**, puis seuillé. C'est la grande différence avec le mod cartoon, dont l'ombrage dépend seulement de l'orientation de la face (dessus, avant, côtés) | Oui (Blender, voir 3.1) |
| **Ombres portées sur l'objet lui-même** (la cheminée projette son ombre sur le toit) | Même rendu, avec ombres de la lumière | Oui |
| **Ombres teintées** : bleu-violet, jamais gris ni noir | Teinte de l'ombre dans le sprite | Oui dans le sprite ; **non pour les ombres au sol** : le jeu dessine les sprites d'ombre en noir semi-transparent, sans couleur (voir section 2) |
| **Peu ou pas de traits noirs** : la silhouette tient par le contraste des couleurs | Contour fin teinté, ou aucun | À décider (question 1) |
| **Couleurs saturées et chaudes**, ciel et mer très bleus, herbe vert vif | Palette propre au mod | À décider (question 2) |
| **Textures peintes simples** : planches, pierres, motifs, sans bruit ni grain | Motifs en aplats sur les modèles (comme les briques du four cartoon) | Oui |
| **Formes rondes et trapues**, proportions un peu exagérées, gros biseaux | Modèles plus ronds que ceux du mod cartoon : le cel-shading a besoin de courbes pour montrer sa frontière | Oui, mais demande de reprendre les modèles (voir 3.2) |
| **Spirales** : fumées en boules qui finissent en volute, vent, nuages, explosions en nuages ronds | Sprites de fumée, de vapeur, d'explosions, de feu | Oui : c'est **la signature** la plus visible, à traiter tôt |
| **Arbres en boules** de feuillage, chacune avec son croissant d'ombre | Arbres en 3D (sphères) plutôt qu'en 2D | Oui (Blender) |
| Mer : bleu profond, écume en lignes blanches dessinées | Bruit de l'eau, textures d'eau, bords | En partie : le shader de l'eau est celui du jeu (même limite que le lot 2.9 cartoon) |

## 2. Contraintes du moteur (connues grâce au mod cartoon)

- **Les ombres au sol sont dessinées par le jeu** : un sprite d'ombre ne fournit qu'une forme ; le jeu l'assombrit
  en noir semi-transparent. Impossible de les teinter en bleu. On peut seulement régler la forme (bord net) et
  l'opacité. Les ombres teintées n'existent donc **que dans les sprites** (ombre propre des objets).
- **La lumière doit venir du même côté que les ombres du jeu** : soleil en haut à gauche, ombres portées vers la
  droite. Dans les sprites : dessus et face gauche éclairés, face droite dans l'ombre. Sinon le monde est incohérent.
- **Mêmes fichiers, même cadre, même emprise** que l'original (règle du mod cartoon, outils de contrôle déjà prêts).
- **Le jeu teinte certains sprites** (feuillages d'arbres, masques d'équipe, décorations) : ils sont dessinés en
  tons neutres, et le cel-shading doit rester lisible après teinte.
- **La nuit** : le jeu assombrit tout ; des ombres déjà bleues risquent de rendre la nuit très bleue. À vérifier en jeu.
- **Petite taille** : 64 px par case. Les leçons du cartoon valent ici : tout détail de moins de 6 px disparaît ;
  vérifier au format final et **en jeu**, jamais sur un montage Python.

## 3. Approche technique recommandée

### 3.1 Rendu cel-shading dans Blender (technique principale)

On garde Blender (`bpy`, Cycles sur CPU, déjà installé dans le `.venv`) : c'est ce qui a rendu le mod cartoon
cohérent, animable et reproductible. Le changement est dans le **matériau** :

1. Une lampe « soleil » à bord dur (angle 0) dans la direction fixée par le style.
2. Rendu en passes : couleur de base (albedo) et lumière directe diffuse (ombres comprises).
3. Seuil sur la lumière : au-dessus, ton éclairé ; en dessous, ton d'ombre (couleur multipliée par la teinte
   d'ombre bleutée). Éventuellement un troisième palier, très clair, pour un reflet sur le métal.
4. Assemblage dans le compositeur de Blender : pas de retouche externe, résultat identique à chaque relance.

Variante plus simple pour un premier essai : seuil sur le produit scalaire normale·lumière directement dans le
matériau (en émission, comme aujourd'hui). Pas d'ombres portées sur l'objet, mais quelques lignes de code. Le
prototype dira si les ombres portées valent la complexité (je pense que oui : c'est très Wind Waker).

Pas de rendu EEVEE (le nœud « Shader to RGB » qui fait le toon dans les tutoriels) : il demande un contexte
graphique, fragile en ligne de commande sous WSL.

### 3.2 Réutiliser les modèles du mod cartoon, puis les arrondir (abandonné le 11 octobre, voir 3.3)

Les générateurs cartoon (`cartoon/blender/*.py`) importent leurs briques depuis `lib.py` (`mat`, `box`, `cyl`,
`gear`, `render_scene`...). Si `celshading/blender/lib.py` offre **les mêmes fonctions** avec le rendu cel-shading,
on peut rendre un modèle cartoon existant en cel-shading sans le réécrire : un aperçu de 9 lots de machines pour
le prix d'une bibliothèque. Ensuite, objet par objet, on arrondit les formes (biseaux plus gros, cylindres au lieu
de boîtes) dans des copies propres au mod, pour ne jamais casser le mod cartoon.

### 3.3 Vision et méthode retenues (11 octobre, soir)

Vu en jeu, le rendu des modèles cartoon en cel-shading est trop discret : boîtes à faces plates, une seule bande
d'ombre sur le flanc droit. Bastien veut **repartir de zéro pour les modèles**, avec sa vision : **Wind Waker pour le
rendu, l'esprit industriel et steampunk de Factorio pour le fond, un peu comme Metal Slug** (machines trapues,
exagérées, rivets, boulons, tuyaux). Machines réinterprétées mais reconnaissables, peu de grosses formes.

Méthode par objet (révisée le 12 octobre : **prototype Blender d'abord**, l'IA seulement s'il ne colle pas, voir
[methode-images-cibles.md](../methode-images-cibles.md)) :
0. **Garder, alléger ou retirer ?** (12 octobre, demande de Bastien) : le Factorio d'origine, très détaillé, a
   besoin d'énormément de sprites ; le cel-shading, fait de grandes formes, risque d'être surchargé si on garde
   tout. Avant de redessiner une famille, on décide si on la garde entière, en quantité réduite (décorations :
   réglages de démarrage du mod, comme `cartoon-epure`), avec moins de variantes, ou pas du tout. Voir STYLE.md §8.
1. **Prototype Blender** rapide, à l'emprise de l'original ; s'il convient, on itère dessus (Bastien peut donner une
   image de référence). Sinon : **guides** tirés du sprite original, puis **images cibles** avec ComfyUI : méthode et outils communs aux mods
   ([docs/methode-images-cibles.md](../methode-images-cibles.md), `tools/concept/`), recette du mod dans
   [`celshading/concept/`](../../celshading/concept/README.md) (SDXL Turbo guidé par ControlNet et par nos propres
   rendus cel-shading en référence de style), plusieurs graines.
3. **Bastien choisit** (ou combine, ou commente), éventuellement une seconde passe en img2img sur l'image choisie.
4. **Modèle Blender** propre au mod (`celshading/blender/`), qui s'approche de l'image cible ; rendu avec le moteur.
5. Vérification en jeu (banc d'essai), comme pour tout lot.

`run_cartoon.py` et le lot « assembleurs » actuel ne servent plus que d'essai du moteur : ils seront remplacés par
les nouveaux modèles.

### 3.4 Le reste

- **Sols, décorations, eau** : procédural 2D (OpenCV, comme `cartoon/terrain/`), avec la palette du mod. Les sols
  plats n'ont pas d'ombrage : ce sont les motifs peints (touffes en virgules, taches) qui donnent le style.
- **Arbres** : en 3D (boules de feuillage cel-shadées) plutôt qu'en 2D ; le cel-shading 2D d'une boule est faux.
- **Fumées, vapeur, explosions, feu** : boules 3D cel-shadées pour les nuages, volutes en 2D vectoriel.
- **Images cibles** : ComfyUI est déjà installé (`~/workspace/comfyui`) ; on peut s'en servir pour des images
  d'ambiance (« cel-shading, couleurs vives » guidé par le sprite original), comme cible à atteindre en Blender,
  **pas** comme production.

### 3.5 Outils communs, déjà prêts

Les outils de `tools/` prennent le nom du dossier du mod : `build.py celshading <lot>`, `inventory.py celshading`,
`check_mod.py celshading --jeu`, `bench.py celshading`, `install_mod.sh celshading`. La galerie connaît aussi le mod (`tools/galerie.py --mod celshading`).

---

## 4. Questions de style (tranchées le 11 octobre : les quatre recommandations, retenues par Bastien)

1. **Contours** : (a) aucun, comme Wind Waker ; (b) **contour fin de silhouette, teinte foncée de l'objet**
   (recommandé : lisible sur une usine chargée, sans ressembler au mod cartoon) ; (c) contour noir chaud.
2. **Palette** : (a) teintes de Factorio conservées (comme le cartoon) ; (b) palette Wind Waker franche ;
   (c) **teintes de Factorio pour reconnaître chaque objet, mais plus saturées et plus claires, avec des ombres
   bleu-violet** (recommandé).
3. **Ombres au sol** : (a) celles du jeu, d'origine ; (b) **silhouette à bord net, moins opaque** (recommandé ;
   le jeu les dessine en noir quoi qu'on fasse).
4. **Par quoi commencer** : (a) **le trio d'essai de l'étape 1** (recommandé) ; (b) directement les machines,
   en réutilisant les modèles cartoon.

## 5. Comment on travaille (plan d'implémentation, 12 octobre)

Même organisation que le mod cartoon ([docs/cartoon/plan.md](../cartoon/plan.md), section 2) : le travail est
découpé en **lots**, avec **les mêmes numéros que le mod cartoon** (galerie commune, comparaison des mods), mais
dans un autre ordre (section 8). Ce qui change, ce sont les contraintes du cel-shading :

- **Chaque modèle est refait de zéro** (prototype Blender d'abord, image cible si besoin) : un lot coûte plus cher
  qu'au cartoon. Deux leviers pour tenir le coût : une **direction par famille** plutôt que par objet (les trois
  coffres, le trio de la vapeur), et une **boîte de pièces communes** (`blender/kit.py`, étape 0) pour que chaque machine coûte un assemblage,
  pas un modèle entier.
- **Moins de sprites que l'original** (STYLE.md §8) : chaque lot commence par « garder, alléger ou retirer ? ».
- **Le jeu teinte certains sprites** (feuillage, masques d'équipe, décorations, fluides) : ils sont rendus en tons
  neutres et doivent rester lisibles une fois teints (ombre bleue x teinte du jeu).
- **Ombres au sol noires** quelle que soit leur couleur : seule leur forme et leur opacité sont à nous.

### 5.1 Le cycle d'un lot

1. **Cadrage** : liste des fichiers (`tools/inventory.py celshading liste <motif>`), lecture des prototypes (tailles,
   `shift`, images, directions, teinte par le jeu), technique (section 7). **D'abord : garder, alléger ou retirer ?**
   Pour chaque famille : quantité (décorations), nombre de modèles distincts (variantes), ou retrait. Le choix est
   proposé à Bastien avec une recommandation.
2. **Prototype Blender** (12 octobre) : quelques grosses formes, à l'emprise de l'original, vues en grand et à la
   taille du jeu ; Bastien juge. S'il ne colle pas : **image cible** (recette `celshading/concept/recette.json`, deux
   séries de 4 graines, planche avec identifiants ; Bastien choisit ; l'image va dans `celshading/concept/cibles/`).
   Pas de prototype ni d'image cible pour le procédural 2D.
3. **Prototype** : un objet représentatif, comparé original / cible / rendu (`tools/concept/compare.py`).
4. **Production** : générateur dans `celshading/blender/` (ou `celshading/terrain/` pour le 2D), déclaré dans
   `celshading/lots.py`, lancé par `tools/build.py celshading <lot>` (écrit dans les overrides, manifeste, contrôle).
5. **Contrôle** : `tools/check_mod.py celshading --jeu`.
6. **Vérification en jeu** : zone du lot dans la galerie (`tools/galerie.py --mod celshading`), banc d'essai pour les
   vues de détail ; **de jour et de nuit** tant que la nuit n'est pas validée (ombres bleues).
7. **Commit** du lot, installation dans le jeu de Bastien (`tools/install_mod.sh celshading`), case cochée ici,
   `STYLE.md` complété, couverture régénérée (`tools/inventory.py celshading`).

### 5.2 Définition de « fini »

Comme au cartoon : chaque fichier du lot est **remplacé, laissé d'origine avec une raison, ou rendu inutile par
l'allègement** (noté dans le tableau du lot) ; le contrôle passe ; le lot a été vu en jeu ; le générateur se relance
de zéro et redonne les mêmes fichiers.

### 5.3 Suivi

Ce plan (cases cochées), la galerie (zones par numéro de lot, communes aux trois mods), `docs/celshading/couverture.md`
(généré ; à compléter pour compter aussi les fichiers rendus inutiles par l'allègement), `STYLE.md`
([VALIDÉ] / [PROVISOIRE]), une synthèse des leçons (`docs/celshading/synthese-celshading.md`, à créer au premier
piège rencontré), `changelog.txt` à la première publication.

## 6. Étape 0 : fondations

- [x] Dossier `celshading/`, mod vide (`celshading/mod/`) incompatible avec les mods cartoon et pixel.
- [x] `celshading/blender/cel_style.py` et `lib.py` : lumière, paliers, teinte d'ombre, contour de silhouette teinté,
      ombres au sol allégées ; mêmes fonctions que la bibliothèque cartoon (reprise telle quelle sauf `mat` et
      `render_scene`). Rendu en deux passes Cycles (couleurs, puis lumière d'un soleil à ombres dures), assemblées
      avec numpy : pas de compositeur Blender. Éclairement calibré (dessus plat = composante verticale de la lumière).
- [x] Essai de faisabilité (`blender/essai.py`) : boîte, cylindre, sphère, tore : frontière d'ombre nette qui suit
      la forme, croissant d'ombre, ombres portées sur l'objet.
- [x] `blender/run_cartoon.py` : rend un générateur du mod cartoon en cel-shading sans le modifier (essai du moteur).
- [x] Galerie : le scénario détecte le mod (variante « celshading », commit `1e27ad4`), `tools/galerie.py --mod celshading`.
- [x] Recette d'images cibles (`celshading/concept/`), sur les outils communs (`tools/concept/`).
- [ ] **Boîte de pièces** (`blender/kit.py`) : tirée de l'assembleur 1 une fois validé (tôle rivetée, gros boulons,
      tuyau à brides, engrenage rond, bloc moteur, pieds), aux proportions « Metal Slug » de la charte.
- [ ] **Allègement par les prototypes** (à cadrer avec le lot 2.8) : réglages de démarrage du mod pour la quantité de
      décorations par famille (comme `cartoon-epure`), et, si besoin, moins de variantes listées dans les
      prototypes (arbres, rochers) plutôt que des fichiers dupliqués : mod plus léger. À vérifier : sans effet sur
      les autres mods, ni sur les sauvegardes existantes.
- [ ] **Icônes** : `lib.save_icon` (repris du cartoon) rendu en cel-shading ; angle et contour à valider sur
      l'icône de l'assembleur 1.

## 7. Quelle technique pour quelle famille

| Code | Technique | Pour |
|---|---|---|
| **B** | Blender cel-shading, modèle propre au mod (prototype d'abord, image cible si besoin) | machines, bâtiments, véhicules, personnage, ennemis, icônes |
| **B3** | Blender cel-shading, formes simples (direction de la famille réutilisée) | arbres, rochers, fumées en boules, objets sur convoyeurs |
| **P** | Procédural 2D (OpenCV, palette du mod), motifs peints en aplats | sols, transitions, eau, taches, volutes |
| **A** | Allégé ou retiré (quantité réduite, variantes regroupées, famille retirée) | décorations, particules, petits effets d'ambiance |
| **L** | Laissé d'origine (fichier technique : masques, cartes d'effets, bruits de shader, reflets) | — |

## 8. Lots

L'ordre suit l'étape 1 du plan initial : **d'abord l'ambiance** (ce qu'on voit sur tout l'écran : sols, nature,
eau, fumées), qui fixe la lumière et la palette, **puis les machines** du début de partie. La colonne
« Allègement » donne la piste à confirmer au cadrage.

### Étape 1 : charte visuelle, sur trois objets vus en jeu
Trois objets qui couvrent les trois familles de rendu, posés ensemble dans le banc d'essai, chacun par la méthode
de la section 3.3 :
- [ ] **Assembleur 1** (machine, surfaces dures) : cibles e-11 et e-15 retenues ; nouveau modèle
      `blender/assembler.py` (planche, ombre, icône), vu en jeu le 12 octobre, avis de Bastien attendu.
- [ ] **Arbre** (organique) : images cibles écartées, prototype Blender retenu (12 octobre), inspiré de l'image de
      Bastien (`concept/cibles/arbre-bastien.jpg`) : touffes en chou-fleur cernées, tronc visible, teinte grise du jeu
      remplacée par un orange d'automne (`mod/data-updates.lua`). `blender/tree.py`, espèce 02 : à voir en jeu.
- [ ] **Four en pierre avec sa fumée** (effets) : la volute de fumée.
- [ ] Plus **l'herbe** comme fond.
- [ ] Vue de nuit des trois objets (ombres bleues de nuit acceptables ?).

Fin d'étape : `STYLE.md` passe de « brouillon » à des règles **[VALIDÉ]**, avec leurs valeurs dans `cel_style.py`.

### Étape 2 : Nauvis, début de partie → version 0.1

Ordre de travail de haut en bas ; les numéros restent ceux du mod cartoon (ceux en 1.x sont les familles que le
cartoon a faites avant son plan).

| Lot | Contenu | Tech. | Allègement (piste) |
|---|---|---|---|
| [ ] 1.1 Sols de Nauvis et transitions | herbes, sables, terres, masques de transition | P | moins de variantes de motif par sol ; transitions nettes |
| [ ] 2.8 Décorations | touffes, buissons, cailloux, taches | P / B3 | **le lot le plus allégé** : familles retirées ou à quelques % (réglage de démarrage), seules les plus lisibles redessinées |
| [ ] 2.7 Nature | arbres (559 fichiers), rochers, poissons | B3 | 2 ou 3 modèles par espèce répartis sur les 12 variantes, peut-être moins d'espèces ; rochers : quelques modèles |
| [ ] 2.9 Eau et falaises | eau, rives, falaises | P (eau), B3 (falaises) | eau : écume en lignes blanches, limitée par le shader du jeu |
| [ ] 3.9a Fumées, vapeur, feu | fumées des fours et chaudières, vapeur, flammes | B3 + P | **avancé** (signature du style) ; particules et petits effets : A |
| [ ] 1.2 Minerais | fer, cuivre, charbon, pierre, uranium | B3 / P | moins de variantes par stade |
| [ ] 1.3 Convoyeurs, souterrains, répartiteurs | 3 niveaux + turbo | B | — (vus partout : à soigner) |
| [ ] 1.4 Bras | 5 bras | B (une cible pour la famille) | — |
| [ ] 1.5 Poteaux et câbles | poteaux, câbles | B (poteaux), P (câbles) | — |
| [ ] 1.6 Assembleurs 2 et 3 | | B (dérivés de l'assembleur 1 et du kit) | — |
| [ ] 2.1 Objets sur les convoyeurs | plaques, engrenages, circuits, packs... | B3 | — |
| [ ] 2.2 Production de base | four en pierre (fait à l'étape 1), foreuses | B | — |
| [ ] 2.3 Stockage | coffres bois, fer, acier | B (une cible) | — |
| [ ] 2.4 Énergie vapeur | pompe côtière, chaudière, machine à vapeur | B (une cible) | — |
| [ ] 2.5 Tuyaux | tuyaux, souterrains, couvercles | B | — |
| [ ] 2.6 Petits bâtiments | laboratoire, radar, lampe | B | — |
| [ ] 2.10 Personnage | animations, 3 armures | B | reprise possible du squelette et des animations du cartoon (copie, sans toucher `cartoon/`) |
| [ ] 2.11 Chargeurs et lecteur de convoyeur | | B | — |
| [ ] 2.12 Publication 0.1 | vignette, description (sans nom de Nintendo), captures, changelog | — | — |

### Étapes 3 à 6

Mêmes lots que le mod cartoon (section 5 du plan cartoon), détaillés au moment de les commencer :

| Étape | Lots | Points propres au cel-shading |
|---|---|---|
| 3 Milieu de partie → 0.2 | 3.1 fours avancés, 3.2 pétrole, 3.3 circuits, 3.4 solaire et accumulateur, 3.5 trains, 3.6 logistique, 3.7 défense, 3.8 ennemis, 3.9b explosions, restes et particules, 3.10 modules et balise | trains et robots : 36 à 64 orientations, le kit et les cibles par famille comptent beaucoup ; ennemis : formes organiques rondes (le style s'y prête), essai de faisabilité d'abord ; explosions en nuages ronds ; particules et restes : A |
| 4 Fin de partie → 0.3 | 4.1 nucléaire, 4.2 véhicules, 4.3 silo, 4.4 robots de combat, 4.5 divers et sols construits | sols construits : motifs peints (dalles, béton) |
| 5 Interface → 0.4 | 5.1 icônes restantes, 5.2 technologies, 5.3 groupes et équipements, 5.4 GUI | icônes des entités modélisées quasi gratuites ; GUI : sans doute laissée d'origine |
| 6 Space Age → 1.x | 6.1 à 6.7, une planète à la fois | une recette d'image cible par planète (palette propre : Vulcanus, Fulgora, Gleba, Aquilo) |

## 9. Risques et décisions à prendre

| Sujet | Question | Quand |
|---|---|---|
| Coût par modèle | Un modèle refait de zéro par objet est long ; tient-on le rythme ? | Mesuré sur l'étape 1 ; kit et cibles par famille (étape 0) |
| Allègement | Jusqu'où réduire décorations et variantes sans appauvrir le monde ? Par fichiers ou par prototypes ? | Cadrage des lots 2.8 et 2.7 |
| Nuit | Les ombres bleues rendent-elles la nuit trop bleue ? | Fin de l'étape 1 |
| Sprites teints par le jeu | Le cel-shading reste-t-il lisible après teinte (feuillage, masques d'équipe) ? | Lots 2.7 et 1.6 |
| Fumées animées | Une volute en boules cel-shadées, animée sur les planches du jeu, est-elle lisible et fluide ? | Étape 1 (four) |
| Eau | Le shader du jeu limite ce qu'on peut faire de la mer « Wind Waker » | Lot 2.9 |
| Personnage et ennemis | Animation organique en cel-shading à coût raisonnable | Lots 2.10 et 3.8 |
| ComfyUI partagé | Une génération à la fois pour toutes les sessions (carte de 6 Go) | En continu : prévenir avant une série |
| Nom et textes publics | Ni Zelda ni Wind Waker (marques de Nintendo) | Lot 2.12 |
| Poids, licence, compatibilité | Comme le mod cartoon (section 6 de son plan) | Avant la 0.1 |
| Outils communs | Toute évolution de `tools/` reste compatible avec les mods cartoon et pixel | En continu |

## 10. Jalons

| Version | Contenu |
|---|---|
| — | Étapes 0 et 1 : moteur, kit, charte validée sur assembleur, arbre, four et fumée |
| 0.1 | Nauvis, début de partie : ambiance (sols, nature, eau, fumées) et machines des premières heures |
| 0.2 | Milieu de partie |
| 0.3 | Fin de partie |
| 0.4 | Interface |
| 1.0 | Nauvis entièrement en cel-shading |
| 1.x | Space Age, planète par planète |
